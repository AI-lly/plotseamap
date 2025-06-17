#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/build_range_lut.py

Erstellt aus einem AIS-Datensatz eine Lookup-Tabelle
P(r | θ, ω) und zusätzlich P(ω | θ).

• Azimut-Bins werden gleichmäßig in Grad aufgespannt.
• Bearing-Rate-Edges werden im logspace von 10⁻² … 10¹ erzeugt,
  symmetrisch um 0 (ohne doppeltes 0).
• Distanz-Bins in festen Schritten.

Alles kommt aus der JSON-Config, außer den log-space-Parametern, die
fest auf -2 bis +1 (Exponent) mit 21 Stufen eingestellt sind.
"""
import os
import json
import pickle
import logging

import click
import numpy as np
import pandas as pd
from pathlib import Path

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
    "--config", "-c", "cfg_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur bearing.json"
)
def main(cfg_path):
    # 1) Config laden
    logger.info(f"→ Lade Konfiguration: {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    stat_cfg = cfg.get("statistics", {})
    csv_path = cfg["output"]["with_distance_csv"]
    out_pkl  = stat_cfg.get("output")
    if not out_pkl:
        logger.error("Fehler: 'statistics.output' fehlt in der Config")
        raise KeyError("Config benötigt 'statistics.output'")

    # 2) Raster-Parameter
    AZ_BIN_DEG = stat_cfg.get("az_bin_deg", 5)
    R_STEP_M   = stat_cfg.get("r_step_m", 500)
    R_MAX_M    = stat_cfg.get("r_max_m", 20_000)
    dist_col   = cfg.get("distance_column", "dist_m")

    # 3) Log-Space Rate-Edges (Exponenten von -2 bis +1, 21 Punkte)
    pos_edges = np.logspace(-5, 1, num=21)
    # Entferne 0 (ist nicht in logspace) und spiegle nach negativ
    neg_edges = -pos_edges[::-1]
    rate_edges = np.concatenate([neg_edges, pos_edges])
    logger.info(f"▸ Verwende logspace Rate-Edges (symmetrisch): {rate_edges}")

    logger.info(
        f"▸ Raster-Parameter: az_bin_deg={AZ_BIN_DEG}, "
        f"r_step_m={R_STEP_M}, r_max_m={R_MAX_M}"
    )

    # 4) AIS-Daten laden
    logger.info(f"📥 Lade AIS-Daten: {csv_path}")
    df = pd.read_csv(csv_path, usecols=["bearing", "bearing_rate", dist_col])
    logger.info(f"→ {len(df):,} Zeilen geladen")

    # 5) Bearing-Bins
    logger.info("🔢 Erstelle Bearing-Bins")
    df["bearing_bin"] = (df["bearing"] // AZ_BIN_DEG) * AZ_BIN_DEG

    # 6) Rate-Bins
    logger.info("🔢 Weise Bearing-Rate den logspace-Bins zu")
    df["bearing_rate_bin"] = pd.cut(
        df["bearing_rate"],
        bins=rate_edges,
        right=False,
        labels=rate_edges[:-1]
    ).astype(float)

    # 7) Distanz-Bins
    logger.info("🔢 Erstelle Distanz-Bins")
    range_vec = np.arange(0, R_MAX_M, R_STEP_M) + R_STEP_M / 2
    df["dist_bin"] = (
        (df[dist_col] // R_STEP_M)
        .clip(upper=len(range_vec) - 1)
        .astype(int)
    )

    # 8) 3D-Histogramm zählen (θ × ω × r)
    n_az   = 360 // AZ_BIN_DEG
    n_rate = len(rate_edges) - 1
    n_r    = len(range_vec)
    logger.info(f"📊 Baue 3D-Histogramm mit Form {n_az}×{n_rate}×{n_r}")
    counts = np.zeros((n_az, n_rate, n_r), dtype=int)
    rate_to_idx = {edge: idx for idx, edge in enumerate(rate_edges[:-1])}

    group = df.groupby(["bearing_bin", "bearing_rate_bin", "dist_bin"])
    for (b_bin, r_bin, d_bin), cnt in group.size().items():
        if pd.isna(r_bin):
            continue
        az_i = int(b_bin / AZ_BIN_DEG)
        rt_i = rate_to_idx[r_bin]
        counts[az_i, rt_i, int(d_bin)] = cnt

    # 9) Wahrscheinlichkeiten P(r | θ, ω)
    logger.info("➗ Normiere zu P(r | θ, ω)")
    sums_r = counts.sum(axis=2, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        probs = np.divide(counts, sums_r, where=sums_r!=0)
    prob_cube = probs.astype("float32")

    # 10) Marginal P(ω | θ)
    logger.info("➗ Berechne marginal P(ω | θ)")
    counts_rate = counts.sum(axis=2)           # (n_az, n_rate)
    sums_rate   = counts_rate.sum(axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        prob_rate = np.divide(counts_rate, sums_rate, where=sums_rate!=0)
    prob_rate[np.isnan(prob_rate)] = 0.0
    prob_rate_cube = prob_rate.astype("float32")

    # 11) Speichern
    logger.info(f"💾 Speicher Lookup-Tabelle nach: {out_pkl}")
    os.makedirs(os.path.dirname(out_pkl), exist_ok=True)
    with open(out_pkl, "wb") as f:
        pickle.dump({
            "params": {
                "az_bin_deg": AZ_BIN_DEG,
                "rate_edges": rate_edges.tolist(),
                "range_vec":  range_vec.tolist()
            },
            "counts_cube":     counts,         # int counts (θ,ω,r)
            "prob_cube":       prob_cube,      # P(r|θ,ω)
            "prob_rate_cube":  prob_rate_cube  # P(ω|θ)
        }, f)

    logger.info("✅ Lookup-Tabelle erfolgreich gespeichert")
    logger.info(f"counts_cube shape:    {counts.shape}")
    logger.info(f"prob_cube shape:      {prob_cube.shape}")
    logger.info(f"prob_rate_cube shape: {prob_rate_cube.shape}")


if __name__ == "__main__":
    main()

# python src/bearing/build_lut.py --config src/bearing/config/bearing.json   