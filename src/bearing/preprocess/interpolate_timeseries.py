#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/preprocess/interpolate_timeseries.py

Erzeugt für jeden AIS-Track (MMSI + Segment) ein äquidistantes Zeitraster
und interpoliert alle numerischen Spalten linear (zeitabhängig). Kategoriale
Felder werden per Vorwärts-/Rückwärts-Fill aufgefüllt, ohne Pandas-Apply-Warnings.

Segment-Regel:
    • Zeitlücke > max_gap_minutes ⇒ neuer ‘segment_idx’
    • optional: Destination-Wechsel, wenn in der Config aktiviert

Input  : cfg["output"]["cleaned_csv"]      (aus load_and_clean.py)
Output : cfg["output"]["interpolated_csv"] (für compute_bearing.py)
"""
import os
import json
import logging
from typing import List, Optional

import click
import pandas as pd
import numpy as np

# ───────────────────────────────────────── Logging ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def add_segment_column(
    df: pd.DataFrame,
    *,
    ts_col: str,
    gap_threshold: pd.Timedelta,
    use_destination: bool,
    dest_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Hängt Spalte 'segment_idx' an:
      • neuer Index bei Zeitlücke > gap_threshold
      • optional: bei Destination-Wechsel
    """
    df = df.sort_values(ts_col).copy()
    time_gap = df[ts_col].diff().gt(gap_threshold)
    if use_destination and dest_col in df.columns:
        dest_change = (
            df[dest_col].fillna("∅")
              .ne(df[dest_col].fillna("∅").shift())
        )
    else:
        dest_change = pd.Series(False, index=df.index)
    df["segment_idx"] = (time_gap | dest_change).cumsum().astype(int)
    return df


@click.command()
@click.option(
    "--config", "cfg_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur bearing.json"
)
def main(cfg_path: str) -> None:
    # 1) Config laden
    logger.info(f"→ Lade Konfiguration: {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # 2) Pfade & Parameter
    in_csv   = cfg["output"]["cleaned_csv"]
    out_csv  = cfg["output"]["interpolated_csv"]
    ts_col   = cfg["timestamp_column"]
    lat_col  = cfg["lat_column"]
    lon_col  = cfg["lon_column"]
    mmsi_col = cfg.get("mmsi_column", "MMSI")
    dest_col = cfg.get("destination_column", "Destination")

    ip = cfg.get("interpolation", {})
    interval_seconds = int(ip.get("interval_seconds", 20))
    gap_minutes      = int(ip.get("max_gap_minutes", 60))
    use_dest         = bool(ip.get("use_destination", True))

    freq_str = f"{interval_seconds}s"
    gap_td   = pd.Timedelta(minutes=gap_minutes)

    logger.info(
        f"▸ Intervall={interval_seconds}s, "
        f"max_gap={gap_minutes}min, use_destination={use_dest}"
    )

    # 3) Daten laden
    logger.info(f"📥 Lade AIS-Daten: {in_csv}")
    df = pd.read_csv(in_csv, parse_dates=[ts_col], low_memory=False)
    logger.info(f"→ {len(df):,} Zeilen geladen")

    # 3a) MMSI-Spalte validieren
    if mmsi_col not in df.columns:
        candidates = [c for c in df.columns if c.lower().strip()=="mmsi"]
        if not candidates:
            raise KeyError("MMSI-Spalte nicht gefunden. Config prüfen.")
        mmsi_col = candidates[0]
        logger.info(f"⚠️  Verwende '{mmsi_col}' als MMSI-Spalte")

    # 3b) Koordinaten säubern
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    before = len(df)
    df = df.dropna(subset=[lat_col, lon_col])
    logger.info(f"→ {before - len(df):,} Zeilen ohne Koordinaten entfernt")

    # 4) Segmente berechnen (ohne apply, kein DeprecationWarning)
    logger.info("🔎 Ermittle Segmente pro MMSI …")
    segmented_parts: List[pd.DataFrame] = []
    for _, group in df.groupby(mmsi_col, sort=False):
        seg = add_segment_column(
            group,
            ts_col=ts_col,
            gap_threshold=gap_td,
            use_destination=use_dest,
            dest_col=dest_col
        )
        segmented_parts.append(seg)
    df = pd.concat(segmented_parts, ignore_index=True)
    total_segs = df.groupby(mmsi_col)["segment_idx"].nunique().sum()
    logger.info(f"→ {total_segs:,} Segmente identifiziert")

    # 5) Spalten für Interpolation bestimmen
    numeric_cols = [
        c for c in df.columns
        if df[c].dtype.kind in "fi" and c not in [lat_col, lon_col]
    ] + [lat_col, lon_col]
    categorical_cols = [
        c for c in df.columns
        if c not in numeric_cols + [ts_col, mmsi_col, "segment_idx"]
    ]
    logger.info(f"Numerische Spalten: {numeric_cols}")
    logger.info(f"Kategoriale Spalten: {categorical_cols}")

    # 6) Kategoriale Spalten zum 'category'-Dtype
    if categorical_cols:
        df[categorical_cols] = df[categorical_cols].astype("category")

    # 7) Resampling & Interpolation
    logger.info(f"⏱  Interpoliere auf {freq_str}-Raster …")
    interpolated_parts: List[pd.DataFrame] = []

    for (mmsi, seg_id), group in df.groupby([mmsi_col, "segment_idx"], sort=False):
        grp = group.sort_values(ts_col).drop_duplicates(ts_col, keep="first")
        grp = grp.set_index(ts_col)

        # gemeinsame Indexunion: Raster + Originalzeiten
        target_idx = pd.date_range(
            start=grp.index.min(),
            end=grp.index.max(),
            freq=freq_str
        )
        full_idx = target_idx.union(grp.index)
        grp = grp.reindex(full_idx).sort_index()

        # numerische Felder: zeitbasierte Interpolation
        grp[numeric_cols] = grp[numeric_cols].interpolate(
            method="time", limit_direction="both"
        )
        # kategoriale Felder: Vorwärts-/Rückwärts-Fill
        if categorical_cols:
            grp[categorical_cols] = grp[categorical_cols].ffill().bfill()

        # nur Rasterpunkte behalten
        grp = grp.loc[target_idx]
        grp[mmsi_col]      = mmsi
        grp["segment_idx"] = seg_id
        grp.index.name     = ts_col
        interpolated_parts.append(grp.reset_index())

    interpolated_df = pd.concat(interpolated_parts, ignore_index=True)
    logger.info(f"→ {len(interpolated_df):,} Zeilen im interpolierten DataFrame")

    # 8) Speichern
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    interpolated_df.to_csv(out_csv, index=False)
    logger.info(f"✅ Interpolierte Datei gespeichert: {out_csv}")


if __name__ == "__main__":
    main()
    
# python src/bearing/preprocess/interpolate_timeseries.py --config src/bearing/config/bearing.json