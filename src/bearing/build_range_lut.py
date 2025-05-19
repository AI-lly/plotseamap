#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_range_lut.py

Erstellt aus einem AIS-Datensatz eine Lookup-Tabelle
P(R | bearing_bin, bearing_rate_bin) und speichert sie als Pickle.
"""
from __future__ import annotations
import os, pickle, numpy as np, pandas as pd

# ------------------------------------------------------------------
# PARAMETER – bei Bedarf anpassen oder via argparse/Cli übergeben
# ------------------------------------------------------------------
CSV_PATH    = (
    "data/processed/bearing/ais_with_distance.csv"
)  # Eingabe-Datei mit Spalten: bearing, bearing_rate, dist_m

AZ_BIN_DEG  = 5
RATE_EDGES  = [0, .01, .03, .1, .3, 1, 3, 10]          # °/s, linker Rand
R_STEP_M    = 500
R_MAX_M     = 20_000

OUT_PKL     = "data/processed/bearing/range_lut.pkl"
# ------------------------------------------------------------------


def main() -> None:
    # 0) Daten laden
    df = pd.read_csv(CSV_PATH, usecols=["bearing", "bearing_rate", "dist_m"])
    print("Zeilen geladen:", len(df))

    # 1) Bearing-Bin
    df["bearing_bin"] = (df["bearing"] // AZ_BIN_DEG) * AZ_BIN_DEG

    # 2) Rate-Bin
    df["bearing_rate_abs"] = df["bearing_rate"].abs()
    df["bearing_rate_bin"] = (
        pd.cut(
            df["bearing_rate_abs"],
            bins=RATE_EDGES,
            right=False,
            labels=RATE_EDGES[:-1],
        ).astype(float)
    )

    # 3) Distanz-Bin
    range_vec = np.arange(0, R_MAX_M, R_STEP_M) + R_STEP_M / 2
    df["dist_bin"] = (df["dist_m"] // R_STEP_M).clip(
        upper=len(range_vec) - 1
    ).astype(int)

    # 4) Histogramm
    AZ_BINS, RATE_BINS, R_BINS = (
        360 // AZ_BIN_DEG,
        len(RATE_EDGES) - 1,
        len(range_vec),
    )
    hist = np.zeros((AZ_BINS, RATE_BINS, R_BINS), dtype=int)

    rate_val_to_idx = {v: i for i, v in enumerate(RATE_EDGES[:-1])}
    grp_counts = (
        df.groupby(["bearing_bin", "bearing_rate_bin", "dist_bin"])
        .size()
        .items()
    )

    for (be_bin, ra_bin, dist_bin), cnt in grp_counts:
        if pd.isna(ra_bin):
            continue
        be_i = int(be_bin / AZ_BIN_DEG)
        ra_i = rate_val_to_idx[ra_bin]
        hist[be_i, ra_i, int(dist_bin)] = cnt

    # 5) Zeilenweise normieren
    row_sums = hist.sum(axis=2, keepdims=True)
    prob_cube = np.divide(hist, row_sums, where=row_sums != 0).astype("float32")

    # 6) Speichern
    os.makedirs(os.path.dirname(OUT_PKL), exist_ok=True)
    pickle.dump(
        {
            "params": {
                "az_bin_deg": AZ_BIN_DEG,
                "rate_edges": RATE_EDGES,
                "range_vec": range_vec.tolist(),
            },
            "prob_cube": prob_cube,
        },
        open(OUT_PKL, "wb"),
    )
    print("✅ Lookup-Tabelle gespeichert →", OUT_PKL)


if __name__ == "__main__":
    main()

# python src/bearing/build_range_lut.py 