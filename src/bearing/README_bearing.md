# Inhaltsverzeichnis

- [1. Bearing-Projekt](#1-bearing-projekt)  
- [2. Projektstruktur](#2-projektstruktur)  
- [3. Step-by-step Pipeline](#3-step-by-step-pipeline)  
- [4. Config-Referenz](#4-config-referenz)  
- [5. Typical Full Run](#5-typical-full-run)  

---

## 1. Bearing-Projekt

`bearing` ist eine modulare Python-Pipeline zur Verarbeitung von AIS-Daten aus Sicht einer fixen Antenne.  
Ziel ist es, aus historischen AIS-Meldungen

1. **Filterung & Bereinigung**  
2. **Interpolation** auf ein konsistentes Zeitraster  
3. **Berechnung**  
   - **Initial Bearing**  
   - **Peilungsänderungs-Rate** (°/s)  
   - **Distanz** zur Antenne  
4. **Statistische Aufbereitung** eines sektoriellen 2-D-Histogramms  
5. **Erzeugung einer Lookup-Table** (LUT) für bedingte Distanz-PDFs  

---

## 2. Projektstruktur

```
src/
└── bearing/
    ├── config/
    │   └── bearing.json              # Alle Parameter & Ausgabepfade
    ├── processed_data/               # Ausgabedaten aller Pipeline-Stufen
    │   ├── 01_cleaned.csv            # Gefilterte & gesäuberte AIS-Daten
    │   ├── 02_interpolated.csv       # + äquidistante Zeitstempel
    │   ├── 03_bearing.csv            # + Initial Bearing (°)
    │   ├── 04_rate.csv               # + Peilungsänderungs-Rate (°/s)
    │   ├── 05_distance.csv           # + Distanz (m) zur Antenne
    │   └── 06_sector_histogram.csv   # Sektor-Histogramm → P(r | θ)
    ├── preprocess/                   # Preprocessing-Skripte
    │   ├── load_and_clean.py         # 1) AIS laden, filtern, Timestamp säubern
    │   ├── interpolate_timeseries.py # 2) Zeitliche Interpolation pro MMSI-Segment
    │   ├── compute_bearing.py        # 3) Initial Bearing berechnen
    │   ├── compute_rate.py           # 4) Peilungsänderungs-Rate berechnen
    │   ├── compute_distance.py       # 5) Distanz zur Antenne berechnen
    │   └── pipeline.py               # Wrapper: Schritt 1–5 in Folge ausführen
    ├── compute_sector_stats.py       # 6) Sektor-Histogramm (Azimut × Distanz)
    ├── build_range_lut.py            # Beispiel: Range-LUT abfragen (P(r|θ,ω))
    ├── lookup_range.py               # Beispiel: Range-LUT abfragen (P(r|θ,ω))
    ├── math.md
    └── README_bearing.md
```

---

# 3.  Step-by-step pipeline

Jeder Schritt liest dieselbe **`--config bearing.json`**:

| #  | Command                                                                                           | Beschreibung                                              |
|----|---------------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| 1  | `python src/bearing/preprocess/load_and_clean.py --config src/bearing/config/bearing.json`        | Filter & Bereinigung → `01_cleaned.csv`                   |
| 2  | `python src/bearing/preprocess/interpolate_timeseries.py --config src/bearing/config/bearing.json`| Einheits-Zeitraster (z.B. 20 s) → `02_interpolated.csv`   |
| 3  | `python src/bearing/preprocess/compute_bearing.py --config src/bearing/config/bearing.json`       | Peilung berechnen → `03_bearing.csv`                      |
| 4  | `python src/bearing/preprocess/compute_rate.py --config src/bearing/config/bearing.json`          | Peilungs-Rate → `04_rate.csv`                             |
| 5  | `python src/bearing/preprocess/compute_distance.py --config src/bearing/config/bearing.json`      | Distanz zur Antenne → `05_distance.csv`                   |
| 6  | `python src/bearing/preprocess/compute_sector_stats.py --config src/bearing/config/bearing.json`  | Sektor-Histogramm → `06_sector_histogram.csv`             |

Nach Schritt 6 liegen dir alle CSVs und ein sektorielles Wahrscheinlichkeits-Histogramm vor.

---

# 4.  Config reference

### `src/bearing/config/bearing.json`

| Key                          | Typ        | Default    | Bedeutung                                                         |
|------------------------------|------------|------------|-------------------------------------------------------------------|
| `input_csv`                  | String     | —          | Pfad zu den Roh-AIS-Daten                                         |
| `timestamp_column`           | String     | `# Timestamp` | Spaltenname mit Zeitstempel                                  |
| `dayfirst`                   | Bool       | `true`     | Datumsparsing im DMY-Format                                      |
| `drop_invalid_ts`            | Bool       | `true`     | Ungültige Timestamps verwerfen                                   |
| `lat_column`, `lon_column`   | String     | —          | Spaltennamen für Breiten-/Längengrad                              |
| `ais_filters`                | Objekt     | —          | OSM-like Filter für AIS-Daten (Class, Status, Ship type etc.)     |
| **Interpolation**            |            |            |                                                                   |
| └─ `interpolation.interval_seconds` | Int   | `20`       | Zeitraster in Sekunden                                            |
| └─ `interpolation.max_gap_minutes` | Int     | `60`       | Max. Lücke → neuer Segment                                       |
| **Antenne**                  |            |            |                                                                   |
| └─ `antenna.latitude`        | Float      | —          | Antennen-Breitengrad                                              |
| └─ `antenna.longitude`       | Float      | —          | Antennen-Längengrad                                               |
| **Δt für Rate**              |            |            |                                                                   |
| └─ `delta_t_sec`             | Int        | Interval  | Sekunden-Intervall für Rate-Berechnung                             |
| **Ausgabe-Pfade**            | Objekt     | —          |                                                                   |
| └─ `output.cleaned_csv`      | String     | —          | Gefilterte AIS-Daten                                              |
| └─ `output.interpolated_csv` | String     | —          | AIS mit äquidistantem Zeitraster                                  |
| └─ `output.with_bearing_csv` | String     | —          | AIS mit Peilung                                                   |
| └─ `output.with_distance_csv`| String     | —          | AIS mit Distanz                                                   |
| └─ `output.with_rate_csv`    | String     | —          | AIS mit Peilungs-Rate                                             |
| └─ `output.sector_hist_csv`  | String     | —          | Sektor-Histogramm CSV                                             |

---

# 5.  Typical full run

```bash
# 0. Virtualenv aktivieren, Abhängigkeiten installieren
source .venv/bin/activate
pip install -r requirements.txt

# 1. AIS-Vorverarbeitung
python src/bearing/preprocess/load_and_clean.py        --config src/bearing/config/bearing.json
python src/bearing/preprocess/interpolate_timeseries.py --config src/bearing/config/bearing.json

# 2. Feature-Berechnung
python src/bearing/preprocess/compute_bearing.py   --config src/bearing/config/bearing.json
python src/bearing/preprocess/compute_rate.py      --config src/bearing/config/bearing.json
python src/bearing/preprocess/compute_distance.py  --config src/bearing/config/bearing.json

# 3. Statistik & Histogramm
python src/bearing/preprocess/compute_sector_stats.py --config src/bearing/config/bearing.json

# Ergebnis
# • data/processed/bearing/ais_with_rate.csv
# • data/processed/bearing/sector_histogram_5deg_500m.csv