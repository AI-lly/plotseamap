#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lookup_range.py

Lädt die Pickle-Lookup-Tabelle und bietet:
• eine Funktion lookup_range_pdf(theta, omega, lut)
• ein kleines CLI-Beispiel: bearing + bearing_rate → Erwartungsdistanz
"""
from __future__ import annotations
import argparse, pickle, numpy as np
from pathlib import Path

LUT_PATH = Path("data/processed/bearing/range_lut.pkl")


def load_lut(path: str | Path = LUT_PATH):
    with open(path, "rb") as f:
        return pickle.load(f)


def lookup_range_pdf(theta: float, omega: float, lut: dict):
    p = lut["params"]
    cube = lut["prob_cube"]

    # Bearing-Bin-Index
    be_i = int((theta % 360) // p["az_bin_deg"])

    # Rate-Bin-Index
    abs_ω = abs(omega)
    edges = p["rate_edges"]
    ra_i = np.searchsorted(edges, abs_ω, side="right") - 1
    if ra_i < 0 or ra_i >= len(edges) - 1:
        return None, None

    pdf = cube[be_i, ra_i]
    if pdf.sum() == 0:
        return None, None

    return np.array(p["range_vec"]), pdf


def main():
    parser = argparse.ArgumentParser(
        description="Lookup Distanz-PDF aus Bearing & Bearing-Rate"
    )
    parser.add_argument("bearing", type=float, help="Bearing in Deg (0=N)")
    parser.add_argument("bearing_rate", type=float, help="Bearing-Rate in Deg/s")
    args = parser.parse_args()

    lut = load_lut()
    range_vec, pdf = lookup_range_pdf(args.bearing, args.bearing_rate, lut)

    if pdf is None:
        print("⚠️  Keine Historie für diese Kombination.")
        return

    exp_r = (range_vec * pdf).sum()
    q10 = np.interp(0.1, pdf.cumsum(), range_vec)
    q90 = np.interp(0.9, pdf.cumsum(), range_vec)

    print(f"E[R]  ≈ {exp_r:,.0f} m")
    print(f"Q10–Q90 ≈ {q10:,.0f} – {q90:,.0f} m")
    print("Top-5 Wahrscheinlichkeiten:")
    for r, p in sorted(zip(range_vec, pdf), key=lambda t: -t[1])[:5]:
        print(f"  R ≈ {r:6.0f} m   P={p:.3f}")


if __name__ == "__main__":
    main()

# python src/bearing/lookup_range.py 88 -0.042