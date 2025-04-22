import os
import logging
import geopandas as gpd

# Logging einrichten
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


def buffer_layer(cfg: dict) -> None:
    """
    Erzeuge Pufferzonen um Geometrien gemäß Konfiguration.

    Erwartete Konfigurationsschlüssel:
      - input_gpkg           Pfad zur Eingabe‑GPKG‑Datei
      - layer_name           Layername im GPKG (optional)
      - buffer_distance      Pufferdistanz in Metern
      - output_buffer_geojson GeoJSON‑Pfad für das Ergebnis
    """
    input_gpkg = cfg.get("input_gpkg")
    layer_name = cfg.get("layer_name", "osm")
    buffer_distance = cfg.get("buffer_distance")
    output_geojson = cfg.get("output_buffer_geojson")

    if not (input_gpkg and buffer_distance is not None and output_geojson):
        raise ValueError(
            "Konfiguration muss 'input_gpkg', 'buffer_distance' und "
            "'output_buffer_geojson' enthalten."
        )

    # -------------------------------------------------- Laden
    log.info(f"Lade Layer '{layer_name}' aus {input_gpkg}")
    gdf = gpd.read_file(input_gpkg, layer=layer_name)
    log.info(f"{len(gdf):,} Features geladen")

    # -------------------------------------------------- CRS → metrisch
    try:
        utm = gdf.estimate_utm_crs()
        gdf = gdf.to_crs(utm)
        log.info(f"Umprojiziert nach metrischem CRS {utm.to_string()}")
    except Exception as e:
        log.warning(f"UTM‑Schätzung fehlgeschlagen – bleibe in Original‑CRS ({e})")

    # -------------------------------------------------- Buffer
    log.info(f"Puffere Geometrien um {buffer_distance} m …")
    gdf["geometry"] = gdf.geometry.buffer(buffer_distance)
    log.info("Puffer fertig")

    # -------------------------------------------------- zurück zu WGS84
    try:
        gdf = gdf.to_crs(epsg=4326)
        log.info("Zurückprojiziert nach EPSG:4326")
    except Exception as e:
        log.warning(f"Rückprojektion fehlgeschlagen ({e}) – behalte aktuelles CRS")

    # -------------------------------------------------- Speichern
    os.makedirs(os.path.dirname(output_geojson), exist_ok=True)
    gdf.to_file(output_geojson, driver="GeoJSON")
    log.info(f"Puffer‑GeoJSON geschrieben: {output_geojson}")