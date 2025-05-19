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
    │   └── bearing.json              # Zentrale Parameter & Ausgabepfade
    ├── processed_data/               # Ausgabedaten aller Pipeline-Stufen
    │   ├── 01_cleaned.csv            # Gefiltert & gesäubert
    │   ├── 02_interpolated.csv       # + äquidistante Zeitstempel
    │   ├── 03_bearing.csv            # + Initial Bearing (°)
    │   ├── 04_rate.csv               # + Peilungsänderungsrate (°/s)
    │   ├── 05_distance.csv           # + Distanz zur Antenne (m)
    │   └── 06_sector_histogram.csv   # Sektor-Histogramm → P(r | θ)
    ├── preprocess/                   # Vorverarbeitungsskripte
    │   ├── load_and_clean.py         # 1) AIS laden & filtern
    │   ├── interpolate_timeseries.py # 2) Zeit-Interpolation pro MMSI
    │   ├── compute_bearing.py        # 3) Initial Bearing berechnen
    │   ├── compute_rate.py           # 4) Peilungsänderungsrate berechnen
    │   ├── compute_distance.py       # 5) Distanzberechnung zur Antenne
    │   └── pipeline.py               # Wrapper: Schritte 1–5 in Serie
    ├── compute_sector_stats.py       # 6) Sektor-Histogramm (Azimut × Distanz)
    ├── build_range_lut.py            # Erzeuge Lookup-Table für P(r | θ,ω)
    ├── lookup_range.py               # Beispiel: Abfrage der Range-LUT
    ├── math.md                       # Mathematische Herleitung & Notation
    └── README_bearing.md             # Anleitung & Projektübersicht
