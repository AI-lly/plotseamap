#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/compute_sector_stats.py
Erstellt ein 2-D-Histogramm (Bearing × Distanz) und zeichnet einen Polar-Plot
im Stil deines Snippets (default-Colormap, shading="auto").
"""
from __future__ import annotations
import os, json, logging, click
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


@click.command()
@click.option("--config", "cfg_path", required=True,
              type=click.Path(exists=True, dir_okay=False),
              help="Pfad zur bearing.json")
def main(cfg_path):
    # ── Config ───────────────────────────────────────────
    with open(cfg_path) as f:
        cfg = json.load(f)

    in_csv  = cfg["output"]["with_distance_csv"]
    out_csv = cfg["output"].get(
        "sector_hist_csv", "data/processed/bearing/sector_histogram.csv"
    )
    out_png = cfg["output"].get("sector_hist_png", None)   # optional

    bearing_col = cfg["bearing_column"]
    dist_col    = cfg.get("distance_column", "dist_m")

    # Rasterparameter (hier beispielhaft 5° × 500 m)
    az_bin_deg = 15
    r_bin_m    = 5000
    r_max_m    = 20_000

    # ── Daten laden ──────────────────────────────────────
    df = pd.read_csv(in_csv, usecols=[bearing_col, dist_col]).dropna()

    # ── Histogramm ───────────────────────────────────────
    az_bins = np.arange(0, 360 + az_bin_deg, az_bin_deg)
    r_bins  = np.arange(0, r_max_m + r_bin_m, r_bin_m)

    H, _, _ = np.histogram2d(
        df[bearing_col], df[dist_col], bins=[az_bins, r_bins]
    )

    row_sums = H.sum(axis=1, keepdims=True)
    H_prob   = np.divide(H, row_sums, where=row_sums != 0)

    # ── CSV speichern ────────────────────────────────────
    az_centers = az_bins[:-1] + az_bin_deg / 2
    r_centers  = r_bins[:-1]  + r_bin_m  / 2
    hist_df = pd.DataFrame(H_prob, index=az_centers, columns=r_centers)
    hist_df.index.name   = "bearing_deg"
    hist_df.columns.name = f"radius_m (bin={r_bin_m})"

    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    hist_df.to_csv(out_csv)
    log.info(f"✅ Histogramm als CSV gespeichert: {out_csv}")

    # ── Polar-Plot wie in deinem Snippet ──────────────────
    theta = np.deg2rad(hist_df.index.astype(float).values)
    r_vals = hist_df.columns.astype(float).values
    T, R = np.meshgrid(theta, r_vals, indexing="ij")

    fig = plt.figure(figsize=(7, 7))
    ax  = fig.add_subplot(111, projection="polar")

    pcm = ax.pcolormesh(T, R, hist_df.values, shading="auto")  # default colormap
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_title("Aufenthalts­wahrsch. je Azimut (5°) und Distanz (500 m)")
    cbar = plt.colorbar(pcm, ax=ax, pad=0.1)
    cbar.set_label("P(Distanz | Azimut)")

    plt.tight_layout()

    if out_png:
        Path(out_png).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_png, dpi=300)
        log.info(f"🖼️  Plot als PNG gespeichert: {out_png}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
# python src/bearing/compute_sector_stats.py --config src/bearing/config/bearing.json