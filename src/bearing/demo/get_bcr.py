#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/demo/get_bcr.py

  * load_lut(path) -> Dict mit LUT-Daten
  * get_bcr_distribution(bearing, lut) -> (rate_intervals, prob_rate, counts_rate)
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Logging (kann in der Anwendung überschrieben werden)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Standard-Pfad zur Lookup-Tabelle
DEFAULT_LUT_PATH = Path("src/bearing/demo/lut.pkl")


def load_lut(path: Path = DEFAULT_LUT_PATH) -> Dict:
    """
    Lädt die Pickle-Datei mit der Lookup-Tabelle und gibt das Dict zurück.
    Erwartet Keys:
      - "params": { "az_bin_deg": int,
                    "rate_edges": list of floats,
                    "range_vec": list of floats }
      - "prob_rate_cube": np.ndarray, shape (n_az, n_rate)
      - "counts_cube":    np.ndarray, shape (n_az, n_rate, n_r)
    """
    logger.info(f"Loading lookup table from: {path}")
    with open(path, "rb") as f:
        lut = pickle.load(f)
    logger.info("Lookup table loaded")
    return lut


def get_bcr_distribution(
    bearing: float,
    lut: Dict
) -> Tuple[List[Tuple[float, float]], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Liefert die Verteilung der Bearing-Change-Rate (omega) für ein gegebenes Bearing.

    Returns:
      * rate_intervals: Liste von (untere, obere) Grenzen der omega-Bins (deg/s)
      * prob_rate:      np.ndarray mit P(omega | bearing), Form (n_rate,)
      * counts_rate:    np.ndarray mit absoluten Zählern, Form (n_rate,)

    Gibt (intervals, None, None) zurück, falls keine Daten vorliegen.
    """
    params = lut.get("params", {})
    rate_edges = params.get("rate_edges", [])
    az_bin_deg = params.get("az_bin_deg", 1)

    prob_rate_cube = lut.get("prob_rate_cube")
    counts_cube = lut.get("counts_cube")

    # 1) Rate-Intervalle aufbauen
    intervals = [(rate_edges[i], rate_edges[i+1]) for i in range(len(rate_edges)-1)]

    if prob_rate_cube is None:
        logger.error("prob_rate_cube fehlt in der LUT")
        return intervals, None, None

    # 2) Azimuth-Bin-Index ermitteln
    az_index = int((bearing % 360) // az_bin_deg)
    if az_index < 0 or az_index >= prob_rate_cube.shape[0]:
        logger.warning("Bearing außerhalb der definierten Azimut-Bins")
        return intervals, None, None

    # 3) Wahrscheinlichkeiten extrahieren
    prob_rate = prob_rate_cube[az_index]

    # 4) Zähler extrahieren (falls vorhanden)
    if counts_cube is not None:
        # counts_cube hat Shape (n_az, n_rate, n_r) → Summe über Distanz-Achse
        counts_rate = counts_cube[az_index].sum(axis=1)
    else:
        counts_rate = None

    return intervals, prob_rate, counts_rate


if __name__ == "__main__":
    # kurzes Usage-Beispiel
    lut = load_lut()
    bearing = 71.0
    intervals, prob_rate, counts_rate = get_bcr_distribution(bearing, lut)

    if prob_rate is not None:
        print(f"P(omega | bearing={bearing}°):")
        for (low, high), p in zip(intervals, prob_rate):
            print(f"  [{low:.10f}, {high:.10f}) deg/s -> P = {p:.10f}")
        if counts_rate is not None:
            print("\nCounts pro Bin:")
            for (low, high), c in zip(intervals, counts_rate):
                print(f"  [{low:.10f}, {high:.10f}) deg/s -> count = {int(c)}")
    else:
        print("Keine Verteilung verfügbar für diesen Bearing.")