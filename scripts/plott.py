import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box
import os
import pandas as pd
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

# Regionen-Parameter
region = "fehmarnbelt"
gpkg_path = f"processed/geopackage/{region}.gpkg"
buffer_path = f"processed/geojson/{region}_buffer.geojson"

# Prüfe, ob die Dateien existieren
if not os.path.exists(gpkg_path) or not os.path.exists(buffer_path):
    print("❌ Fehlende Datei(en).")
    exit(1)

# Lade den Buffer und projiziere auf Web Mercator (EPSG:3857)
buffer = gpd.read_file(buffer_path)
crs = "EPSG:3857"
buffer = buffer.to_crs(crs)

# Lade den Multipolygone-Layer und clippe ihn auf die BoundingBox
multipolygons = gpd.read_file(gpkg_path, layer="multipolygons").to_crs(crs)
bbox_geom = buffer.total_bounds
bbox = gpd.GeoDataFrame(geometry=[box(*bbox_geom)], crs=crs)
multipolygons = gpd.clip(multipolygons, bbox)

# Definiere eine Liste wasserbezogener Tags, damit auch Flächen mit "wetland", "coastline" etc. erfasst werden.
wasser_tags = ["water", "wetland", "coastline", "bay", "beach", "strait", "sand", "shingle", "mud"]

# Filtere die Kategorien:
water_polys = multipolygons[multipolygons["natural"].isin(wasser_tags)]
print(f"Gefundene Wasserflächen (erweiterter Filter): {len(water_polys)}")

military_polys = multipolygons[multipolygons["landuse"] == "military"]
print(f"Gefundene Military-Features: {len(military_polys)}")

protected_areas = multipolygons[multipolygons["boundary"] == "protected_area"]
print(f"Gefundene Protected Areas: {len(protected_areas)}")

land_polys = multipolygons[
    (~multipolygons["natural"].isin(wasser_tags)) &
    ~(multipolygons["landuse"] == "military") &
    ~(multipolygons["boundary"] == "protected_area")
]
print(f"Gefundenes Land: {len(land_polys)}")

# Erstelle den Plot für die Multipolygone
fig, ax = plt.subplots(figsize=(12, 12))

# Hintergrund: Weiches Blau als Ozeanhintergrund
bbox.plot(ax=ax, color="#d0e7f9", zorder=0)

# 1. Plot Land: Gefüllt in Beige mit grauen Umrissen
land_polys.plot(ax=ax,
                color="#f5f2eb",
                edgecolor="gray",
                linewidth=0.5,
                zorder=1,
                label="Land")

# 2. Plot Wasser: Gefüllt in Blau mit schwarzen Umrissen
water_polys.plot(ax=ax,
                 color="#a6cee3",
                 edgecolor="black",
                 linewidth=0.5,
                 zorder=2,
                 label="Wasser")

# 3. Plot Military: Gefüllt in Rot (alpha=0.4) mit dunkelroten, gestrichelten Umrissen
military_polys.plot(ax=ax,
                    facecolor="red",
                    alpha=0.4,
                    edgecolor="#8B0000",
                    linewidth=2,
                    linestyle="--",
                    zorder=3,
                    label="Military")

# 4. Plot Protected Areas: Keine Füllung, aber grüne Umrisse
protected_areas.plot(ax=ax,
                     facecolor="none",
                     edgecolor="green",
                     linewidth=2,
                     linestyle="-",
                     zorder=4,
                     label="Protected Area")

# Füge Namensbeschriftung hinzu

# Wasserflächen-Namen (Beschriftung in Blau)
for idx, row in water_polys.iterrows():
    if pd.notnull(row.get("name")):
        centroid = row.geometry.centroid
        ax.annotate(row["name"],
                    xy=(centroid.x, centroid.y),
                    fontsize=6,
                    color="blue",
                    ha="center",
                    va="center")

