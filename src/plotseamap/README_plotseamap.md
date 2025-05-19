# Inhaltsverzeichnis
- [Projektübersicht](#1-plotseamap)
- [Projektstruktur](#2-project-tree)
- [Pipeline-Schritte](#3-step-by-step-pipeline)
- [Konfigurationsreferenz](#4-config-reference)
- [Beispiel-Ablauf](#5-typical-full-run)

# 1. plotseamap

`plotseamap` ist eine kleine Python-Toolchain zum Extrahieren, Aufbereiten und Plotten von OSM-Daten für ein definiertes Seegebiet.  
Es unterstützt:

- **Merge** mehrerer OSM-PBF-Dateien in eine Datei  
- **Clipping** auf eine Kreis-Bounding-Box (BBox)  
- **Extraktion** von OSM-Features (Punkte, Linien, Polygone…) in ein GeoPackage (GPKG)  
- **Konvertierung** von GeoJSON zu GPKG  
- **Puffern** von Layern um einen angegebenen Radius  
- **Rendering** einer Basis-Karte mit smarter Küsten-/Wasser-Klassifizierung  

---

# 2.  Project tree

```
src/
└── plotseamap/
    ├── processed_data/         # generierte OSM/Geo-Outputs
    │   ├── osm/                # PBF-Dateien (merged.pbf, bbox-clip.pbf)
    │   ├── gpkg/               # GeoPackage-Exporte (GPKG mit Layers)
    │   ├── geojson/            # GeoJSON-Exporte (z. B. Puffer-Polygon)
    │   └── maps/               # gerenderte Karten (PNG)
    ├── config/                 # JSON-Konfigurationsdateien
    │   └── fehmarnbelt.json    # PlotSeaMap-Hauptconfig
    ├── buffer.py               # Puffer um Geometrien (z. B. Küstenlinien)
    ├── cli.py                  # Haupt-CLI (merge, clip, extract, buffer, plot)
    ├── clip.py                 # Bounding-Box-Clip (Wrapper für clip_bbox.py)
    ├── convert.py              # GeoJSON → GeoPackage (GPKG) Konverter
    ├── merge.py                # PBF-Merge Utility (osmium.SimpleWriter)
    ├── extract.py              # 2-Pass Streaming-Extraktion in GPKG
    ├── plot.py                 # Basemap-Plotter (erstellt PNG)
    └── README_plotseamap.md    # Module-spezifische Doku zu plotseamap
```


---

# 3.  Step by step pipeline

Build the local OSM map (`src/plotseamap`)

| # | Command | What happens |
|---|---------|--------------|
|1|`python src/plotseamap/cli.py --config src/plotseamap/config/fehmarnbelt.json merge`|merge Denmark + Schleswig‑Holstein PBF into `denmark_sh.pbf`|
|2|`python src/plotseamap/cli.py --config src/plotseamap/config/fehmarnbelt.json clip` |clip rectangular bbox → `fehmarnbelt_bbox.osm.pbf`|
|3|`python src/plotseamap/cli.py --config src/plotseamap/config/fehmarnbelt.json extract`|2‑pass stream → multi‑layer `fehmarnbelt_data.gpkg`|
|4|`python src/plotseamap/cli.py --config src/plotseamap/config/ehmarnbelt.json buffer` |500 m coastal buffer → `fehmarnbelt_buffer.geojson`|
|5|`python src/plotseamap/plot.py --config src/plotseamap/config/fehmarnbelt.json`|render static basemap `fehmarnbelt_base.png`|

After step 5 you have a ready PNG and a GeoJSON mask for further use.

---

# 4.  Config reference                                

### `src/plotseamap/config/fehmarnbelt.json`

| Key | Meaning |
|-----|---------|
|`radius`|40 ⇒ circle radius in **km** for initial cut|
|`buffer_distance`|500 ⇒ coastal buffer in **m**|
|`extract_layers`|OSM layers to keep (points can be excluded) |
|`output_base_map`|target PNG for the basemap|


---

# 5.  Typical full run

```bash
# 0.  Activate venv, install packages
source AIS/bin/activate

# 1.  Map pipeline (takes ~45 min once)
python src/plotseamap/cli.py --config src/plotseamap/config/fehmarnbelt.json merge
python src/plotseamap/cli.py --config src/plotseamap/config/fehmarnbelt.json clip
python src/plotseamap/cli.py --config src/plotseamap/config/fehmarnbelt.json extract
python src/plotseamap/cli.py --config src/plotseamap/config/fehmarnbelt.json buffer
python src/plotseamap/plot.py  --config src/plotseamap/config/fehmarnbelt.json


