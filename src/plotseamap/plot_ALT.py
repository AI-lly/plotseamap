import os
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box
import pandas as pd
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

# ───────────────────────────────────────────────────────────────────────
# Prüfung der Pfade
# ───────────────────────────────────────────────────────────────────────
region       = "fehmarnbelt"
gpkg_path    = f"data/processed/gpkg/{region}_data.gpkg"
buffer_path  = f"data/processed/geojson/{region}_buffer.geojson"

if not os.path.exists(gpkg_path):
    raise FileNotFoundError(f"{gpkg_path} nicht gefunden")
if not os.path.exists(buffer_path):
    raise FileNotFoundError(f"{buffer_path} nicht gefunden")

# ───────────────────────────────────────────────────────────────────────
# CRS für Plot
# ───────────────────────────────────────────────────────────────────────
crs_plot = "EPSG:3857"

# ───────────────────────────────────────────────────────────────────────
# Bounding‑Box aus Buffer
# ───────────────────────────────────────────────────────────────────────
buffer = gpd.read_file(buffer_path).to_crs(crs_plot)
minx, miny, maxx, maxy = buffer.total_bounds
bbox = gpd.GeoDataFrame(
    geometry=[box(minx, miny, maxx, maxy)],
    crs=crs_plot
)

# ───────────────────────────────────────────────────────────────────────
# Multipolygone aus GeoPackage laden & auf BBox clippen
# ───────────────────────────────────────────────────────────────────────
gdf_all = (
    gpd.read_file(gpkg_path, layer=region)
       .to_crs(crs_plot)
)
# nur Flächen‑Geometrien
multipolygons = gdf_all[
    gdf_all.geometry.type.isin(["Polygon", "MultiPolygon"])
].pipe(lambda df: gpd.clip(df, bbox))

# ───────────────────────────────────────────────────────────────────────
# Tag‑Filter definieren
# ───────────────────────────────────────────────────────────────────────
wasser_tags = [
    "water", "wetland", "coastline", "bay",
    "beach", "strait", "sand", "shingle", "mud"
]

# ───────────────────────────────────────────────────────────────────────
# Kategorien filtern
# ───────────────────────────────────────────────────────────────────────
water_polys     = multipolygons[multipolygons.get("natural", "")   .isin(wasser_tags)]
military_polys  = multipolygons[multipolygons.get("landuse", "")   == "military"]
protected_areas = multipolygons[multipolygons.get("boundary", "")  == "protected_area"]
land_polys      = multipolygons[
    (~multipolygons.get("natural", "").isin(wasser_tags)) &
    (multipolygons.get("landuse", "")  != "military") &
    (multipolygons.get("boundary", "") != "protected_area")
]

print(f"Land:      {len(land_polys):,}")
print(f"Wasser:    {len(water_polys):,}")
print(f"Military:  {len(military_polys):,}")
print(f"Protected: {len(protected_areas):,}")

# ───────────────────────────────────────────────────────────────────────
# Linien aus GeoPackage laden & auf BBox clippen
# ───────────────────────────────────────────────────────────────────────
lines = (
    gdf_all[gdf_all.geometry.type.isin(["LineString", "MultiLineString"])]
       .pipe(lambda df: gpd.clip(df, bbox))
)
fairway_lines = lines[lines.get("waterway", "") == "fairway"]
river_lines   = lines[lines.get("waterway", "") == "river"]
stream_lines  = lines[lines.get("waterway", "") == "stream"]

print(f"Fairway‑Linien: {len(fairway_lines):,}")
print(f"River‑Linien:   {len(river_lines):,}")
print(f"Stream‑Linien:  {len(stream_lines):,}")

# ───────────────────────────────────────────────────────────────────────
# Plot Vorbereitung
# ───────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 12))
bbox.plot(ax=ax, color="#d0e7f9", zorder=0)

# ───────────────────────────────────────────────────────────────────────
# 1) Land
# ───────────────────────────────────────────────────────────────────────
land_polys.plot(
    ax=ax,
    facecolor="#f5f2eb",
    edgecolor="gray",
    linewidth=0.5,
    zorder=1,
    label="Land"
)

# ───────────────────────────────────────────────────────────────────────
# 2) Wasser
# ───────────────────────────────────────────────────────────────────────
water_polys.plot(
    ax=ax,
    facecolor="#a6cee3",
    edgecolor="black",
    linewidth=0.5,
    zorder=2,
    label="Wasser"
)

# ───────────────────────────────────────────────────────────────────────
# 3) Military
# ───────────────────────────────────────────────────────────────────────
military_polys.plot(
    ax=ax,
    facecolor="red",
    alpha=0.4,
    edgecolor="#8B0000",
    linewidth=2,
    linestyle="--",
    zorder=3,
    label="Military"
)

# ───────────────────────────────────────────────────────────────────────
# 4) Protected Areas
# ───────────────────────────────────────────────────────────────────────
protected_areas.plot(
    ax=ax,
    facecolor="none",
    edgecolor="green",
    linewidth=2,
    linestyle="-",
    zorder=4,
    label="Protected Area"
)

# ───────────────────────────────────────────────────────────────────────
# Beschriftungen (optional)
# ───────────────────────────────────────────────────────────────────────
for gdf, col, color in [
    (water_polys, "name", "blue"),
    (military_polys, "name", "#8B0000"),
    (protected_areas, "name", "green")
]:
    for _, row in gdf.iterrows():
        if pd.notnull(row.get(col)):
            c = row.geometry.centroid
            ax.text(c.x, c.y, row[col],
                    fontsize=6, color=color,
                    ha="center", va="center")

# ───────────────────────────────────────────────────────────────────────
# 5) Fairway‑Linien
# ───────────────────────────────────────────────────────────────────────
fairway_lines.plot(
    ax=ax,
    color="#8A2BE2",
    linewidth=2,
    zorder=5,
    label="Fairway"
)

# (River & Stream auskommentiert, aktivieren bei Bedarf)
# river_lines.plot(color="#000080", linewidth=2, zorder=6, label="River")
# stream_lines.plot(color="#00BFFF", linewidth=2, zorder=7, label="Stream")

# ───────────────────────────────────────────────────────────────────────
# Legende & Layout
# ───────────────────────────────────────────────────────────────────────
legend_handles = [
    mpatches.Patch(facecolor="#f5f2eb", edgecolor="gray", label="Land"),
    mpatches.Patch(facecolor="#a6cee3", edgecolor="black", label="Wasser"),
    Line2D([0],[0], marker="s", color="none", markerfacecolor="red",
           markeredgecolor="#8B0000", markersize=10,
           linestyle="--", label="Military", alpha=0.4),
    mpatches.Patch(facecolor="none", edgecolor="green", label="Protected Area"),
    Line2D([0],[0], color="#8A2BE2", lw=2, label="Fairway")
]
ax.legend(handles=legend_handles, title="Kategorien", loc="lower left",
          fontsize=9, title_fontsize=10)

ax.set_title("Schritt X: Kategorien‑Plot")
ax.axis("off")
plt.tight_layout()
plt.show()