```

---

# 3.  Step-by-step pipeline

Jeder Schritt liest dieselbe **`--config src/bearing/config/bearing.json`** und schreibt seine Ausgabe nach `processed_data/`.

| #   | Command                                                                                             | Output                              | Beschreibung                                                    |
|-----|-----------------------------------------------------------------------------------------------------|-------------------------------------|-----------------------------------------------------------------|
| 1   | `python src/bearing/preprocess/load_and_clean.py --config src/bearing/config/bearing.json`         | `01_cleaned.csv`                    | AIS-Daten filtern & Timestamps säubern                          |
| 2   | `python src/bearing/preprocess/interpolate_timeseries.py --config src/bearing/config/bearing.json` | `02_interpolated.csv`               | Einheitliches Zeitraster (z. B. 20 s) pro MMSI-Segment           |
| 3   | `python src/bearing/preprocess/compute_bearing.py --config src/bearing/config/bearing.json`        | `03_bearing.csv`                    | Initial-Bearing (°) für jeden Zeitstempel                       |
| 4   | `python src/bearing/preprocess/compute_rate.py --config src/bearing/config/bearing.json`           | `04_rate.csv`                       | Peilungs-Änderungsrate (°/s)                                     |
| 5   | `python src/bearing/preprocess/compute_distance.py --config src/bearing/config/bearing.json`       | `05_distance.csv`                   | Distanz (m) zur Antenne                                          |
| 6   | `python src/bearing/preprocess/compute_sector_stats.py --config src/bearing/config/bearing.json`   | `06_sector_histogram.csv`           | Sektor-Histogramm (Azimut × Distanz) → P(r | θ)                   |
| 7   | `python src/bearing/build_range_lut.py --config src/bearing/config/bearing.json`                   | `range_lut.pkl`                     | Lookup-Table für P(r | θ, ω) aus Histogramm                       |
| 8   | `python src/bearing/lookup_range.py 88 -0.042 --lut src/bearing/processed_data/range_lut.pkl`      | (stdout: Wahrscheinlichkeiten)      | Distanz-PDF für θ = 88° und ω = −0.042 °/s aus der Lookup-Table  |

Nach Schritt 7 liegt die Pickle-Datei `range_lut.pkl` vor, und Schritt 8 zeigt exemplarisch, wie man für einen gemessenen Bearing und eine Bearing-Rate die bedingte Distanzverteilung abfragt.

---

# 4.  Config reference

### `src/bearing/config/bearing.json`

| Key                                    | Typ        | Default    | Bedeutung                                                         |
|----------------------------------------|------------|------------|-------------------------------------------------------------------|
| `input_csv`                            | String     | —          | Pfad zu den Roh-AIS-Daten                                         |
| `timestamp_column`                     | String     | `# Timestamp` | Spaltenname mit Zeitstempel                                  |
| `dayfirst`                             | Bool       | `true`     | Datumsparsing im DMY-Format                                      |
| `drop_invalid_ts`                      | Bool       | `true`     | Ungültige Timestamps verwerfen                                   |
| `lat_column`, `lon_column`             | String     | —          | Spaltennamen für Breiten- und Längengrad                          |
| `distance_column`                      | String     | `dist_m`   | Spaltenname für Distanz zur Antenne                              |
| `ais_filters`                          | Objekt     | —          | OSM-like Filter für AIS-Daten (Class, Status, Ship type etc.)     |
| **Interpolation**                      | —          | —          |                                                                   |
| └─ `interpolation.interval_seconds`    | Int        | `20`       | Zeitraster in Sekunden                                            |
| └─ `interpolation.max_gap_minutes`     | Int        | `60`       | Max. Lücke → neuer Segment                                       |
| **Antenne**                            | —          | —          |                                                                   |
| └─ `antenna.latitude`                  | Float      | —          | Antennen-Breitengrad                                              |
| └─ `antenna.longitude`                 | Float      | —          | Antennen-Längengrad                                               |
| **Δt für Rate**                        | —          | —          |                                                                   |
| └─ `delta_t_sec`                       | Int        | `20`       | Konstanter Δt (in s) zur Berechnung der Peilungs-Rate             |
| **Ausgabe-Pfade**                      | Objekt     | —          |                                                                   |
| └─ `output.cleaned_csv`                | String     | —          | Gefilterte AIS-Daten                                              |
| └─ `output.interpolated_csv`           | String     | —          | AIS mit äquidistantem Zeitraster                                  |
| └─ `output.with_bearing_csv`           | String     | —          | AIS mit berechneter Peilung                                       |
| └─ `output.with_rate_csv`              | String     | —          | AIS mit berechneter Peilungs-Rate                                  |
| └─ `output.with_distance_csv`          | String     | —          | AIS mit berechneter Distanz                                       |
| └─ `output.sector_hist_csv`            | String     | —          | Sektor-Histogramm CSV                                             |
| └─ `output.sector_hist_png`            | String     | —          | Polar-Heatmap als PNG                                             |
| **Statistics**                         | —          | —          |                                                                   |
| └─ `statistics.az_bin_deg`             | Int        | `5`        | Azimut-Bin-Breite (in °)                                           |
| └─ `statistics.rate_edges`             | List[Float]| `[0,0.01,…,10]` | Kanten der Bearing-Rate-Bins (in °/s)                     |
| └─ `statistics.r_step_m`               | Int        | `500`      | Distanz-Bin-Breite (in m)                                          |
| └─ `statistics.r_max_m`                | Int        | `20000`    | Maximaler Radius (in m) für Histogramm                             |
| └─ `statistics.output`                 | String     | —          | Pfad zur Pickle-Datei mit der Lookup-Table                         |

---

# 5.  Typical full run

```bash
# 0) Virtuelle Umgebung aktivieren & Abhängigkeiten installieren
source .venv/bin/activate
pip install -r requirements.txt

# 1) Preprocessing
python src/bearing/preprocess/load_and_clean.py --config src/bearing/config/bearing.json
python src/bearing/preprocess/interpolate_timeseries.py --config src/bearing/config/bearing.json

# 2) Feature-Berechnung
python src/bearing/preprocess/compute_bearing.py --config src/bearing/config/bearing.json
python src/bearing/preprocess/compute_rate.py --config src/bearing/config/bearing.json
python src/bearing/preprocess/compute_distance.py --config src/bearing/config/bearing.json

# 3) Statistik & Histogramme
python src/bearing/compute_sector_stats.py --config src/bearing/config/bearing.json

# 4) Lookup-Table erzeugen & Abfrage
python src/bearing/build_range_lut.py --config src/bearing/config/bearing.json
python src/bearing/lookup_range.py 88 -0.042 --lut src/bearing/processed_data/range_lut.pkl

# Ergebnisse finden Sie in:
#  • src/bearing/processed_data/01_cleaned.csv
#  • src/bearing/processed_data/02_interpolated.csv
#  • src/bearing/processed_data/03_bearing.csv
#  • src/bearing/processed_data/04_rate.csv
#  • src/bearing/processed_data/05_distance.csv
#  • src/bearing/processed_data/06_sector_histogram.csv
#  • src/bearing/processed_data/range_lut.pkl