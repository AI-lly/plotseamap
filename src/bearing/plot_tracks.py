#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/plot_tracks.py

Zeichnet AIS-Tracklinien auf die Basemap aus plotseamap.
Tracks werden segmentweise (MMSI + segment_idx) erzeugt und nur
Gruppen mit ≥2 Punkten geplottet. Nur AIS-Punkte innerhalb des
Radius um die Antenne werden überhaupt verarbeitet.
Der Plot wird standardmäßig nach src/bearing/processed_data/tracks_plot.png
gespeichert. Override über --output möglich.
"""
import os
import logging
from pathlib import Path

import click
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from shapely.geometry import box, Point, LineString

# ───────────────────────────────────────────────────────────────────────
# Logging konfigurieren
# ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────
# Vorkonfigurierte Defaults
# ───────────────────────────────────────────────────────────────────────
DEFAULT_GPKG       = "src/plotseamap/processed_data/gpkg/fehmarnbelt_data.gpkg"
DEFAULT_BUFFER     = "src/plotseamap/processed_data/geojson/fehmarnbelt_buffer.geojson"
DEFAULT_AIS_CSV    = "src/bearing/processed_data/05_distance.csv"
DEFAULT_ANT_LAT    = 54.578614
DEFAULT_ANT_LON    = 11.289016
DEFAULT_RADIUS_KM  = 20.0
DEFAULT_FIGSIZE    = "10,8"
DEFAULT_OUT_PNG    = "src/bearing/processed_data/tracks_plot.png"

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
    help="AIS-CSV (muss col 'segment_idx' enthalten)"
)
@click.option(
    "--ant-lat", "ant_lat",
    default=DEFAULT_ANT_LAT, show_default=True, type=float,
    help="Antenne-Breitengrad"
)
@click.option(
    "--ant-lon", "ant_lon",
    default=DEFAULT_ANT_LON, show_default=True, type=float,
    help="Antenne-Längengrad"
)
@click.option(
    "--radius-km", "radius_km",
    default=DEFAULT_RADIUS_KM, show_default=True, type=float,
    help="Radius um Antenne in km"
)
@click.option(
    "--figsize", "figsize",
    default=DEFAULT_FIGSIZE, show_default=True,
    help="Figure-Größe als 'width,height' in Zoll"
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
    # ─────────────── Parameter parsen & loggen ──────────────────────────
    fig_w, fig_h = map(float, figsize.split(","))
    crs_plot     = "EPSG:3857"
    radius_m     = radius_km * 1_000

    log.info(f"Antenne @ ({ant_lat:.6f}, {ant_lon:.6f}), Radius = {radius_km} km")
    log.info(f"Basemap-GPKG: {gpkg_path}")
    log.info(f"Puffer-GeoJSON: {buffer_path}")
    log.info(f"AIS-CSV: {ais_csv}")
    log.info(f"Figure size: {fig_w}×{fig_h}")
    log.info(f"Output PNG: {out_png}")

    # ─────────────── 1) Extent bestimmen ───────────────────────────────
    if Path(buffer_path).exists():
        buf = gpd.read_file(buffer_path).to_crs(crs_plot)
        minx, miny, maxx, maxy = buf.total_bounds
        log.info("Extent aus Puffer-GeoJSON geladen")
    else:
        centre = Point(ant_lon, ant_lat)
        circle = (
            gpd.GeoSeries([centre], crs="EPSG:4326")
               .to_crs(crs_plot)
               .buffer(radius_m)
               .iloc[0]
        )
        minx, miny, maxx, maxy = circle.bounds
        log.info("Extent aus Kreis um Antenne erstellt")

    bbox     = box(minx, miny, maxx, maxy)
    bbox_gdf = gpd.GeoDataFrame(geometry=[bbox], crs=crs_plot)

    # ─────────────── 2) Basemap laden + klassifizieren ────────────────
    mp = gpd.read_file(gpkg_path, layer="multipolygons").to_crs(crs_plot)
    mp = gpd.clip(mp, bbox)
    wasser_tags = ["water","wetland","bay","beach","strait","sand","shingle","mud"]
    water = mp[
        mp.get("natural","").isin(wasser_tags)
        | (mp.get("seamark:sea_area:category","") != "")
    ]
    mil   = mp[mp.get("landuse","")=="military"]
    prot  = mp[mp.get("boundary","")=="protected_area"]
    land  = mp.drop(water.index.union(mil.index).union(prot.index))
    log.info(f"Basemap: Land={len(land):,}, Wasser={len(water):,}, Mil={len(mil):,}, Prot={len(prot):,}")

    # ─────────────── 3) AIS-Daten einlesen + radial filtern ───────────
    df = pd.read_csv(ais_csv, parse_dates=["# Timestamp"], low_memory=False)
    # GeoDataFrame mit nur den nötigen Spalten + Geometrie
    gdf = gpd.GeoDataFrame(
        df[["MMSI","segment_idx","# Timestamp","Longitude","Latitude","Ship type"]],
        geometry=gpd.points_from_xy(df.Longitude, df.Latitude),
        crs="EPSG:4326"
    ).to_crs(crs_plot)
    # nur Punkte innerhalb des Kreises behalten
    gdf = gdf[gdf.geometry.within(bbox)]
    log.info(f"AIS-Punkte im Radius: {len(gdf):,} (von {len(df):,})")

    # ─────────────── 4) Plot aufbauen ───────────────────────────────────
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    # Hinter­grund
    bbox_gdf.plot(ax=ax, color="#d0e7f9", zorder=0)
    land  .plot(ax=ax, facecolor="#f5f2eb", edgecolor="gray", linewidth=0.5, zorder=1)
    water .plot(ax=ax, facecolor="#a6cee3", edgecolor="black", linewidth=0.5, zorder=2)
    mil   .plot(ax=ax, facecolor="red", edgecolor="#8B0000", alpha=0.4,
                linestyle="--", linewidth=1.5, zorder=3)
    prot  .plot(ax=ax, facecolor="none", edgecolor="green", linewidth=1.5, zorder=4)

    # ─────────────── 5) Pro Ship type Linien erzeugen & plotten ───────
    for ship_type, sub in gdf.groupby("Ship type"):
        log.info(f"→ Bearbeite Ship type «{ship_type}», Punkte: {len(sub):,}")
        tracks_lines = []
        mmsi_list    = []
        seg_list     = []

        # gruppiere nach Schiff & Segment
        for (mmsi, seg_id), grp in sub.groupby(["MMSI","segment_idx"], sort=False):
            if len(grp) < 2:
                continue
            grp = grp.sort_values("# Timestamp")
            coords = [(p.x, p.y) for p in grp.geometry]  # p.x,p.y sind schon in EPSG:3857
            tracks_lines.append(LineString(coords))
            mmsi_list.append(mmsi)
            seg_list.append(seg_id)

        log.info(f"   → Erzeugte Tracks: {len(tracks_lines):,}")
        if not tracks_lines:
            continue

        # ← hier den CRS direkt auf crs_plot setzen, kein .to_crs mehr
        tracks_gdf = gpd.GeoDataFrame(
            {"MMSI": mmsi_list, "segment_idx": seg_list},
            geometry=tracks_lines,
            crs=crs_plot
        )

        tracks_gdf.plot(
            ax=ax, linewidth=0.7, alpha=0.6,
            label=ship_type, zorder=5
        )

    # ─────────────── 6) Antenne markieren ──────────────────────────────
    ant_pt = (
        gpd.GeoSeries([Point(ant_lon, ant_lat)], crs="EPSG:4326")
           .to_crs(crs_plot)
    )
    ant_pt.plot(ax=ax, color="blue", marker="*", markersize=100, zorder=6)

    # ─────────────── 7) Legende + Finalisieren ────────────────────────
    handles = [
        mpatches.Patch(facecolor="#f5f2eb", edgecolor="gray",    label="Land"),
        mpatches.Patch(facecolor="#a6cee3", edgecolor="black",   label="Wasser"),
        Line2D([0],[0], marker="s", color="none",
               markerfacecolor="red", markeredgecolor="#8B0000",
               linestyle="--", label="Military"),
        Line2D([0],[0], color="green", lw=2,                   label="Protected"),
        Line2D([0],[0], color="crimson", lw=1,                 label="AIS-Tracks"),
        Line2D([0],[0], marker="*", color="blue", linestyle="None",
               markersize=10, label="Antenne"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=6)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.axis("off")
    ax.set_title(f"AIS-Tracks ±{radius_km:.0f} km um Antenne")
    plt.tight_layout()

    # ─────────────── 8) Speichern ───────────────────────────────────────
    os.makedirs(Path(out_png).parent, exist_ok=True)
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    log.info(f"Plot gespeichert: {out_png}")

if __name__ == "__main__":
    main()


# python src/bearing/plot_tracks.py   