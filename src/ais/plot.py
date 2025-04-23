import os
import json
import click
import logging
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

@click.command()
@click.option("--config", "config_path", required=True,
              type=click.Path(exists=True),
              help="Pfad zur AIS-Plot-Config-JSON-Datei")
def plot_ais(config_path):
    """
    Zeichnet die vorgerenderte Basiskarte und überlagert AIS-Trajektorien.

    Config-Keys:
      - output_csv (str): Pfad zur gefilterten AIS-CSV-Datei
      - base_map_png (str): Pfad zum vorgerenderten Basemap-PNG
      - bbox_geojson (str): Pfad zur GeoJSON mit Puffer-Polygon
      - plot (dict): {
            figsize: [width, height],
            track_color: Farbcode oder Name,
            track_width: Linienbreite
        }
      - output_ais_plot (str): Pfad zur Ausgabe-PNG-Datei
      - name (str, optional): Titel für den Plot
    """
    # Config laden
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    ais_csv        = cfg.get('output_csv')
    base_map_png   = cfg.get('base_map_png')
    bbox_geojson   = cfg.get('bbox_geojson')
    plot_cfg       = cfg.get('plot', {})
    output_ais_png = cfg.get('output_ais_plot')

    # Validierung
    for label, path in [('AIS-CSV', ais_csv),
                        ('Base-Map PNG', base_map_png),
                        ('BBox-GeoJSON', bbox_geojson)]:
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"{label} nicht gefunden: {path}")
    if not output_ais_png:
        raise ValueError("'output_ais_plot' muss in der Config angegeben sein.")

    # Bounding-Box für Extent aus GeoJSON
    bbox_gdf = gpd.read_file(bbox_geojson).to_crs(epsg=3857)
    minx, miny, maxx, maxy = bbox_gdf.total_bounds

    # Basemap-Bild laden
    img = plt.imread(base_map_png)

    # AIS-Daten laden
    df = pd.read_csv(ais_csv, parse_dates=['# Timestamp'])
    # Umbenennen falls nötig
    if 'Longitude' in df.columns and 'lat' not in df.columns:
        df = df.rename(columns={'Longitude':'lon','Latitude':'lat'})

    # GeoDataFrame erstellen und reprojizieren
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df['lon'], df['lat']),
        crs='EPSG:4326'
    ).to_crs(epsg=3857)

    # Plot-Parameter
    figsize     = tuple(plot_cfg.get('figsize', [10, 8]))
    track_color = plot_cfg.get('track_color', 'orange')
    track_width = plot_cfg.get('track_width', 1)

    # Plot aufsetzen
    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(img, extent=(minx, maxx, miny, maxy), zorder=0)

    # AIS-Trajektorien zeichnen
    for mmsi, sub in gdf.groupby('MMSI'):
        sub_sorted = sub.sort_values('# Timestamp')
        ax.plot(
            sub_sorted.geometry.x,
            sub_sorted.geometry.y,
            color=track_color,
            linewidth=track_width,
            alpha=0.7,
            zorder=1
        )

    # Achsen und Titel
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.axis('off')
    title = cfg.get('name', 'AIS-Trajektorien')
    ax.set_title(title)
    plt.tight_layout()

    # Speichern
    os.makedirs(os.path.dirname(output_ais_png), exist_ok=True)
    plt.savefig(output_ais_png, dpi=300, bbox_inches='tight')
    log.info(f"AIS-Plot gespeichert: {output_ais_png}")

if __name__ == '__main__':
    plot_ais()
