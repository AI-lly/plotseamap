# scripts/convert_to_poly.py
import argparse
import geopandas as gpd
import os
from utils.geo_helpers import save_as_poly

parser = argparse.ArgumentParser(description="Convert buffer GeoJSON to .poly format")
parser.add_argument("--name", required=True, help="Region name (used for file naming)")
args = parser.parse_args()

in_path = f"processed/geojson/{args.name}_buffer.geojson"
out_path = f"processed/poly/{args.name}.poly"
os.makedirs("processed/poly", exist_ok=True)

gdf = gpd.read_file(in_path)
save_as_poly(gdf, args.name, out_path)
print(f"✅ .poly gespeichert unter: {out_path}")