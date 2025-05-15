#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/compute_distance.py

Berechnet den ellipsoidischen Abstand (Meter) zwischen einer festen Antenne
und jedem AIS-Punkt (Lat/Lon) mittels pyproj.Geod.inv.

Aufruf:
    python src/bearing/compute_distance.py \
        --config src/bearing/config/bearing.json
"""
from __future__ import annotations

import os
import json
import logging

import click
import pandas as pd
import numpy as np
from pyproj import Geod

# ───────────────────────────── Logging ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)


# ───────────────────────────── CLI ─────────────────────────────
@click.command()
@click.option(
    "--config", "cfg_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur bearing.json",
)
def main(cfg_path: str) -> None:
    # 1) Config laden
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    log.info(f"→ Config geladen: {cfg_path}")

    # Dateipfade
    in_csv  = cfg["output"]["with_rate_csv"]
    out_csv = cfg["output"].get("with_distance_csv",
                                "data/processed/bearing/ais_with_distance.csv")

    # Spalten
    lat_col = cfg["lat_column"]
    lon_col = cfg["lon_column"]
    dist_col = cfg.get("distance_column", "dist_m")

    # Antennen-Koordinaten
    ant_lat = cfg["antenna"]["latitude"]
    ant_lon = cfg["antenna"]["longitude"]

    # 2) Daten laden
    log.info(f"📥 Lade AIS-Daten: {in_csv}")
    df = pd.read_csv(in_csv, low_memory=False)
    log.info(f"→ {len(df):,} Zeilen geladen")

    # 3) Koordinaten in Float casten
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    before = len(df)
    df = df.dropna(subset=[lat_col, lon_col])
    if before != len(df):
        log.info(f"⚠️  {before-len(df):,} Zeilen mit ungültigen Koordinaten verworfen")

    # 4) Distanz berechnen (vectorisiert)
    geod = Geod(ellps="WGS84")
    log.info("📏 Berechne Distanzen …")

    _, _, dist = geod.inv(
        np.full(len(df), ant_lon, dtype=float),
        np.full(len(df), ant_lat, dtype=float),
        df[lon_col].to_numpy(dtype=float),
        df[lat_col].to_numpy(dtype=float)
    )
    df[dist_col] = dist        # Meter

    # 5) Speichern
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=False)
    log.info(f"✅ Datei mit Distanz gespeichert: {out_csv}")


# ───────────────────────── Entry-Point ─────────────────────────
if __name__ == "__main__":
    main()

# python src/bearing/compute_distance.py --config src/bearing/config/bearing.json