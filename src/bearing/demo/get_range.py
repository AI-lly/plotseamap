#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/demo/get_range.py

  • load_lut(path) -> dict
  • get_range_distribution(theta, omega, lut)
        -> (range_vec, pdf, counts) oder (None, None, None)

Am Ende ein kurzes Beispiel, das VecRange, VecProb und VecCount ausgibt.
"""
import logging
import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

# ───────────────────────────────────────────────────────────────────────
# configure logging (can be overridden in your application)
# ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────
# default path to the lookup‐table pickle
# ───────────────────────────────────────────────────────────────────────
DEFAULT_LUT_PATH = Path("src/bearing/demo/lut.pkl")


def load_lut(path: Path = DEFAULT_LUT_PATH) -> Dict:
    """
    Load the pickle file with the lookup‐table and return its dict.

    Expects a dict with keys:
      - "params": {
            "az_bin_deg": int,
            "rate_edges": list of float,
            "range_vec": list of float
        }
      - "prob_cube": numpy array of shape (n_az, n_rate, n_r)
      - "counts_cube": numpy array of same shape (n_az, n_rate, n_r)
    """
    logger.info(f"Loading LUT from {path}")
    with open(path, "rb") as f:
        lut = pickle.load(f)
    logger.info("LUT loaded")
    return lut


def get_range_distribution(
    theta: float,
    omega: float,
    lut: Dict
) -> Tuple[
    Optional[np.ndarray],  # range_vec
    Optional[np.ndarray],  # pdf
    Optional[np.ndarray]   # counts
]:
    """
    Return (range_vec, pdf, counts) for a given bearing 'theta' (deg)
    and bearing‐rate 'omega' (deg/s). Returns (None,None,None) if the
    combination is not covered by the LUT.

    - range_vec : centers of the distance bins (meters)
    - pdf       : P(r | θ, ω) over the distance bins
    - counts    : absolute histogram counts for that (θ, ω)
    """
    params      = lut["params"]
    prob_cube   = lut["prob_cube"]    # shape = (n_az, n_rate, n_r)
    counts_cube = lut.get("counts_cube")

    # 1) find azimuth bin index
    az_bin_deg = params["az_bin_deg"]
    az_index   = int((theta % 360) // az_bin_deg)

    # 2) find rate bin index (using absolute value)
    edges       = params["rate_edges"]
    rate_index  = np.searchsorted(edges, omega, side="right") - 1

    # check validity
    if az_index < 0 or az_index >= prob_cube.shape[0] or \
       rate_index < 0 or rate_index >= prob_cube.shape[1]:
        logger.warning("theta or omega outside defined bins")
        return None, None, None

    # 3) extract pdf and counts
    pdf    = prob_cube[az_index, rate_index]
    counts = counts_cube[az_index, rate_index] if counts_cube is not None else None

    # 4) check for empty
    if pdf.sum() == 0:
        logger.warning("no data for this theta/omega combination")
        return None, None, None

    # 5) return range vector, pdf and counts
    range_vec = np.array(params["range_vec"])
    return range_vec, pdf, counts


# ───────────────────────────────────────────────────────────────────────
# simple usage example
# ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 1) load LUT
    lut = load_lut()  # or load_lut(Path("other/path/range_lut.pkl"))

    # 2) choose example values
    theta = 88.0
    omega = -0.042

    # 3) get distributions
    range_vec, pdf, counts = get_range_distribution(theta, omega, lut)

    if pdf is not None:
        print("VecRange (meters):")
        print(range_vec)
        print("\nVecProb (probabilities):")
        print(pdf)
        print("\nVecCount (absolute counts):")
        print(counts)
    else:
        print("No valid theta/omega combination found.")