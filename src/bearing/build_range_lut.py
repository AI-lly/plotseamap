#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/build_range_lut.py

Erstellt aus einem AIS-Datensatz eine Lookup-Tabelle
P(r | bearing_bin, bearing_rate_bin) und speichert sie als Pickle.
Input- und Output-Pfade kommen aus dem Abschnitt "statistics" der JSON-Config.
"""
import os
import json
import pickle
import numpy as np
import pandas as pd
import click

@click.command()
@click.option(
    "--config", "cfg_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur bearing.json"
)
def main(cfg_path: str) -> None:
    # 1) Config laden
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # 2) Pfade aus Config
    csv_path = cfg["output"]["with_distance_csv"]
    out_pkl  = cfg["statistics"]["output"]

    # 3) Raster-Parameter aus Config (Falle auf Defaults zurück)
    AZ_BIN_DEG = cfg["statistics"]["az_bin_deg"]
    RATE_EDGES = cfg["statistics"]["rate_edges"]
    R_STEP_M   = cfg["statistics"]["r_step_m"]
    R_MAX_M    = cfg["statistics"]["r_max_m"]

    # 4) Daten einlesen
    df = pd.read_csv(
        csv_path,
        usecols=["bearing", "bearing_rate", cfg.get("distance_column", "dist_m")],
        low_memory=False
    )
    click.echo(f"📥  {len(df):,} Zeilen geladen")

    # 5) Bearing-Bins
    df["bearing_bin"] = (df["bearing"] // AZ_BIN_DEG) * AZ_BIN_DEG

    # 6) Rate-Bins
    df["bearing_rate_abs"] = df["bearing_rate"].abs()
    df["bearing_rate_bin"] = (
        pd.cut(
            df["bearing_rate_abs"],
            bins=RATE_EDGES,
            right=False,
            labels=RATE_EDGES[:-1]
        ).astype(float)
    )

    # 7) Distanz-Bins
    range_vec = np.arange(0, R_MAX_M, R_STEP_M) + R_STEP_M / 2
    df["dist_bin"] = (
        (df[cfg.get("distance_column", "dist_m")] // R_STEP_M)
        .clip(upper=len(range_vec) - 1)
        .astype(int)
    )

    # 8) 3-D-Histogramm (θ × ω × r)
    AZ_BINS, RATE_BINS, R_BINS = (
        360 // AZ_BIN_DEG,
        len(RATE_EDGES) - 1,
        len(range_vec)
    )
    hist = np.zeros((AZ_BINS, RATE_BINS, R_BINS), dtype=int)
    rate_to_idx = {v: i for i, v in enumerate(RATE_EDGES[:-1])}

    for (b_bin, r_bin, d_idx), cnt in df.groupby(
        ["bearing_bin", "bearing_rate_bin", "dist_bin"]
    ).size().items():
        if pd.isna(r_bin):
            continue
        i_b = int(b_bin / AZ_BIN_DEG)
        i_r = rate_to_idx[r_bin]
        hist[i_b, i_r, int(d_idx)] = cnt

    # 9) Zeilenweise Normierung → P(r | θ, ω)
    sums = hist.sum(axis=2, keepdims=True)
    prob_cube = np.divide(hist, sums, where=sums != 0).astype("float32")

    # 10) Pickle speichern
    os.makedirs(os.path.dirname(out_pkl), exist_ok=True)
    with open(out_pkl, "wb") as f:
        pickle.dump({
            "params": {
                "az_bin_deg": AZ_BIN_DEG,
                "rate_edges": RATE_EDGES,
                "range_vec":  range_vec.tolist()
            },
            "prob_cube": prob_cube
        }, f)
    click.echo(f"✅ Lookup-Tabelle gespeichert: {out_pkl}")


if __name__ == "__main__":
    main()

# python src/bearing/build_range_lut.py 