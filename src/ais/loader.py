# src/ais/loader.py
import os
import json
import logging
import pandas as pd
import geopandas as gpd
import click

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

def load_and_process_ais(config_path: str) -> gpd.GeoDataFrame:
    """
    Lädt AIS-Daten, wendet Bounding-Box und Filter an, und speichert das Ergebnis als CSV.
    """
    # Config laden
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    ais_file     = cfg.get("ais_file")
    bbox_geojson = cfg.get("bbox_geojson")
    filters      = cfg.get("ais_filters", {})
    output_csv   = cfg.get("output_csv")

    # Validierung
    if not ais_file or not os.path.exists(ais_file):
        log.error(f"AIS-CSV nicht gefunden: {ais_file!r}")
        raise click.Abort()
    if not bbox_geojson or not os.path.exists(bbox_geojson):
        log.error(f"BBox-GeoJSON nicht gefunden: {bbox_geojson!r}")
        raise click.Abort()
    if not output_csv:
        log.error("Config muss 'output_csv' enthalten.")
        raise click.Abort()

    log.info(f"Lese AIS-Datei:     {ais_file}")
    log.info(f"Lese Bounding-Box:  {bbox_geojson}")

    # 1) Bounding-Box einlesen & vereinigen
    bbox_gdf  = gpd.read_file(bbox_geojson).to_crs("EPSG:4326")
    clip_poly = bbox_gdf.geometry.union_all()

    # 2) AIS-Daten einlesen
    df = pd.read_csv(
        ais_file,
        parse_dates=["# Timestamp"],
        dtype={"MMSI": str},
        low_memory=False
    )
    log.info(f"Roh geladen:       {len(df):,} Zeilen")

    # 3) Spalten umbenennen
    df = df.rename(columns={"Latitude": "lat", "Longitude": "lon"})

    # 4) In GeoDataFrame umwandeln
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.lon, df.lat),
        crs="EPSG:4326"
    )

    # 5) Clip auf Bounding-Box
    gdf = gdf[gdf.geometry.within(clip_poly)]
    log.info(f"Nach BBox-Clip:    {len(gdf):,} Zeilen")

    # 6) Dynamisches Filtern
    for col, crit in filters.items():
        before = len(gdf)
        if isinstance(crit, list):
            gdf = gdf[gdf[col].isin(crit)]
        else:
            gdf = gdf[gdf[col] == crit]
        log.info(f"Filter {col!r}={crit!r}: {before:,} → {len(gdf):,}")

    # 7) Ergebnis speichern als CSV (ohne Geometrie-Spalte)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_out = gdf.drop(columns="geometry")
    df_out.to_csv(output_csv, index=False)
    log.info(f"Gefilterte AIS-Daten geschrieben: {output_csv}")

    return gdf

@click.command(context_settings={"ignore_unknown_options": True})
@click.option("--config", "config_path", required=True,
              type=click.Path(exists=True),
              help="Pfad zur AIS-Filter-Config-JSON")
def cli(config_path):
    """CLI-Entrypoint für AIS-Loader."""
    load_and_process_ais(config_path)

if __name__ == "__main__":
    cli()