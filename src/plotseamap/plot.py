import os
import json
import click
import logging
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box
import pandas as pd
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

@click.command()
@click.option("--config", "config_path", required=True,
              type=click.Path(exists=True),
              help="Pfad zur Config-JSON-Datei")
def plot_map(config_path):
    """
    Liest die extrahierten Multipolygon-Layer aus dem GeoPackage und rendert die Karte ohne Linien,
    mit smarter Beschriftung und korrekter Wasser-Klassifizierung (inkl. seamark:sea_area).
    """
    # Config laden
    with open(config_path) as f:
        cfg = json.load(f)

    gpkg = cfg["output_gpkg"]
    buffer_geojson = cfg.get("output_buffer_geojson")
    figsize = tuple(cfg.get("plot", {}).get("figsize", [10, 8]))
    extract_layers = cfg.get("extract_layers", [])

    # Pfade prüfen
    if not os.path.exists(gpkg):
        raise FileNotFoundError(f"GeoPackage nicht gefunden: {gpkg}")

    # CRS & Bounding-Box bestimmen
    crs_plot = "EPSG:3857"
    if buffer_geojson and os.path.exists(buffer_geojson):
        buf = gpd.read_file(buffer_geojson).to_crs(crs_plot)
        minx, miny, maxx, maxy = buf.total_bounds
    else:
        bounds_list = []
        for layer in extract_layers:
            try:
                df_tmp = gpd.read_file(gpkg, layer=layer).to_crs(crs_plot)
                bounds_list.append(df_tmp.total_bounds)
            except Exception:
                continue
        dfb = pd.DataFrame(bounds_list, columns=["minx","miny","maxx","maxy"])
        minx, miny = dfb["minx"].min(), dfb["miny"].min()
        maxx, maxy = dfb["maxx"].max(), dfb["maxy"].max()
    bbox_geom = box(minx, miny, maxx, maxy)
    bbox = gpd.GeoDataFrame(geometry=[bbox_geom], crs=crs_plot)

    # Plot initialisieren
    fig, ax = plt.subplots(figsize=figsize)
    bbox.plot(ax=ax, color="#d0e7f9", zorder=0)

    # Wasser-Tags (OSM) und Sea Area-Seamark
    wasser_tags = ["water","wetland","bay","beach",
                   "strait","sand","shingle","mud"]

    legend_handles = []

    # Multipolygons verarbeiten
    if "multipolygons" in extract_layers:
        try:
            gdf = gpd.read_file(gpkg, layer="multipolygons").to_crs(crs_plot)
            gdf = gpd.clip(gdf, bbox_geom)
        except Exception:
            log.warning("Layer 'multipolygons' konnte nicht geladen werden.")
            gdf = gpd.GeoDataFrame(columns=["geometry"])

        # Wasserflächen: OSM natural oder seamark sea_area
        water = gdf[(gdf.get("natural","").isin(wasser_tags)) |
                    (gdf.get("seamark:sea_area:category","") != "")]
        # Military & Protected
        mil   = gdf[gdf.get("landuse","") == "military"]
        prot  = gdf[gdf.get("boundary","") == "protected_area"]
        # Rest als Land
        land  = gdf.drop(water.index.union(mil.index).union(prot.index))

        # Flächen plotten und legendieren
        if not land.empty:
            land.plot(ax=ax, facecolor="#f5f2eb", edgecolor="gray",
                      linewidth=0.5, zorder=1)
            legend_handles.append(mpatches.Patch(
                facecolor="#f5f2eb", edgecolor="gray", label="Land"))
        if not water.empty:
            water.plot(ax=ax, facecolor="#a6cee3", edgecolor="black",
                       linewidth=0.5, zorder=2)
            legend_handles.append(mpatches.Patch(
                facecolor="#a6cee3", edgecolor="black", label="Wasser"))
        if not mil.empty:
            mil.plot(ax=ax, facecolor="red", edgecolor="#8B0000",
                     alpha=0.4, linestyle="--", linewidth=1.5, zorder=3)
            legend_handles.append(Line2D([0],[0], marker="s", color="none",
                markerfacecolor="red", markeredgecolor="#8B0000",
                markersize=10, linestyle="--", alpha=0.4,
                label="Military"))
        if not prot.empty:
            prot.plot(ax=ax, facecolor="none", edgecolor="green",
                      linewidth=1.5, zorder=4)
            legend_handles.append(Line2D([0],[0], color="green", lw=2,
                                          label="Protected Area"))

        # Intelligente Labels: nur Features mit 'name' und ausreichender Fläche
        total_area = bbox_geom.area
        min_area   = total_area / 300  # anpassen für bessere Lesbarkeit
        for subset, color in [(land, "black"), (water, "blue"),
                              (mil, "red"), (prot, "green")]:
            if "name" in subset.columns:
                dfn = subset.dropna(subset=["name"])
                for _, row in dfn.iterrows():
                    if row.geometry.area < min_area:
                        continue
                    pt = row.geometry.centroid
                    ax.text(pt.x, pt.y, row["name"], fontsize=6,
                            color=color, ha="center", va="center",
                            path_effects=[pe.withStroke(linewidth=1,
                                    foreground="white")])

    # Legende, Titel, Layout
    ax.legend(handles=legend_handles, loc="lower left", fontsize=8)
    ax.set_title(cfg.get("name","Karte").capitalize())
    ax.axis("off")
    plt.tight_layout()

    # Speichern oder Anzeigen
    out = cfg.get("output_plot")
    if out:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        plt.savefig(out, dpi=300, bbox_inches="tight")
        log.info(f"Plot gespeichert nach {out}")
    else:
        plt.show()

if __name__ == "__main__":
    plot_map()
