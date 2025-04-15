import argparse
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
from shapely.geometry import box

# Argumente parsen
parser = argparse.ArgumentParser(description="Plot a clipped OSM region from GeoPackage")
parser.add_argument("--name", required=True, help="Region name (used for file naming)")
args = parser.parse_args()

region = args.name.lower()
gpkg_path = f"processed/geopackage/{region}.gpkg"
buffer_path = f"processed/geojson/{region}_buffer.geojson"

if not os.path.exists(gpkg_path) or not os.path.exists(buffer_path):
    print("❌ Fehlende Datei(en).")
    exit(1)

# Buffer laden
buffer = gpd.read_file(buffer_path)

# Layer laden
layers = ["multipolygons", "lines"]
data = {}

for layer in layers:
    try:
        gdf = gpd.read_file(gpkg_path, layer=layer)
        if not gdf.empty:
            data[layer] = gdf
            print(f"✅ Layer '{layer}' geladen mit {len(gdf)} Features.")
        else:
            print(f"⚠️  Layer '{layer}' ist leer.")
    except Exception as e:
        print(f"⚠️  Layer '{layer}' konnte nicht geladen werden: {e}")

if not data:
    print("❌ Keine gültigen Layer zum Plotten gefunden.")
    exit(1)

# Projektion in metrisches Koordinatensystem (Web Mercator)
crs = "EPSG:3857"
buffer = buffer.to_crs(crs)
for key in data:
    data[key] = data[key].to_crs(crs)

# Rechteckige BoundingBox aus dem Buffer erzeugen
bbox_geom = buffer.total_bounds  # [minx, miny, maxx, maxy]
bbox = gpd.GeoDataFrame(
    geometry=[box(*bbox_geom)],
    crs=crs
)

# Ungültige Geometrien reparieren
for key in data:
    gdf = data[key]
    gdf["geometry"] = gdf["geometry"].apply(lambda geom: geom.buffer(0) if geom and not geom.is_valid else geom)
    data[key] = gdf

# Daten auf BoundingBox clippen
for key in data:
    data[key] = gpd.clip(data[key], bbox)

# Plot vorbereiten
fig, ax = plt.subplots(figsize=(10, 10))

# Multipolygone farbig nach Typ plotten
if "multipolygons" in data and not data["multipolygons"].empty:
    multipolygons = data["multipolygons"]

    categories = {
        "natural=water":    (multipolygons["natural"] == "water"),
        "landuse=forest":   (multipolygons["landuse"] == "forest"),
        "landuse=residential": (multipolygons["landuse"] == "residential"),
        "building":         (multipolygons["building"].notna()),
        "leisure":          (multipolygons["leisure"].notna())
    }

    style = {
        "natural=water": "blue",
        "landuse=forest": "green",
        "landuse=residential": "lightgray",
        "building": "gray",
        "leisure": "lightgreen",
        "other": "beige"
    }

    plotted = set()
    for label, mask in categories.items():
        subset = multipolygons[mask]
        if not subset.empty:
            subset.plot(ax=ax, color=style[label], edgecolor="white", label=label)
            plotted.add(label)

    # Andere restliche Polygone
    combined_mask = np.logical_or.reduce(list(categories.values()))
    other = multipolygons[~combined_mask]
    if not other.empty:
        other.plot(ax=ax, color=style["other"], edgecolor="white", label="other")

# Farbige Linien je nach Typ
if "lines" in data and not data["lines"].empty:
    lines = data["lines"]

    color_map = {
        "highway": "gray",
        "waterway": "blue",
        "railway": "black",
        "aerialway": "orange",
        "barrier": "red",
        "man_made": "green",
    }

    for key, color in color_map.items():
        subset = lines[lines[key].notna()]
        if not subset.empty:
            subset.plot(ax=ax, color=color, linewidth=0.7, label=key)

    # Andere Linien ohne bekannten Typ
    other = lines[lines[list(color_map.keys())].isna().all(axis=1)]
    if not other.empty:
        other.plot(ax=ax, color="lightgray", linewidth=0.5, label="other_lines")

# BoundingBox-Rand zeichnen
bbox.boundary.plot(ax=ax, color="red", linewidth=1)

# Layout & Anzeige
ax.set_aspect("equal")
ax.set_title(f"Region: {region} (rechteckiger Ausschnitt)")
ax.legend(title="Typen", loc="lower left", fontsize=7, title_fontsize=8)
plt.axis("off")
plt.tight_layout()

# Speichern & anzeigen
out_path = f"output/plots/{region}_map_clipped_rect.png"
plt.savefig(out_path, dpi=300)
plt.show()
print(f"✅ Rechteckige Karte gespeichert unter: {out_path}")

# python scripts/plot_map.py --name fehmarnbelt