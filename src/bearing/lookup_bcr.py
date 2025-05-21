#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/lookup_bcr.py

Pure Library-Version, kein CLI:

  • load_lut(path) → Dict mit LUT-Daten  
  • get_bcr_distribution(theta, lut) → (rate_intervals, prob_rate, counts_rate)
"""
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ───────────────────────────────────────────────────────────────────────
# Logging konfigurieren (kann überschrieben werden)
# ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────
# Default-Pfad zur Lookup-Tabelle (Pickle)
# ───────────────────────────────────────────────────────────────────────
DEFAULT_LUT_PATH = Path("src/bearing/demonstrator/range_lut.pkl")

def load_lut(path: Path = DEFAULT_LUT_PATH) -> Dict:
    """
    Lädt die Pickle-Datei mit der Lookup-Tabelle und gibt das Dict zurück.
    Erwartet ein Dict mit den Keys:
      - "params": { "az_bin_deg": int,
                    "rate_edges": list[float],
                    "range_vec": list[float] }
      - "prob_rate_cube": np.ndarray of shape (n_az, n_rate)
      - "counts_cube":    np.ndarray of shape (n_az, n_rate, n_r)
    """
    logger.info(f"📂 Lade Lookup-Tabelle: {path}")
    with open(path, "rb") as f:
        lut = pickle.load(f)
    logger.info("→ Lookup-Tabelle geladen")
    return lut

def get_bcr_distribution(
    theta: float,
    lut: Dict
) -> Tuple[List[Tuple[float, float]], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Liefert die Verteilung der Bearing-Change-Rate ω für einen gegebenen Bearing θ:

      • rate_intervals : Liste von (untere, obere) Grenzen der ω-Bins (°/s)  
      • prob_rate      : P(ω | θ) aus prob_rate_cube  
      • counts_rate    : absolute Zähler aus counts_cube (summiert über Distanz)

    Gibt (intervals, None, None) zurück, wenn kein prob_rate_cube vorhanden ist,
    oder (intervals, None, None) falls θ außerhalb abgedeckter Bin-Indizes liegt.
    """
    params         = lut.get("params", {})
    edges          = params.get("rate_edges", [])
    az_bin_deg     = params.get("az_bin_deg", 1)
    prob_rate_cube = lut.get("prob_rate_cube")
    counts_cube    = lut.get("counts_cube")

    # 1) Intervalle bauen
    intervals = list(zip(edges[:-1], edges[1:]))

    if prob_rate_cube is None:
        logger.error("❌ 'prob_rate_cube' nicht in LUT enthalten")
        return intervals, None, None

    # 2) az-Bin-Index ermitteln
    be_i = int((theta % 360) // az_bin_deg)
    if be_i < 0 or be_i >= prob_rate_cube.shape[0]:
        logger.warning("⚠️  θ außerhalb definierter Bins")
        return intervals, None, None

    # 3) Wahrscheinlichkeiten extrahieren
    prob_rate = prob_rate_cube[be_i]
    # 4) Zähler extrahieren (falls vorhanden)
    if counts_cube is not None:
        # counts_cube shape (n_az, n_rate, n_r) → summe über Distanz-Achse → (n_az, n_rate)
        counts_rate = counts_cube[be_i].sum(axis=1)
    else:
        counts_rate = None

    return intervals, prob_rate, counts_rate

# ───────────────────────────────────────────────────────────────────────
# Usage-Beispiel
# ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # LUT laden
    lut = load_lut()

    θ = 88.0   # Beispiel-Bearing
    intervals, probs, counts = get_bcr_distribution(θ, lut)

    if probs is not None:
        print(f"P(ω|θ={θ}°):")
        for (low, high), p in zip(intervals, probs):
            print(f"  [{low:.3f}, {high:.3f})°/s → P={p:.3f}")
        if counts is not None:
            print("\nAbsolute Zähler pro Bin:")
            for (low, high), c in zip(intervals, counts):
                print(f"  [{low:.3f}, {high:.3f})°/s → count={int(c)}")
    else:
        print("⚠️  Verteilung nicht verfügbar für diesen θ.")