import argparse
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
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
bbox_geom = buffer.total_bounds
bbox = gpd.GeoDataFrame(geometry=[box(*bbox_geom)], crs=crs)

# Geometrien reparieren
for key in data:
    gdf = data[key]
    gdf["geometry"] = gdf["geometry"].apply(lambda geom: geom.buffer(0) if geom and not geom.is_valid else geom)
    data[key] = gdf

# Clipping
for key in data:
    data[key] = gpd.clip(data[key], bbox)

# Plot vorbereiten
fig, ax = plt.subplots(figsize=(12, 12))
ax.set_facecolor("#dbeeff")  # Wasser-Hintergrund

# ➤ Rechteckfüllung für „Land“ zeichnen
bbox.plot(ax=ax, color="#f5f2eb", zorder=0)  # Helles Beige als Grundfläche

# ➤ Multipolygone (Land, Wasser, Gebäude etc.)
if "multipolygons" in data and not data["multipolygons"].empty:
    multipolygons = data["multipolygons"]

    categories = {
        "natural=water": multipolygons["natural"] == "water",
        "landuse=forest": multipolygons["landuse"] == "forest",
        "landuse=residential": multipolygons["landuse"] == "residential",
        "building": multipolygons["building"].notna(),
        "leisure": multipolygons["leisure"].notna()
    }

    style = {
        "natural=water": "#b5d0f0",
        "landuse=forest": "#a5cba7",
        "landuse=residential": "#e0dfdf",
        "building": "#999999",
        "leisure": "#cceebb",
        "other": "#f2efe9"
    }

    combined_mask = np.zeros(len(multipolygons), dtype=bool)
    for label, mask in categories.items():
        subset = multipolygons[mask]
        combined_mask |= mask
        if not subset.empty:
            subset.plot(ax=ax, color=style[label], edgecolor="white", linewidth=0.2, label=label)

    other = multipolygons[~combined_mask]
    if not other.empty:
        other.plot(ax=ax, color=style["other"], edgecolor="white", linewidth=0.2, label="other")

# ➤ Linien (Straßen, Wasserwege etc.)
if "lines" in data and not data["lines"].empty:
    lines = data["lines"]

    color_map = {
        "highway": "#666666",
        "waterway": "#3366cc",
        "railway": "#444444",
        "aerialway": "#ff9900",
        "barrier": "red",
        "man_made": "#66cc66"
    }

    for key, color in color_map.items():
        if key in lines.columns:
            subset = lines[lines[key].notna()]
            if not subset.empty:
                subset.plot(ax=ax, color=color, linewidth=0.8, label=key)

    other_lines = lines[lines[list(color_map.keys())].isna().all(axis=1)]
    if not other_lines.empty:
        other_lines.plot(ax=ax, color="lightgray", linewidth=0.5, label="other_lines")

# ➤ Punkte (Leuchttürme, Häfen, Barrieren)
points = gpd.read_file(gpkg_path, layer="points").to_crs(crs)

point_categories = {
    "man_made=lighthouse": {
        "filter": points["man_made"] == "lighthouse",
        "color": "red",
        "marker": "o",
        "label": "Leuchtturm"
    },
    "place=harbour": {
        "filter": points["place"] == "harbour",
        "color": "blue",
        "marker": "s",
        "label": "Hafen"
    },
    "barrier": {
        "filter": points["barrier"].notna(),
        "color": "black",
        "marker": "x",
        "label": "Barriere"
    }
}

for key, props in point_categories.items():
    subset = points[props["filter"]]
    if not subset.empty:
        subset.plot(
            ax=ax,
            color=props["color"],
            markersize=50,
            marker=props["marker"],
            label=props["label"],
            linewidth=0
        )

# Bounding Box-Rand
bbox.boundary.plot(ax=ax, color="red", linewidth=1)

# Layout
ax.set_aspect("equal")
ax.set_title(f"🚢 OpenSeaMap-Stil: {region.title()}", fontsize=14)
ax.legend(title="Kartentypen", loc="lower left", fontsize=7, title_fontsize=8)
ax.axis("off")
plt.tight_layout()

# Speichern
out_path = f"output/plots/{region}_seamap_style.png"
plt.savefig(out_path, dpi=300)
plt.show()
print(f"✅ Karte gespeichert unter: {out_path}")


# python scripts/plot_map.py --name fehmarnbelt