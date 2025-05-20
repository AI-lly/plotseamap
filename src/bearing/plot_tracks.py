#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/plot_tracks.py

Zeichnet AIS-Tracklinien auf die Basemap aus plotseamap.
Alles innerhalb eines gegebenen Radius um die Antenne wird dargestellt.
"""
import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

# ───────────────────────────────────────────────────────────────────────
# Logging konfigurieren
# ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────
# Konstanten / Pfade
# ───────────────────────────────────────────────────────────────────────
CONFIG_PATH = Path("src/bearing/config/bearing.json")
GPKG_PATH   = Path("src/plotseamap/processed_data/gpkg/fehmarnbelt_data.gpkg")
AIS_CSV     = Path("src/bearing/processed_data/05_distance.csv")
LAYERS      = ["multipolygons", "lines", "multilinestrings"]  # Basemap-Layer

# Radius um Antenne in km
PLOT_RADIUS_KM = 30


def main():
    # 1) Config laden (für Antennen-Koordinaten)
    logger.info(f"→ Lade Config: {CONFIG_PATH}")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    ant_lat = cfg["antenna"]["latitude"]
    ant_lon = cfg["antenna"]["longitude"]
    logger.info(f"→ Antenne bei (lat, lon) = ({ant_lat}, {ant_lon})")
    radius_m = PLOT_RADIUS_KM * 1_000
    logger.info(f"→ Plot-Radius = {PLOT_RADIUS_KM} km ({radius_m:.0f} m)")

    # 2) Basemap laden und in Meter-CRS reprojizieren
    logger.info(f"📂 Lade Basemap aus GeoPackage: {GPKG_PATH}")
    basemap_parts = []
    for layer in LAYERS:
        try:
            g = gpd.read_file(GPKG_PATH, layer=layer).to_crs(epsg=3857)
            basemap_parts.append(g)
            logger.info(f"  Layer '{layer}': {len(g):,} Features")
        except Exception as e:
            logger.warning(f"⚠️  Konnte Layer '{layer}' nicht laden: {e}")
    if not basemap_parts:
        logger.error("Keine Basemap-Layer geladen – Abbruch")
        return
    basemap = gpd.GeoDataFrame(
        pd.concat(basemap_parts, ignore_index=True),
        crs="EPSG:3857"
    )

    # 3) Antennen-Punkt & Kreis-Polygon in Meter-CRS
    ant_point = gpd.GeoSeries(
        [Point(ant_lon, ant_lat)],
        crs="EPSG:4326"
    ).to_crs(epsg=3857).iloc[0]
    circle = ant_point.buffer(radius_m)
    minx, miny, maxx, maxy = circle.bounds
    logger.info(f"  Kreis-Bounds (EPSG:3857): {minx:.0f}, {miny:.0f}, {maxx:.0f}, {maxy:.0f}")

    # 4) Basemap auf Kreis-Extent clippen
    logger.info("🔪 Clippe Basemap auf 30 km-Kreis")
    basemap_clipped = gpd.clip(basemap, circle)

    # 5) AIS-Daten laden und Track-Linien erzeugen
    logger.info(f"📥 Lade AIS-Daten: {AIS_CSV}")
    df = pd.read_csv(AIS_CSV, parse_dates=["# Timestamp"])
    logger.info(f"→ {len(df):,} AIS-Meldungen geladen")

    logger.info("🔗 Erzeuge Track-Linien pro MMSI")
    df_sorted = df.sort_values(["MMSI", "# Timestamp"])
    tracks = df_sorted.groupby("MMSI")[["Longitude", "Latitude"]].apply(
        lambda pts: LineString(pts.values)
    )
    tracks_gdf = gpd.GeoDataFrame(
        {"MMSI": tracks.index.get_level_values(0)},
        geometry=tracks.values,
        crs="EPSG:4326"
    ).to_crs(epsg=3857)
    logger.info(f"→ {len(tracks_gdf):,} Tracks erzeugt")

    # 6) Tracks auf Kreis-Polygon beschneiden
    logger.info("🔪 Clippe Tracks auf 30 km-Kreis")
    tracks_clipped = gpd.clip(tracks_gdf, circle)
    logger.info(f"→ {len(tracks_clipped):,} Tracks im Kreis verbleibend")

    # 7) Plot erstellen
    logger.info("🖼️  Erstelle Plot")
    fig, ax = plt.subplots(figsize=(10, 10))
    basemap_clipped.plot(
        ax=ax, facecolor="#f5f2eb",
        edgecolor="gray", linewidth=0.5, zorder=1
    )
    tracks_clipped.plot(
        ax=ax, linewidth=0.7,
        alpha=0.6, color="crimson", zorder=2
    )
    # Antennenpunkt markieren
    gpd.GeoSeries([ant_point]).plot(
        ax=ax, color="blue", markersize=50,
        marker="*", zorder=3
    )

    # Achsenbegrenzung auf Kreis-Bounds
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    ax.set_axis_off()
    ax.set_title(f"AIS-Tracks (±{PLOT_RADIUS_KM} km um Antenne)", pad=16)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()