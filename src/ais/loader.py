# src/ais/loader.py

import os
import json
import logging
import click
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# ───────────────────────────────────────────────────────────────────────
# Logging konfigurieren
# ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

@click.command()
@click.option(
    "--config", "config_path", required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur AIS-Filter-Config (ais_filters.json)"
)
@click.option(
    "--map-config", "map_config", required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur Map-Config (fehmarnbelt.json)"
)
def cli(config_path: str, map_config: str):
    """
    1) Lädt AIS-CSV und map-Config (lon, lat, radius).
    2) Baut den 40 km-Kreis auf Basis dieser Parameter.
    3) Clippt alle AIS-Punkte in diesen Kreis und wendet ais_filters an.
    4) Speichert das Ergebnis als CSV.
    """
    log.info(f"Starte AIS-Loader mit AIS-Config: {config_path} und Map-Config: {map_config}")

    # ───────────────────────────────────────────────────────────────────────
    # Configs einlesen
    # ───────────────────────────────────────────────────────────────────────
    with open(map_config,  "r", encoding="utf-8") as f:
        mcfg = json.load(f)
    log.info("Map-Config geladen")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    log.info("AIS-Filter-Config geladen")

    ais_file   = cfg.get("ais_file")
    filters    = cfg.get("ais_filters", {})
    output_csv = cfg.get("output_csv")

    # ───────────────────────────────────────────────────────────────────────
    # Validation
    # ───────────────────────────────────────────────────────────────────────
    if not os.path.exists(ais_file):
        log.error(f"AIS-CSV nicht gefunden: {ais_file}")
        raise FileNotFoundError(f"AIS-CSV nicht gefunden: {ais_file}")
    log.info(f"AIS-CSV gefunden: {ais_file}")

    if not output_csv:
        log.error("`output_csv` muss in der Config angegeben sein.")
        raise ValueError("`output_csv` muss in der Config angegeben sein.")
    log.info(f"Output-CSV wird geschrieben nach: {output_csv}")

    # ───────────────────────────────────────────────────────────────────────
    # Kreis-Polygon erstellen (40 km)
    # ───────────────────────────────────────────────────────────────────────
    lon, lat, radius_km = mcfg["lon"], mcfg["lat"], mcfg["radius"]
    log.info(f"Erzeuge Kreis-Polygon: Zentrum=({lat}, {lon}), Radius={radius_km} km")
    center = Point(lon, lat)
    circle = (
        gpd.GeoSeries([center], crs="EPSG:4326")
           .to_crs(3857)
           .buffer(radius_km * 1000)
           .to_crs("EPSG:4326")
           .iloc[0]
    )

    # ───────────────────────────────────────────────────────────────────────
    # AIS-Daten einlesen
    # ───────────────────────────────────────────────────────────────────────
    log.info("Lade AIS-Daten in DataFrame …")
    df = pd.read_csv(
        ais_file,
        parse_dates=["# Timestamp"],
        dtype={"MMSI": str},
        low_memory=False
    )
    log.info(f"AIS-Daten geladen: {len(df):,} Zeilen")

    # Umbenennen falls nötig
    if "Latitude" in df.columns and "lat" not in df.columns:
        df.rename(columns={"Latitude": "lat", "Longitude": "lon"}, inplace=True)
        log.info("Spalten 'Latitude'/'Longitude' → 'lat'/'lon' umbenannt")

    # ───────────────────────────────────────────────────────────────────────
    # Zu GeoDataFrame und Clip auf Kreis
    # ───────────────────────────────────────────────────────────────────────
    log.info("Erstelle GeoDataFrame und clippe auf Kreis-Polygon …")
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs="EPSG:4326"
    )
    before_clip = len(gdf)
    gdf = gdf[gdf.geometry.within(circle)].copy()
    log.info(f"Punkte innerhalb Kreis: {len(gdf):,} / {before_clip:,}")

    # ───────────────────────────────────────────────────────────────────────
    # Dynamisches Filtern nach ais_filters
    # ───────────────────────────────────────────────────────────────────────
    for col, crit in filters.items():
        if isinstance(crit, list):
            gdf = gdf[gdf[col].isin(crit)]
            log.info(f"Filter {col} ∈ {crit}: verbleibend {len(gdf):,}")
        else:
            gdf = gdf[gdf[col] == crit]
            log.info(f"Filter {col} == {crit}: verbleibend {len(gdf):,}")

    # ───────────────────────────────────────────────────────────────────────
    # Ergebnis speichern als CSV (ohne Geometrie-Spalte)
    # ───────────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_out = gdf.drop(columns="geometry")
    df_out.to_csv(output_csv, index=False)
    log.info(f"Gefilterte AIS-Daten gespeichert nach: {output_csv}")

if __name__ == "__main__":
    cli()