### src/plotseamap/cli.py
#!/usr/bin/env python3
import sys
import os
# Projekt/src zum Modulpfad hinzufügen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

import click
import json
import geopandas as gpd
from shapely.geometry import Point

from plotseamap.merge import merge_pbf
from plotseamap.clip_bbox import clip_bbox
from plotseamap.extract import extract_stream  # falls ersetzt
from plotseamap.convert import convert_to_gpkg
from plotseamap.buffer import buffer_layer
#from plotseamap.plot import plot_map

@click.group()
@click.option('--config', '-c', default='config/fehmarnbelt.json', show_default=True,
              help='Pfad zur JSON-Konfigurationsdatei')
@click.pass_context
def main(ctx, config):
    """
    Haupt-CLI für plotseamap.
    """
    with open(config, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    ctx.obj = cfg

@main.command()
@click.pass_context
def merge(ctx):
    """Merge multiple raw PBFs into one."""
    cfg = ctx.obj
    merge_pbf(cfg['raw_pbf_files'], cfg['merged_pbf'])

@main.command()
@click.pass_context
def clip(ctx):
    """Clip the merged PBF down to the bounding box of the configured circle."""
    cfg = ctx.obj
    lon, lat, radius_km = cfg['lon'], cfg['lat'], cfg['radius']
    # Build circle and bbox
    center = Point(lon, lat)
    gdf = gpd.GeoDataFrame(geometry=[center], crs="EPSG:4326")
    utm_crs = gdf.estimate_utm_crs()
    circle = gdf.to_crs(utm_crs).buffer(radius_km * 1000).to_crs("EPSG:4326").iloc[0]
    bbox = circle.bounds  # (minx, miny, maxx, maxy)
    clip_bbox(cfg['merged_pbf'], cfg['bbox_pbf'], bbox)

@main.command()
@click.pass_context
def extract(ctx):
    extract_stream(ctx.obj)

@main.command()
@click.pass_context
def convert(ctx):
    """Convert extracted GeoJSON to GeoPackage."""
    convert_to_gpkg(ctx.obj)

@main.command()
@click.pass_context
def buffer(ctx):
    """Add buffer zones (optional)."""
    buffer_layer(ctx.obj)

#@main.command()
#@click.pass_context
#def plot(ctx):
#    """Render final map plot."""
#    plot_map(ctx.obj)

if __name__ == '__main__':
    main()
