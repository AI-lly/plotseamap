# Fehmarnbelt — OSM Map + AIS Tracks

A compact Python workflow that

* **extracts** OpenStreetMap data for a 40 km radius around the Fehmarnbelt,
* builds a clean **base map** (land, water, military, protected),
* **filters & joins** daily Danish AIS CSV files,
* plots **ship trajectories** on top of the base map,
* runs only on pure‑Python libraries (no `osmium‑tool`, `osmosis`, `gdal`).

---

## 1  Project tree

```
.
├── config/                 # JSON configs
│   ├── fehmarnbelt.json    # OSM / map pipeline
│   └── ais_filters.json    # AIS filters & plotting
├── data/
│   ├── raw/
│   │   ├── osm/ …          # *.pbf downloads
│   │   └── ais/ …          # aisdk‑YYYY‑MM‑DD.csv files
│   ├── processed/
│   │   ├── osm/ …          # clipped PBF
│   │   ├── gpkg/ …         # extracted GeoPackage
│   │   ├── geojson/ …      # buffer polygon
│   │   ├── maps/ …         # static PNG basemap
│   │   └── ais/ …          # merged + filtered AIS CSV
│   └── …
├── output/plots/           # final figures
├── src/
│   ├── plotseamap/
│   │   ├── cli.py          # merge, clip, extract, buffer, basemap‑plot
│   │   ├── merge.py        # pure‑python PBF merge
│   │   ├── clip_bbox.py    # rectangular clip
│   │   ├── extract.py      # 2‑pass streaming extraction → GPKG
│   │   ├── buffer.py       # 500‑m coastal buffer
│   │   └── plot.py         # save basemap PNG
│   └── ais/
│       ├── cli.py          # loader + plot entry points
│       ├── loader.py       # merge & filter AIS CSVs
│       └── plot.py         # draw trajectories on basemap
└── README.md               # you are here
```

---

## 2  Environment

```bash
python -m venv AIS
source AIS/bin/activate
pip install -r requirements.txt   # geopandas, pyogrio, osmium, click, …
```

---

## 3  Step‑by‑step pipeline

> **Run every command from the project root.** All scripts are pure‑Python; no extra binaries needed.

### 3.1  Build the local OSM map (`src/plotseamap`)

| # | Command | What happens |
|---|---------|--------------|
|1|`python src/plotseamap/cli.py --config config/fehmarnbelt.json merge`|merge Denmark + Schleswig‑Holstein PBF into `denmark_sh.pbf`|
|2|`python src/plotseamap/cli.py --config config/fehmarnbelt.json clip` |clip rectangular bbox → `fehmarnbelt_bbox.osm.pbf`|
|3|`python src/plotseamap/cli.py --config config/fehmarnbelt.json extract`|2‑pass stream → multi‑layer `fehmarnbelt_data.gpkg`|
|4|`python src/plotseamap/cli.py --config config/fehmarnbelt.json buffer` |500 m coastal buffer → `fehmarnbelt_buffer.geojson`|
|5|`python src/plotseamap/plot.py      --config config/fehmarnbelt.json`|render static basemap `fehmarnbelt_base.png`|

After step 5 you have a ready PNG and a GeoJSON mask for further use.

### 3.2  Prepare AIS data (`src/ais`)

1. **Combine & filter all raw CSVs** (can be one or many days):

```bash
python src/ais/loader.py   \
       --config config/ais_filters.json
```

* reads all `data/raw/ais/*.csv` (or the single file given by `ais_file`),
* unions them, applies the filter block (`ais_filters`),
* stores `data/processed/ais/fehmarnbelt_ais_filtered.csv`.

2. **Plot trajectories on the basemap**:

```bash
python src/ais/plot.py     \
       --config config/ais_filters.json
```

* loads the PNG created in step 3.1‑5,
* clips points with the same buffer polygon,
* connects points per `MMSI` to a LineString,
* draws tracks in orange (`track_color`) on top,
* writes `output/plots/fehmarnbelt_ais.png`.

---

## 4  Config reference

### `config/fehmarnbelt.json`

| Key | Meaning |
|-----|---------|
|`radius`|40 ⇒ circle radius in **km** for initial cut|
|`buffer_distance`|500 ⇒ coastal buffer in **m**|
|`extract_layers`|OSM layers to keep (points can be excluded) |
|`output_base_map`|target PNG for the basemap|

### `config/ais_filters.json`

| Key | Meaning |
|-----|---------|
|`bbox_geojson`|mask polygon from buffer step|
|`ais_filters`|dictionary: column → allowed value(s) |
|`base_map_png`|PNG produced by plotseamap/plot.py |
|`track_color / width`|styling parameters for AIS lines |

---

## 5  Typical full run

```bash
# 0.  Activate venv, install packages
source AIS/bin/activate

# 1.  Map pipeline (takes ~45 min once)
python src/plotseamap/cli.py --config config/fehmarnbelt.json merge
python src/plotseamap/cli.py --config config/fehmarnbelt.json clip
python src/plotseamap/cli.py --config config/fehmarnbelt.json extract
python src/plotseamap/cli.py --config config/fehmarnbelt.json buffer
python src/plotseamap/plot.py  --config config/fehmarnbelt.json

# 2.  AIS pipeline (seconds‑minutes)
python src/ais/loader.py --config config/ais_filters.json
python src/ais/plot.py   --config config/ais_filters.json

# 3.  Enjoy
open output/plots/fehmarnbelt_ais.png   # macOS preview
```

---

## 6  Troubleshooting

| Issue | Fix |
|-------|-----|
|`Layer 'xyz' could not be opened` | Check `extract_layers` vs. actual layers in GeoPackage (`fiona.listlayers`). |
|`NULL pointer error` on extract | Delete old *.gpkg before rerun; ensure write permissions. |
|No AIS points plotted | Verify bbox overlap; increase `buffer_distance` or check AIS filter values. |

---

## 7  Contributing / TODO

* CI workflow (pytest + tiny sample data)
* Switch AIS plotting to Datashader for millions of points
* Export interactive Leaflet / Kepler.gl HTML map

Pull requests welcome!

