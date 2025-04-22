import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


def safe_select(gdf, column, values):
    if column not in gdf.columns:
        return gpd.GeoDataFrame(columns=gdf.columns, crs=gdf.crs)
    return gdf[gdf[column].isin(values)]


def safe_eq(gdf, column, value):
    if column not in gdf.columns:
        return gpd.GeoDataFrame(columns=gdf.columns, crs=gdf.crs)
    return gdf[gdf[column] == value]


def plot_map(cfg: dict) -> None:
    region       = cfg["name"]
    gpkg_path    = cfg["output_gpkg"]
    layer        = cfg.get("layer_name", region)
    buffer_path  = cfg.get("output_buffer_geojson")
    figsize      = tuple(cfg.get("plot", {}).get("figsize", [10, 8]))
    crs_out      = "EPSG:3857"

    if not os.path.exists(gpkg_path):
        raise FileNotFoundError(gpkg_path)
    if buffer_path and not os.path.exists(buffer_path):
        buffer_path = None

    gdf_all = gpd.read_file(gpkg_path, layer=layer).to_crs(crs_out)
    if gdf_all.empty:
        raise ValueError("Layer enthält keine Geometrien – nichts zu plotten.")

    polys  = gdf_all[gdf_all.geometry.type.isin(["Polygon", "MultiPolygon"])]
    lines  = gdf_all[gdf_all.geometry.type.isin(["LineString", "MultiLineString"])]

    # Bounding Box
    bbox_geom = (polys.total_bounds if not polys.empty else gdf_all.total_bounds)
    if any(pd.isna(bbox_geom)):
        raise ValueError("Ungültige Bounding Box – Abbruch.")
    bbox_gdf = gpd.GeoDataFrame(geometry=[box(*bbox_geom)], crs=crs_out)

    # Kategorien
    wasser_tags = {"water", "wetland", "coastline", "bay", "beach",
                   "strait", "sand", "shingle", "mud"}

    water     = safe_select(polys, "natural", wasser_tags)
    military  = safe_select(polys, "landuse", {"military"})
    protected = safe_select(polys, "boundary", {"protected_area"})
    land      = polys.drop(water.index.union(military.index).union(protected.index))

    print(f"Wasserflächen: {len(water):,}")
    print(f"Military:      {len(military):,}")
    print(f"Protected:     {len(protected):,}")
    print(f"Land:          {len(land):,}")

    # Linien
    lines = lines.clip(bbox_gdf)
    fairway = safe_eq(lines, "waterway", "fairway")
    river   = safe_eq(lines, "waterway", "river")
    stream  = safe_eq(lines, "waterway", "stream")

    # Plot
    fig, ax = plt.subplots(figsize=figsize)
    bbox_gdf.plot(ax=ax, color="#d0e7f9", zorder=0)
    if not land.empty:
        land.plot(ax=ax, color="#f5f2eb", edgecolor="gray",
                  lw=0.5, zorder=1, label="Land")
    if not water.empty:
        water.plot(ax=ax, color="#a6cee3", edgecolor="black",
                   lw=0.4, zorder=2, label="Water")
    if not military.empty:
        military.plot(ax=ax, color="red", alpha=0.4, edgecolor="#8B0000",
                      lw=1.2, ls="--", zorder=3, label="Military")
    if not protected.empty:
        protected.plot(ax=ax, facecolor="none", edgecolor="green",
                       lw=1.2, zorder=4, label="Protected")

    if not fairway.empty:
        fairway.plot(ax=ax, color="#8A2BE2", lw=1.5, zorder=5, label="Fairway")
    if not river.empty:
        river.plot(ax=ax, color="#000080", lw=1, zorder=6, label="River")
    if not stream.empty:
        stream.plot(ax=ax, color="#00BFFF", lw=1, zorder=7, label="Stream")

    # Buffer‑Layer
    if buffer_path:
        buffer = gpd.read_file(buffer_path).to_crs(crs_out)
        if not buffer.empty:
            buffer.boundary.plot(ax=ax, color="orange", lw=1,
                                 ls=":", zorder=8, label="Buffer")

    # Legende & Layout
    ax.set_title(f"{region.capitalize()} – Overview")
    ax.axis("off")
    ax.legend(loc="lower left", fontsize=8)

    out_png = cfg["output_plot"]
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    print("✅ Plot gespeichert:", out_png)
    plt.show()