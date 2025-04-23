import os
import json
import pandas as pd
import geopandas as gpd

def load_and_process_ais(config_path: str) -> gpd.GeoDataFrame:
    """
    Lädt AIS-Daten, wendet Bounding-Box und Filter an, und speichert das Ergebnis als CSV.

    Config-JSON (config_path) muss enthalten:
      - ais_file: Pfad zur AIS-CSV-Datei
      - bbox_geojson: Pfad zum GeoJSON mit Bounding-Box
      - ais_filters: dict von Spaltennamen zu Filterkriterien (Wert oder Liste)
      - output_csv: Pfad, wohin die gefilterten Daten als CSV geschrieben werden

    Returns:
      - Gefiltertes GeoDataFrame mit CRS EPSG:4326
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
        raise FileNotFoundError(f"AIS-CSV nicht gefunden: {ais_file}")
    if not bbox_geojson or not os.path.exists(bbox_geojson):
        raise FileNotFoundError(f"BBox-GeoJSON nicht gefunden: {bbox_geojson}")
    if not output_csv:
        raise ValueError("`output_csv` muss in der Config angegeben sein.")

    # 1) Bounding-Box einlesen & vereinigen
    bbox_gdf  = gpd.read_file(bbox_geojson).to_crs("EPSG:4326")
    clip_poly = bbox_gdf.geometry.unary_union

    # 2) AIS-Daten einlesen
    df = pd.read_csv(
        ais_file,
        parse_dates=["# Timestamp"],
        dtype={"MMSI": str}
    )

    # 3) Spalten umbenennen
    df = df.rename(columns={"Latitude": "lat", "Longitude": "lon"})

    # 4) In GeoDataFrame umwandeln
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.lon, df.lat),
        crs="EPSG:4326"
    )

    # 5) Clip auf Bounding-Box
    mask = gdf.geometry.within(clip_poly)
    gdf  = gdf.loc[mask].copy()

    # 6) Dynamisches Filtern
    for col, crit in filters.items():
        if isinstance(crit, list):
            gdf = gdf[gdf[col].isin(crit)]
        else:
            gdf = gdf[gdf[col] == crit]

    # 7) Ergebnis speichern als CSV (ohne Geometrie-Spalte)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_out = gdf.drop(columns="geometry")
    df_out.to_csv(output_csv, index=False)
    print(f"→ Gefilterte AIS-Daten gespeichert nach: {output_csv}")

    return gdf