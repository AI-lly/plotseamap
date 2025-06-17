#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/demo/plot_bcr_hist.py

Erzeugt zwei Histogramme der Bearing-Change-Rate aus einer AIS-CSV:
  - links: Signed (inkl. negativer Werte)
  - rechts: Absolutwerte

Berechnet und gibt aus:
  • 5 %– und 95 %–Quantile der signierten Werte
  • 5 %– und 95 %–Quantile der Absolutwerte

Alle Einstellungen (Pfad, Spalte, Bins, Log-Skala etc.) sind im Skript definiert.
"""
import os
import logging
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# ───────────────────────────────────────────────────────────────────────
# Logging konfigurieren
# ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────
# Konfiguration (hier anpassen)
# ───────────────────────────────────────────────────────────────────────
INPUT_CSV   = Path("src/bearing/processed_data/05_distance.csv")
COLUMN      = "bearing_rate"
BINS        = 200
LOG_SCALE   = True
OUTPUT_PNG  = Path("src/bearing/visualize/bcr_hist_signed_abs.png")


def main():
    # 1) Daten lesen
    logger.info(f"📥 Lade Bearing-Change-Rate aus: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV, usecols=[COLUMN])
    rates_signed = df[COLUMN].dropna()
    rates_abs    = rates_signed.abs()

    # 2) 5 %– und 95 %–Quantile berechnen
    q_low_s, q_high_s = rates_signed.quantile([0.05, 0.95])
    q_low_a, q_high_a = rates_abs.quantile([0.05, 0.95])
    logger.info(
        f"Signed:   90 % der Werte liegen zwischen "
        f"{q_low_s:.6f} … {q_high_s:.6f} °/s"
    )
    logger.info(
        f"Absolute: 90 % der Werte liegen zwischen "
        f"{q_low_a:.6f} … {q_high_a:.6f} °/s"
    )

    # 3) Plot aufsetzen
    fig, (ax1, ax2) = plt.subplots(
        ncols=2, figsize=(12, 4), sharey=True
    )

    # 3a) Signed-Histogramm
    ax1.hist(
        rates_signed,
        bins=BINS,
        density=True,
        log=LOG_SCALE,
        edgecolor="black",
        alpha=0.7
    )
    ax1.set_title("Bearing-Change-Rate (signed)")
    ax1.set_xlabel(f"{COLUMN} (°/s)")
    ax1.set_ylabel("Dichte" + (" (log)" if LOG_SCALE else ""))

    # 3b) Absolut-Histogramm
    ax2.hist(
        rates_abs,
        bins=BINS,
        density=True,
        log=LOG_SCALE,
        edgecolor="black",
        alpha=0.7
    )
    ax2.set_title("Bearing-Change-Rate (absolute Werte)")
    ax2.set_xlabel(f"|{COLUMN}| (°/s)")

    # 3c) Gitter & Layout
    for ax in (ax1, ax2):
        ax.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()

    # 4) Speichern
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PNG, dpi=300)
    logger.info(f"Histogramme gespeichert: {OUTPUT_PNG}")


if __name__ == "__main__":
    main()

# python src/bearing/visualize/plot_bcr_hist.py