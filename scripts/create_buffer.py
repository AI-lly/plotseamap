# scripts/create_buffer.py

import argparse
from shapely.geometry import Point
import geopandas as gpd
import os

# Argumente aus der Kommandozeile einlesen
parser = argparse.ArgumentParser(description="Create circular buffer around coordinates.")
parser.add_argument("--lon", type=float, required=True)
parser.add_argument("--lat", type=float, required=True)
parser.add_argument("--radius", type=int, required=True, help="Radius in meters")
parser.add_argument("--name", required=True, help="Region name (used for file naming)")
args = parser.parse_args()

# Punkt erzeugen
point = Point(args.lon, args.lat)
gdf = gpd.GeoDataFrame(geometry=[point], crs="EPSG:4326")

# In Meter-Projektion umrechnen (Web Mercator)
gdf_proj = gdf.to_crs("EPSG:3857")
buffer = gdf_proj.buffer(args.radius)

# Zurück in WGS84 für GeoJSON
buffer_wgs84 = gpd.GeoDataFrame(geometry=buffer, crs="EPSG:3857").to_crs("EPSG:4326")

# Zielpfad
out_path = f"processed/geojson/{args.name}_buffer.geojson"
os.makedirs("processed/geojson", exist_ok=True)

# Speichern
buffer_wgs84.to_file(out_path, driver="GeoJSON")
print(f"✅ Buffer gespeichert unter: {out_path}")