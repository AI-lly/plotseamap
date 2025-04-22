import os
import geopandas as gpd


def convert_to_gpkg(cfg: dict) -> None:
    """
    Konvertiere GeoJSON zu GeoPackage (GPKG) anhand der Konfiguration.

    Erwartete Konfigurationsschlüssel in cfg:
      - extracted_geojson: Pfad zur Eingabe-GeoJSON-Datei
      - output_gpkg: Pfad zur Ausgabe-GPKG-Datei
      - layer_name: Name der Layer im GPKG (optional, Standard: 'osm')
    """
    input_geojson = cfg.get("extracted_geojson")
    output_gpkg = cfg.get("output_gpkg")
    layer_name = cfg.get("layer_name", "osm")

    if not (input_geojson and output_gpkg):
        raise ValueError("Konfiguration muss 'extracted_geojson' und 'output_gpkg' enthalten.")

    # GDF einlesen
    gdf = gpd.read_file(input_geojson)

    # sicherstellen, dass CRS EPSG:4326 ist
    try:
        gdf = gdf.to_crs(epsg=4326)
    except Exception:
        # falls kein CRS vorhanden oder Konvertierung fehlschlägt
        pass

    # Ausgabeordner erstellen
    os.makedirs(os.path.dirname(output_gpkg), exist_ok=True)

    # Als GPKG speichern
    gdf.to_file(output_gpkg, driver="GPKG", layer=layer_name)
