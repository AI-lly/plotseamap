#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/lookup_range.py

Lädt die Pickle-Lookup-Tabelle und bietet:
• eine Funktion lookup_range_pdf(theta, omega, lut)
• ein CLI-Beispiel: Bearing + Bearing-Rate → Erwartungsdistanz & Quantile
"""
import argparse
import logging
import pickle
import numpy as np
from pathlib import Path
from typing import Union, Tuple, Optional

# ───────────────────────────────────────────────────────────────────────
# Logging konfigurieren
# ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Standard-Pfad zur LUT
LUT_PATH = Path("src/bearing/processed_data/range_lut.pkl")


def load_lut(path: Union[str, Path] = LUT_PATH) -> dict:
    """
    Lädt die Pickle-LUT von `path` und gibt das Dict zurück.
    """
    logger.info(f"📂 Lade Lookup-Tabelle: {path}")
    with open(path, "rb") as f:
        lut = pickle.load(f)
    logger.info("→ Lookup-Tabelle geladen")
    return lut


def lookup_range_pdf(
    theta: float,
    omega: float,
    lut: dict
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Liefert (range_vec, pdf) für gegebenen Bearing (θ) und Rate (ω).
    Gibt (None, None) zurück, wenn keine gültige Kombination existiert.
    """
    p = lut["params"]
    cube = lut["prob_cube"]

    # 1) Bearing-Bin-Index
    be_i = int((theta % 360) // p["az_bin_deg"])
    logger.debug(f"Bearing θ={theta}° → Bin-Index {be_i}")

    # 2) Rate-Bin-Index
    abs_ω = abs(omega)
    edges = p["rate_edges"]
    ra_i = np.searchsorted(edges, abs_ω, side="right") - 1
    logger.debug(f"Rate |ω|={abs_ω}°/s → Bin-Index {ra_i}")

    # ungültiger Rate-Index?
    if ra_i < 0 or ra_i >= cube.shape[1]:
        logger.warning("⚠️  Rate außerhalb definierter Bins")
        return None, None

    # 3) PDF extrahieren
    pdf = cube[be_i, ra_i]
    if pdf.sum() == 0:
        logger.warning("⚠️  Keine historisierten Daten für diese (θ, ω)-Kombination")
        return None, None

    return np.array(p["range_vec"]), pdf


def main():
    parser = argparse.ArgumentParser(
        description="Lookup Distanz-PDF aus Bearing & Bearing-Rate"
    )
    parser.add_argument(
        "bearing", type=float,
        help="Bearing in Grad (0 = Nord, im Uhrzeigersinn)"
    )
    parser.add_argument(
        "bearing_rate", type=float,
        help="Bearing-Rate in Grad pro Sekunde"
    )
    parser.add_argument(
        "--lut", "-l",
        dest="lut_path",
        default=str(LUT_PATH),
        help="Pfad zur Lookup-Tabelle (Pickle)"
    )
    args = parser.parse_args()

    # 1) LUT laden
    lut = load_lut(args.lut_path)

    # 2) PDF abrufen
    logger.info(f"🔍 Suche PDF für θ={args.bearing}°, ω={args.bearing_rate}°/s")
    range_vec, pdf = lookup_range_pdf(args.bearing, args.bearing_rate, lut)

    if pdf is None:
        logger.error("Abbruch: Kein Ergebnis für diese Parameterkombination.")
        return

    # 3) Erwartungswert & Quantile berechnen
    exp_r = (range_vec * pdf).sum()
    q10 = np.interp(0.1, pdf.cumsum(), range_vec)
    q90 = np.interp(0.9, pdf.cumsum(), range_vec)
    logger.info(f"E[R]  ≈ {exp_r:,.0f} m")
    logger.info(f"Q10–Q90 ≈ {q10:,.0f} – {q90:,.0f} m")

    # 4) Top-5 Wahrscheinlichkeiten
    top5_idx = np.argsort(pdf)[-5:][::-1]
    logger.info("Top-5 Wahrscheinlichkeiten:")
    for idx in top5_idx:
        r = range_vec[idx]
        p = pdf[idx]
        logger.info(f"  R ≈ {r:6.0f} m   P = {p:.3f}")


if __name__ == "__main__":
    main()

# python src/bearing/lookup_range.py 88 -0.042 --lut src/bearing/processed_data/range_lut.pkl