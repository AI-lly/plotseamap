#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/build_range_lut.py

Erstellt aus einem AIS-Datensatz eine Lookup-Tabelle
P(r | bearing_bin, bearing_rate_bin) und speichert sie als Pickle.
Input-/Output-Pfade und Raster-Parameter kommen aus der JSON-Config.
"""
import os
import json
import pickle
import logging

import click
import numpy as np
import pandas as pd

# ───────────────────────────────────────────────────────────────────────
# Logging konfigurieren
# ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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

    # 2) Pfade & Parameter aus Config
    stat_cfg   = cfg.get("statistics", {})
    csv_path   = cfg["output"]["with_distance_csv"]
    out_pkl    = stat_cfg.get("output")
    if not out_pkl:
        logger.error("Fehler: 'statistics.output' fehlt in der Config")
        raise KeyError("Config benötigt 'statistics.output'")

    AZ_BIN_DEG    = stat_cfg.get("az_bin_deg", 5)
    POS_RATE_EDGES= stat_cfg.get("rate_edges", [0, .01, .03, .1, .3, 1, 3, 10])
    R_STEP_M      = stat_cfg.get("r_step_m", 500)
    R_MAX_M       = stat_cfg.get("r_max_m", 20_000)
    dist_col      = cfg.get("distance_column", "dist_m")

    logger.info(
        f"▸ Raster-Parameter: az_bin_deg={AZ_BIN_DEG}, "
        f"pos_rate_edges={POS_RATE_EDGES}, r_step_m={R_STEP_M}, r_max_m={R_MAX_M}"
    )

    # 3) AIS-Daten laden
    logger.info(f"📥 Lade AIS-Daten: {csv_path}")
    df = pd.read_csv(
        csv_path,
        usecols=["bearing", "bearing_rate", dist_col],
        low_memory=False
    )
    logger.info(f"→ {len(df):,} Zeilen geladen")

    # 4) Bearing-Bins erstellen
    logger.info("🔢 Erstelle Bearing-Bins")
    df["bearing_bin"] = (df["bearing"] // AZ_BIN_DEG) * AZ_BIN_DEG

    # 5) Rate-Bins erstellen (jetzt mit positiven UND negativen Raten)
    logger.info("🔢 Erstelle symmetrische Rate-Edges")
    # negative Kanten (ohne 0), in umgekehrter Reihenfolge
    neg_edges = [-e for e in reversed(POS_RATE_EDGES[1:])]
    rate_edges = neg_edges + POS_RATE_EDGES
    logger.info(f"▸ Rate-Edges (symmetrisch um 0): {rate_edges}")

    df["bearing_rate_bin"] = (
        pd.cut(
            df["bearing_rate"],
            bins=rate_edges,
            right=False,
            labels=rate_edges[:-1]
        )
        .astype(float)
    )

    # 6) Distanz-Bins erstellen
    logger.info("🔢 Erstelle Distanz-Bins")
    range_vec = np.arange(0, R_MAX_M, R_STEP_M) + R_STEP_M / 2
    df["dist_bin"] = (
        (df[dist_col] // R_STEP_M)
        .clip(upper=len(range_vec) - 1)
        .astype(int)
    )

    # 7) 3-D-Histogramm (θ × ω × r)
    AZ_BINS   = 360 // AZ_BIN_DEG
    RATE_BINS = len(rate_edges) - 1
    R_BINS    = len(range_vec)
    logger.info(f"📊 Erstelle 3D-Histogramm mit Form {AZ_BINS}×{RATE_BINS}×{R_BINS}")
    hist = np.zeros((AZ_BINS, RATE_BINS, R_BINS), dtype=int)

    rate_to_idx = {edge: idx for idx, edge in enumerate(rate_edges[:-1])}

    for (b_bin, r_bin, d_idx), cnt in df.groupby(
        ["bearing_bin", "bearing_rate_bin", "dist_bin"]
    ).size().items():
        if pd.isna(r_bin):
            continue
        i_b = int(b_bin / AZ_BIN_DEG)
        i_r = rate_to_idx[r_bin]
        hist[i_b, i_r, int(d_idx)] = cnt

    # 8) Normierung → P(r | θ, ω)
    logger.info("➗ Normiere Histogramm zu Wahrscheinlichkeiten")
    sums = hist.sum(axis=2, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = np.zeros_like(hist, dtype="float64")
        np.divide(hist, sums, out=raw, where=sums != 0)
    prob_cube = raw.astype("float32")

    # 9) Lookup-Tabelle speichern
    logger.info(f"💾 Speicher Lookup-Table nach: {out_pkl}")
    os.makedirs(os.path.dirname(out_pkl), exist_ok=True)
    with open(out_pkl, "wb") as f:
        pickle.dump({
            "params": {
                "az_bin_deg": AZ_BIN_DEG,
                "rate_edges": rate_edges,
                "range_vec":  range_vec.tolist()
            },
            "prob_cube": prob_cube
        }, f)
    logger.info("✅ Lookup-Tabelle erfolgreich gespeichert")


if __name__ == "__main__":
    main()

# python src/bearing/build_range_lut.py --config src/bearing/config/bearing.json   