#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/plot_tracks.py

Zeichnet AIS-Tracklinien auf die Basemap aus plotseamap.
Tracks werden segmentweise (MMSI + segment_idx) erzeugt und nur
Gruppen mit ≥2 Punkten geplottet. Der Plot wird standardmäßig
nach src/bearing/processed_data/tracks_plot.png gespeichert.
Override über --output möglich.
"""
import os
import logging
from pathlib import Path
from typing import Optional

import click
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from shapely.geometry import box, Point, LineString

# ───────────────────────────────────────────────────────────────────────
# Logging
# ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────
# Vorkonfigurierte Defaults
# ───────────────────────────────────────────────────────────────────────
DEFAULT_GPKG        = "src/plotseamap/processed_data/gpkg/fehmarnbelt_data.gpkg"
DEFAULT_BUFFER      = "src/plotseamap/processed_data/geojson/fehmarnbelt_buffer.geojson"
DEFAULT_AIS_CSV     = "src/bearing/processed_data/05_distance.csv"
DEFAULT_ANT_LAT     = 54.578614
DEFAULT_ANT_LON     = 11.289016
DEFAULT_RADIUS_KM   = 20.0
DEFAULT_FIGSIZE     = "10,8"
DEFAULT_OUT_PNG     = "src/bearing/processed_data/tracks_plot.png"


@click.command()
@click.option(
    "--gpkg", "gpkg_path",
    default=DEFAULT_GPKG, show_default=True,
    help="GeoPackage mit Basemap-Layern"
)
@click.option(
    "--buffer-geojson", "buffer_path",
    default=DEFAULT_BUFFER, show_default=True,
    help="GeoJSON mit Puffer-Polygon für Extent"
)
@click.option(
    "--ais-csv", "ais_csv",
    default=DEFAULT_AIS_CSV, show_default=True,
    help="AIS-CSV (muss Spalte 'segment_idx' enthalten)"
)
@click.option(
    "--ant-lat", "ant_lat",
    default=DEFAULT_ANT_LAT, show_default=True,
    type=float, help="Antenne Breitengrad"
)
@click.option(
    "--ant-lon", "ant_lon",
    default=DEFAULT_ANT_LON, show_default=True,
    type=float, help="Antenne Längengrad"
)
@click.option(
    "--radius-km", "radius_km",
    default=DEFAULT_RADIUS_KM, show_default=True,
    type=float, help="Plot-Radius um Antenne (km)"
)
@click.option(
    "--figsize", "figsize",
    default=DEFAULT_FIGSIZE, show_default=True,
    help="Figure-Größe 'width,height' in Zoll"
)
@click.option(
    "--output", "out_png",
    default=DEFAULT_OUT_PNG, show_default=True,
    help="Pfad zum Speichern des PNGs"
)
def main(
    gpkg_path: str,
    buffer_path: str,
    ais_csv: str,
    ant_lat: float,
    ant_lon: float,
    radius_km: float,
    figsize: str,
    out_png: str,
):
    # — Parameter & Logging —
    fig_w, fig_h = map(float, figsize.split(","))
    radius_m     = radius_km * 1000
    crs_plot     = "EPSG:3857"

    log.info(f"Antenne @ ({ant_lat:.6f}, {ant_lon:.6f}), Radius = {radius_km} km")
    log.info(f"Basemap GPKG   : {gpkg_path}")
    log.info(f"Puffer-GeoJSON : {buffer_path}")
    log.info(f"AIS-CSV        : {ais_csv}")
    log.info(f"Figure-Size    : {fig_w}×{fig_h}")
    log.info(f"Output-PNG     : {out_png}")

    # — 1) Extent bestimmen —
    if Path(buffer_path).exists():
        buf = gpd.read_file(buffer_path).to_crs(crs_plot)
        minx, miny, maxx, maxy = buf.total_bounds
        log.info("Extent aus Puffer-GeoJSON geladen")
    else:
        center = Point(ant_lon, ant_lat)
        circle = (
            gpd.GeoSeries([center], crs="EPSG:4326")
               .to_crs(crs_plot)
               .buffer(radius_m)
               .iloc[0]
        )
        minx, miny, maxx, maxy = circle.bounds
        log.info("Extent aus Kreis um Antenne erstellt")

    bbox = box(minx, miny, maxx, maxy)
    bbox_gdf = gpd.GeoDataFrame(geometry=[bbox], crs=crs_plot)

    # — 2) Basemap laden & klassifizieren —
    mp_layer = "multipolygons"
    gdf = gpd.read_file(gpkg_path, layer=mp_layer).to_crs(crs_plot)
    gdf = gpd.clip(gdf, bbox)
    log.info(f"{len(gdf):,} Polygone aus '{mp_layer}' geladen und geclippt")

    wasser_tags = ["water","wetland","bay","beach","strait","sand","shingle","mud"]
    water = gdf[
        gdf.get("natural","").isin(wasser_tags) |
        (gdf.get("seamark:sea_area:category","") != "")
    ]
    mil  = gdf[gdf.get("landuse","") == "military"]
    prot = gdf[gdf.get("boundary","") == "protected_area"]
    land = gdf.drop(water.index.union(mil.index).union(prot.index))
    log.info(f"Land:{len(land):,}, Wasser:{len(water):,}, Mil:{len(mil):,}, Prot:{len(prot):,}")

    # — 3) AIS-Tracks pro Segment erzeugen & clippen —
    df = pd.read_csv(ais_csv, parse_dates=["# Timestamp"])
    df = df.sort_values(["MMSI", "# Timestamp"])
    log.info(f"{len(df):,} AIS-Meldungen geladen")

    def make_line(pts: pd.DataFrame) -> Optional[LineString]:
        coords = pts.values
        return LineString(coords) if len(coords) > 1 else None

    seg_tracks = df.groupby(["MMSI", "segment_idx"])[["Longitude","Latitude"]]
    lines = seg_tracks.apply(make_line).dropna()
    tracks_gdf = gpd.GeoDataFrame({
        "MMSI":        lines.index.get_level_values(0),
        "segment_idx": lines.index.get_level_values(1),
    }, geometry=lines.values, crs="EPSG:4326") \
        .to_crs(crs_plot)

    tracks_clipped = gpd.clip(tracks_gdf, bbox)
    log.info(f"{len(tracks_clipped):,} Tracks im Radius-Extent verbleibend")

    # — 4) Plotten —
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    bbox_gdf.plot(ax=ax, color="#d0e7f9", zorder=0)
    land.plot(ax=ax, facecolor="#f5f2eb", edgecolor="gray", lw=0.5, zorder=1)
    water.plot(ax=ax, facecolor="#a6cee3", edgecolor="black", lw=0.5, zorder=2)
    mil.plot(ax=ax, facecolor="red", edgecolor="#8B0000",
             alpha=0.4, linestyle="--", lw=1.5, zorder=3)
    prot.plot(ax=ax, facecolor="none", edgecolor="green", lw=1.5, zorder=4)

    tracks_clipped.plot(ax=ax, color="crimson", lw=0.7, alpha=0.6, zorder=5)

    ant_pt = (
        gpd.GeoSeries([Point(ant_lon, ant_lat)], crs="EPSG:4326")
           .to_crs(crs_plot)
    )
    ant_pt.plot(ax=ax, color="blue", marker="*", markersize=100, zorder=6)

    handles = [
        mpatches.Patch(facecolor="#f5f2eb", edgecolor="gray", label="Land"),
        mpatches.Patch(facecolor="#a6cee3", edgecolor="black", label="Wasser"),
        Line2D([0],[0], marker="s", color="none",
               markerfacecolor="red", markeredgecolor="#8B0000",
               linestyle="--", label="Military"),
        Line2D([0],[0], color="green", lw=2, label="Protected"),
        Line2D([0],[0], color="crimson", lw=1, label="AIS-Tracks"),
        Line2D([0],[0], marker="*", color="blue",
               linestyle="None", markersize=10, label="Antenne"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=8)

    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.axis("off")
    ax.set_title(f"AIS-Tracks ±{radius_km:.0f} km um Antenne", pad=16)
    plt.tight_layout()

    # — 5) Speichern / Anzeigen —
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    log.info(f"Plot gespeichert: {out_png}")


if __name__ == "__main__":
    main()


# python src/bearing/plot_tracks.py   