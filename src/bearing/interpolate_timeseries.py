#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/interpolate_timeseries.py
────────────────────────────────────────────────────────────────────────────
Erzeugt für jeden AIS-Track (MMSI + Segment) ein äquidistantes Zeitraster
und interpoliert alle numerischen Spalten linear (zeitabhängig). Kategoriale
Felder werden per Vorwärts-/Rückwärts-Fill ausgefüllt.

Segment-Regel:
    • Destination-Wechsel ODER
    • Zeitlücke > max_gap_minutes  ⇒  neuer 'segment_idx'

Input  : cfg["output"]["cleaned_csv"]        (aus load_and_clean.py)
Output : cfg["output"]["interpolated_csv"]   (für compute_bearing.py)

Aufruf:
    python src/bearing/interpolate_timeseries.py \
        --config src/bearing/config/bearing.json
"""
from __future__ import annotations

import os, json, logging
from typing import List
import click
import pandas as pd
import numpy as np

pd.set_option("future.no_silent_downcasting", True)  # ← Warning verschwindet

# ────────────────────────────────  Logging  ────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)


# ───────────────────────  Segment-Spalte anfügen  ──────────────────────────
def add_segment_column(
    df: pd.DataFrame,
    *,
    ts_col: str,
    dest_col: str,
    gap_threshold: pd.Timedelta,
) -> pd.DataFrame:
    df = df.sort_values(ts_col).copy()
    dest_change = df[dest_col].fillna("∅").ne(df[dest_col].fillna("∅").shift())
    time_gap = df[ts_col].diff().gt(gap_threshold)
    df["segment_idx"] = (dest_change | time_gap).cumsum() - 1
    return df


# ───────────────────────────────────  CLI  ─────────────────────────────────
@click.command()
@click.option(
    "--config", "cfg_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur bearing.json",
)
def main(cfg_path: str) -> None:
    # 1) Config laden
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    log.info(f"→ Config geladen: {cfg_path}")

    in_csv  = cfg["output"]["cleaned_csv"]
    out_csv = cfg["output"]["interpolated_csv"]

    ts_col  = cfg["timestamp_column"]
    lat_col = cfg["lat_column"]
    lon_col = cfg["lon_column"]

    mmsi_col = cfg.get("mmsi_column", "MMSI")
    dest_col = cfg.get("destination_column", "Destination")

    ip_cfg           = cfg.get("interpolation", {})
    interval_seconds = int(ip_cfg.get("interval_seconds", 20))
    gap_minutes      = int(ip_cfg.get("max_gap_minutes", 60))

    freq_str = f"{interval_seconds}s"
    gap_td   = pd.Timedelta(minutes=gap_minutes)

    # 2) Daten laden
    log.info(f"📥 Lade AIS-Daten: {in_csv}")
    df = pd.read_csv(in_csv, low_memory=False, parse_dates=[ts_col])
    log.info(f"→ {len(df):,} Zeilen geladen")

    # 2a) MMSI-Spalte prüfen / auto-finden
    if mmsi_col not in df.columns:
        cand = [c for c in df.columns if c.lower().strip() == "mmsi"]
        if not cand:
            raise KeyError("MMSI-Spalte nicht gefunden – Config prüfen.")
        mmsi_col = cand[0]
        log.info(f"⚠️  Verwende '{mmsi_col}' als MMSI-Spalte")

    # 2b) Lat/Lon in Float casten
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df = df.dropna(subset=[lat_col, lon_col])

    # 3) Segmente bestimmen
    log.info("🔎 Ermittle Segmente pro MMSI …")
    df = (
        df.groupby(mmsi_col, group_keys=False, sort=False)
          .apply(
              add_segment_column,
              ts_col=ts_col,
              dest_col=dest_col,
              gap_threshold=gap_td,
          )
          .reset_index(drop=True)
    )
    log.info(
        f"→ {df.groupby(mmsi_col)['segment_idx'].nunique().sum():,} Segmente identifiziert"
    )

    # 4) Spaltenlisten
    numeric_cols: List[str] = [lat_col, lon_col] + [
        c for c in df.columns
        if df[c].dtype.kind in "fi" and c not in (lat_col, lon_col)
    ]
    categorical_cols: List[str] = [
        c for c in df.columns
        if c not in numeric_cols + [ts_col, mmsi_col, "segment_idx"]
    ]

    # 5) Resampling & Interpolation
    log.info(f"⏱  Interpoliere … ({freq_str}-Raster)")
    parts: List[pd.DataFrame] = []

    for (mmsi, seg_id), grp in df.groupby([mmsi_col, "segment_idx"], sort=False):
        grp = grp.sort_values(ts_col)
        grp = grp[~grp[ts_col].duplicated(keep="first")]  # doppelte Timestamps

        grp = grp.set_index(ts_col)

        # Zielindex + Originalpunkte
        target_idx = pd.date_range(
            start=grp.index.min(), end=grp.index.max(), freq=freq_str
        )
        full_idx = target_idx.union(grp.index)        # ← wichtig!
        grp = grp.reindex(full_idx).sort_index()

        # numerische Felder interpolieren (zeitbasiert)
        grp[numeric_cols] = grp[numeric_cols].interpolate(
            method="time", limit_direction="both"
        )
        # kategoriale Felder füllen
        grp[categorical_cols] = (
            grp[categorical_cols]
                .ffill()
                .bfill()
                .infer_objects(copy=False)   # ← Warnungsfrei
)
        # nur noch Rasterpunkte behalten
        grp = grp.loc[target_idx]

        grp[mmsi_col]      = mmsi
        grp["segment_idx"] = seg_id
        grp.index.name     = ts_col
        parts.append(grp.reset_index())

    interpolated_df = pd.concat(parts, ignore_index=True)
    log.info(f"→ Ergebnis: {len(interpolated_df):,} Zeilen")

    # 6) Speichern
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    interpolated_df.to_csv(out_csv, index=False)
    log.info(f"✅ Interpolierte Datei gespeichert: {out_csv}")


# ─────────────────────────────  Entry-Point  ───────────────────────────────
if __name__ == "__main__":
    main()
    
# python src/bearing/interpolate_timeseries.py --config src/bearing/config/bearing.json