# Military-Namen (Beschriftung in Dunkelrot)
for idx, row in military_polys.iterrows():
    if pd.notnull(row.get("name")):
        centroid = row.geometry.centroid
        ax.annotate(row["name"],
                    xy=(centroid.x, centroid.y),
                    fontsize=6,
                    color="#8B0000",
                    ha="center",
                    va="center")

# Protected Areas-Namen (Beschriftung in Grün)
for idx, row in protected_areas.iterrows():
    if pd.notnull(row.get("name")):
        centroid = row.geometry.centroid
        ax.annotate(row["name"],
                    xy=(centroid.x, centroid.y),
                    fontsize=6,
                    color="green",
                    ha="center",
                    va="center")

# Lade den Linien-Layer und clippe ihn an die BoundingBox
lines = gpd.read_file(gpkg_path, layer="lines").to_crs(crs)
lines = gpd.clip(lines, bbox)

# Filtere nun ausschließlich die Linien für 'fairway', 'river' und 'stream'
fairway_lines = lines[lines["waterway"] == "fairway"]
river_lines = lines[lines["waterway"] == "river"]
stream_lines = lines[lines["waterway"] == "stream"]

print(f"Gefundene Fairway-Linien: {len(fairway_lines)}")
print(f"Gefundene River-Linien: {len(river_lines)}")
print(f"Gefundene Stream-Linien: {len(stream_lines)}")

# Plot Fairway-Linien in BlauViolet (#8A2BE2)
fairway_lines.plot(ax=ax,
                   color="#8A2BE2",
                   linewidth=2,
                   zorder=5,
                   label="Fairway Lines")

# Plot River-Linien in Navy (#000080)
#river_lines.plot(ax=ax,
#                 color="#000080",
#                 linewidth=2,
#                 zorder=6,
#                 label="River Lines")

# Plot Stream-Linien in Deepskyblue (#00BFFF)
#stream_lines.plot(ax=ax,
#                  color="#00BFFF",
#                  linewidth=2,
#                  zorder=7,
#                  label="Stream Lines")

ax.set_title("Multipolygone & Linien:\nLand, Wasser, Military, Protected Areas, Fairway, River & Stream Lines")
ax.axis("off")

# Benutzerdefinierte Legende-Einträge erstellen:
legend_handles = []

# Land: Patch mit Beige Füllung und grauem Rand
land_patch = mpatches.Patch(facecolor="#f5f2eb", edgecolor="gray", label="Land")
legend_handles.append(land_patch)

# Wasser: Patch mit Blau Füllung und schwarzem Rand
water_patch = mpatches.Patch(facecolor="#a6cee3", edgecolor="black", label="Wasser")
legend_handles.append(water_patch)

# Military: Line2D für Military Features (rot gestrichelt)
military_handle = Line2D([0], [0], marker="s", color="none",
                          markerfacecolor="red",
                          markeredgecolor="#8B0000",
                          markersize=15, linestyle="--",
                          label="Military", alpha=0.4)
legend_handles.append(military_handle)

# Protected Area: Patch ohne Füllung, mit grünem Rand
protected_handle = mpatches.Patch(facecolor="none", edgecolor="green", label="Protected Area")
legend_handles.append(protected_handle)

# Fairway Lines: Line2D in BlueViolet (#8A2BE2)
fairway_handle = Line2D([0], [0], color="#8A2BE2", linewidth=2, label="Fairway Lines")
legend_handles.append(fairway_handle)

# River Lines: Line2D in Navy (#000080)
river_handle = Line2D([0], [0], color="#000080", linewidth=2, label="River Lines")
legend_handles.append(river_handle)

# Stream Lines: Line2D in Deepskyblue (#00BFFF)
stream_handle = Line2D([0], [0], color="#00BFFF", linewidth=2, label="Stream Lines")
legend_handles.append(stream_handle)

ax.legend(handles=legend_handles, title="Kategorien", loc="lower left", fontsize=9, title_fontsize=10)

plt.tight_layout()
plt.show()