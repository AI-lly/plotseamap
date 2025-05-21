#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/compute_bearing.py

Berechnet die initiale Peilung (bearing) von einer festen Antenne zu jedem
AIS‑Punkt. Verwendet eine ellipsoidische Lösung (WGS‑84) via pyproj.Geod.inv.

⏩ Aufruf:
    python src/bearing/compute_bearing.py --config src/bearing/config/bearing.json
"""
import os
import json
import logging

import click
import pandas as pd
import numpy as np
from pyproj import Geod


# ──────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────
@click.command()
@click.option(
    "--config", "cfg_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur bearing.json",
)
def main(cfg_path: str) -> None:
    # ------------------------------------------------------------------
    # 1) Config laden
    # ------------------------------------------------------------------
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    log.info(f"→ Config geladen: {cfg_path}")

    # Relevante Parameter extrahieren
    in_csv      = cfg["output"]["interpolated_csv"]
    out_csv     = cfg["output"]["with_bearing_csv"]
    lat_col     = cfg["lat_column"]
    lon_col     = cfg["lon_column"]
    ts_col      = cfg["timestamp_column"]           # aktuell nur mitgeladen
    bearing_col = cfg.get("bearing_column", "bearing")

    ant_lat = cfg["antenna"]["latitude"]
    ant_lon = cfg["antenna"]["longitude"]

    # ------------------------------------------------------------------
    # 2) AIS‑Daten laden
    # ------------------------------------------------------------------
    log.info(f"📥 Lade AIS‑Daten: {in_csv}")
    df = pd.read_csv(
        in_csv,
        low_memory=False,          # schnelleres Laden, kein dtype‑Guessing
        # Nur benötigte Spalten; Timestamp ggf. später noch relevant
        usecols=[lat_col, lon_col, ts_col, "MMSI", "Destination", "segment_idx", "Ship type"],
    )
    log.info(f"→ {len(df):,} Zeilen geladen")

    # ------------------------------------------------------------------
    # 3) Koordinaten säubern
    # ------------------------------------------------------------------
    # Nicht‑numerische Werte in NaN umwandeln
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")

    before = len(df)
    df = df.dropna(subset=[lon_col, lat_col])
    after = len(df)
    if before != after:
        log.info(f"⚠️  {before - after:,} Zeilen wegen fehlender Koordinaten verworfen")

    # ------------------------------------------------------------------
    # 4) Bearing berechnen (pyproj.Geod.inv)
    # ------------------------------------------------------------------
    geod = Geod(ellps="WGS84")
    log.info("🔢 Berechne Bearing …")

    n = len(df)
    lon1_arr = np.full(n, ant_lon, dtype=float)
    lat1_arr = np.full(n, ant_lat, dtype=float)

    az12, _, _ = geod.inv(
        lon1_arr,
        lat1_arr,
        df[lon_col].to_numpy(dtype=float),
        df[lat_col].to_numpy(dtype=float),
    )

    # Normalisierung auf 0 – <360°
    df[bearing_col] = np.mod(az12, 360.0)

    # ------------------------------------------------------------------
    # 5) Ergebnis speichern
    # ------------------------------------------------------------------
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=False)
    log.info(f"✅ Datei mit Peilung gespeichert: {out_csv}")


# ──────────────────────────────────────────────────────────────
# Entry‑Point
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()

# python src/bearing/compute_bearing.py --config src/bearing/config/bearing.json