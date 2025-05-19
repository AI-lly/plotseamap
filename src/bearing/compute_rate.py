#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/compute_rate.py

Berechnet die zeitliche Änderungsrate der Bearing (°/s) je MMSI + Segment.
Winkelsprünge über 0°/360° werden per komplexer Division korrekt behandelt.

Aufruf:
    python src/bearing/compute_rate.py \
        --config src/bearing/config/bearing.json
"""
from __future__ import annotations

import os
import json
import logging

import click
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter   # optionales Glätten

# ─────────────────────────── Logging ───────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

pd.set_option("future.no_silent_downcasting", True)   # künftiges pandas-Verhalten


# ────────────────────── Hilfsfunktion Winkel-Diff ──────────────────────
def get_angle_diff(a_curr: np.ndarray, a_prev: np.ndarray) -> np.ndarray:
    """
    Winkeldifferenz (-180..+180°) via komplexe Division, robust gegen Wrap.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        diff = np.rad2deg(
            np.angle(
                np.exp(1j * np.deg2rad(a_curr)) /
                np.exp(1j * np.deg2rad(a_prev))
            )
        )
    return diff


# ───────────────────────────── CLI ─────────────────────────────
@click.command()
@click.option(
    "--config", "cfg_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur bearing.json",
)
def main(cfg_path: str) -> None:
    # 1) Config einlesen
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    log.info(f"→ Config geladen: {cfg_path}")

    in_csv   = cfg["output"]["with_bearing_csv"]
    out_csv  = cfg["output"]["with_rate_csv"]

    ts_col   = cfg["timestamp_column"]
    bear_col = cfg["bearing_column"]
    mmsi_col = cfg.get("mmsi_column", "MMSI")
    seg_col  = "segment_idx"                       # stammt aus interpolate-Step

    dt_const = cfg.get("delta_t_sec")              # optional
    sg_win   = cfg.get("rate_savgol_window")       # optional Glättung

    # 2) Daten laden
    log.info(f"📥 Lade Bearing-Daten: {in_csv}")
    df = pd.read_csv(in_csv, parse_dates=[ts_col], low_memory=False)
    log.info(f"→ {len(df):,} Zeilen eingelesen")

    # 3) Gruppier-Spalten
    grp_cols = [mmsi_col]
    if seg_col in df.columns:
        grp_cols.append(seg_col)

    # 4) Winkel-Differenz berechnen
    df["_prev_bearing"] = df.groupby(grp_cols)[bear_col].shift()

    df["_angle_diff"] = get_angle_diff(
        df[bear_col].to_numpy(),
        df["_prev_bearing"].to_numpy()
    )
    df["_angle_diff"] = df["_angle_diff"].fillna(0.0)

    # 5) Δt bestimmen
    if dt_const is None:
        df["_prev_ts"] = df.groupby(grp_cols)[ts_col].shift()
        df["_dt"] = (df[ts_col] - df["_prev_ts"]).dt.total_seconds().fillna(1.0)
    else:
        df["_dt"] = dt_const

    # 6) Bearing-Rate
    df["bearing_rate"] = df["_angle_diff"] / df["_dt"]

    # 7) Optionale Glättung
    if sg_win and sg_win > 2 and sg_win % 2 == 1:
        log.info(f"✨ Glätte Bearing-Rate mit Savitzky-Golay (window={sg_win})")
        def smooth(arr):           # lokaler Helper
            return savgol_filter(arr, sg_win, polyorder=2, mode="interp")

        df["bearing_rate"] = (
            df.groupby(grp_cols)["bearing_rate"].transform(smooth)
        )

    # 8) Aufräumen
    df.drop(
        columns=["_prev_bearing", "_angle_diff", "_dt", "_prev_ts"],
        errors="ignore",
        inplace=True
    )

    # 9) Speichern
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=False)
    log.info(f"✅ Bearing-Rate gespeichert: {out_csv}")


# ───────────────────────── Entry-Point ─────────────────────────
if __name__ == "__main__":
    main()

# python src/bearing/compute_rate.py --config src/bearing/config/bearing.json