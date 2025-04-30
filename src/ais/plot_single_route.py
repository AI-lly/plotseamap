import os
import json
import click
import logging
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# ───────────────────────────────────────────────────────────────────────
# Logging konfigurieren
# ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

@click.command()
@click.option("--config", "config_path", required=True,
              type=click.Path(exists=True),
              help="Pfad zur AIS-Plot-Config-JSON-Datei")
def plot_single_route(config_path):
    """
    Zeichnet eine einzelne AIS-Route aus einer CSV.

    Config-Keys:
      - output_csv (str): Pfad zur AIS-CSV-Datei mit einer Route
      - base_map_png (str): Pfad zum vorgerenderten Basemap-PNG
      - bbox_geojson (str): Pfad zur GeoJSON mit Puffer-Polygon für Extent
      - plot (dict): {
            figsize: [width, height],
            track_color: Farbcode oder Name,
            track_width: Linienbreite
        }
      - output_ais_plot (str): Pfad zur Ausgabe-PNG-Datei
      - name (str, optional): Titel für den Plot
    """
    log.info(f"Starte AIS-Single-Route-Plot mit Config: {config_path}")

    # Config laden
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    log.info("Config erfolgreich geladen")

    ais_csv        = cfg.get('output_csv')
    base_map_png   = cfg.get('base_map_png')
    bbox_geojson   = cfg.get('bbox_geojson')
    plot_cfg       = cfg.get('plot', {})
    output_ais_png = cfg.get('output_ais_plot')

    # Validierung der Pfade
    for label, path in [
        ('AIS-CSV', ais_csv),
        ('Base-Map PNG', base_map_png),
        ('BBox-GeoJSON', bbox_geojson),
    ]:
        if not path or not os.path.exists(path):
            log.error(f"{label} nicht gefunden: {path}")
            raise FileNotFoundError(f"{label} nicht gefunden: {path}")
        log.info(f"{label} gefunden: {path}")

    if not output_ais_png:
        log.error("'output_ais_plot' muss in der Config angegeben sein.")
        raise ValueError("'output_ais_plot' muss in der Config angegeben sein.")
    log.info(f"Output-Pfad für AIS-Plot: {output_ais_png}")

    # Bounding-Box für Extent aus GeoJSON
    log.info("Lese Bounding-Box aus GeoJSON …")
    bbox_gdf = gpd.read_file(bbox_geojson).to_crs(epsg=3857)
    minx, miny, maxx, maxy = bbox_gdf.total_bounds
    log.info(f"Extent berechnet: minx={minx:.0f}, miny={miny:.0f}, maxx={maxx:.0f}, maxy={maxy:.0f}")

    # Basemap-Bild laden
    log.info("Lade Basemap-Bild …")
    img = plt.imread(base_map_png)

    # AIS-Daten laden
    log.info("Lade AIS-Daten …")
    df = pd.read_csv(ais_csv, parse_dates=['# Timestamp'])
    log.info(f"AIS-Daten geladen: {len(df):,} Zeilen")

    # Spalten umbenennen falls nötig
    if 'Longitude' in df.columns and 'lon' not in df.columns:
        df = df.rename(columns={'Longitude':'lon','Latitude':'lat'})
        log.info("Spalten 'Latitude'/'Longitude' zu 'lat'/'lon' umbenannt")

    # GeoDataFrame erstellen und reprojizieren
    log.info("Erstelle GeoDataFrame und reprojiziere auf EPSG:3857 …")
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df['lon'], df['lat']),
        crs='EPSG:4326'
    ).to_crs(epsg=3857)
    log.info(f"GeoDataFrame erstellt: {len(gdf):,} Punkte")

    # Plot-Parameter aus Config
    figsize     = tuple(plot_cfg.get('figsize', [10, 8]))
    track_color = plot_cfg.get('track_color', 'orange')
    track_width = plot_cfg.get('track_width', 1)
    log.info(f"Plot-Konfiguration: figsize={figsize}, color={track_color}, width={track_width}")

    # Plot erstellen
    log.info("Erstelle Single-Route-Plot …")
    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(img, extent=(minx, maxx, miny, maxy), zorder=0)

    # Single Route zeichnen
    sub_sorted = gdf.sort_values('# Timestamp')
    ax.plot(
        sub_sorted.geometry.x,
        sub_sorted.geometry.y,
        color=track_color,
        linewidth=track_width,
        alpha=0.7,
        zorder=1
    )
    log.info("Single Route gezeichnet")

    # Achsen und Titel
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.axis('off')
    title = cfg.get('name', 'AIS-Single-Route')
    ax.set_title(title)
    plt.tight_layout()
    log.info(f"Plot-Titel gesetzt: {title}")

    # Speichern
    os.makedirs(os.path.dirname(output_ais_png), exist_ok=True)
    plt.savefig(output_ais_png, dpi=300, bbox_inches='tight')
    log.info(f"AIS-Single-Route-Plot gespeichert: {output_ais_png}")

if __name__ == '__main__':
    plot_single_route()
