# 🗺️ Geo-Workflow

Ein vollständig automatisierter, flexibler Geodaten-Workflow zur Extraktion, Umwandlung und Analyse von OpenStreetMap-Daten für beliebige Regionen.

---

## 📦 Projektstruktur
```
project/
├── config/                      # Konfigurationsdateien (.json)
├── data/
│   ├── osm/                    # OSM-Daten (.pbf, .poly)
│   └── ais/                    # AIS-Daten (optional)
├── processed/
│   ├── geojson/                # Pufferbereiche (.geojson)
│   ├── poly/                   # .poly-Dateien (aus GeoJSON)
│   ├── clipped_osm/            # Ausgeschnittene OSM-Dateien
│   ├── geopackage/             # Analysefähige .gpkg-Dateien
│   └── shapefiles/             # (optional)
├── output/
│   └── plots/                  # Exportierte Visualisierungen
├── scripts/
│   ├── create_buffer.py            # Erstellt Pufferzone
│   ├── convert_to_poly.py          # Wandelt GeoJSON → .poly
│   ├── extract_clip.sh             # Schneidet .osm.pbf-Datei
│   ├── convert_to_gpkg.sh          # Konvertiert .osm.pbf → .gpkg
│   ├── plot_map.py                 # Visualisiert die Daten
│   ├── workflow.py                # Master-Workflow
│   ├── merge_osm.sh               # OSM-Merge mit osmosis
│   └── utils/
│       └── geo_helpers.py          # Helferfunktion save_as_poly()
└── README.md
```

---

## 🚀 Schnellstart

### 1. 🔽 OSM-Dateien herunterladen (z. B. von [Geofabrik](https://download.geofabrik.de/))
Speichern in:
```
data/osm/denmark-latest.osm.pbf
data/osm/schleswig-holstein-latest.osm.pbf
```

### 2. 🔗 OSM-Dateien zusammenführen

```bash
bash scripts/merge_osm.sh denmark-latest.osm.pbf schleswig-holstein-latest.osm.pbf denmark_sh.pbf
```

### 3. ▶️ Workflow starten
```bash
python scripts/workflow.py --config config/fehmarnbelt.json
```

### 4. 🖼️ Karte plotten
```bash
python scripts/plot_map.py --name fehmarnbelt
```

### ✅ Ergebnis-Dateien
- `processed/geojson/fehmarnbelt_buffer.geojson`
- `processed/poly/fehmarnbelt.poly`
- `processed/clipped_osm/cut_fehmarnbelt.osm.pbf`
- `processed/geopackage/fehmarnbelt.gpkg`
- `output/plots/fehmarnbelt_map_clipped.png`

---

## ⚙️ Abhängigkeiten

### 📦 Python
```bash
pip install geopandas shapely fiona matplotlib osmium
```

### 🔧 Systemtools (macOS über Homebrew)
```bash
brew install osmium-tool osmosis gdal
```

> `osmium-tool`: OSM-Dateien verarbeiten  
> `osmosis`: OSM-Dateien zusammenführen  
> `gdal`: Für `ogr2ogr`-Konvertierung

---

## 🧠 Erweiterbar für beliebige Regionen
Du kannst den Workflow einfach für andere Orte nutzen:
```json
{
  "name": "hamburg",
  "lon": 9.99,
  "lat": 53.55,
  "radius": 50,
  "source": "germany-latest.osm.pbf"
}
```

```bash
python scripts/workflow.py --config config/fehmarnbelt.json
```

---

## 🛠️ Noch geplant / möglich:
- Interaktive Karten mit Folium
- Integration von AIS-Daten (Schiffsbewegungen)
- Erweiterung um Routing, Wasserwege, Küstenlinien-Filter
- Export als Shapefiles oder GeoTIFF

---

## 📜 Lizenz
MIT License
