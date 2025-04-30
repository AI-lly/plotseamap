#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preprocessing für AIS-Schiffstyp-Klassifikation
------------------------------------------------

1. Lädt rohe AIS-CSV
2. Parsed Timestamps (dd/mm/YYYY), verwirft ungültige Zeilen
3. Wendet konfigurierbare AIS-Filter an (Class A/B, Status, Position device)
4. Berechnet Δt-Spalte (Sekunden) pro MMSI
5. Legt Zielvariable `is_cargo` an
6. Entfernt Zeilen mit fehlenden Werten in wichtigen Features
7. Speichert das bereinigte CSV
"""

import os
import json
import logging
import click
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
@click.command()
@click.option(
    "--config", "config_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur Preprocessing-Config (JSON)"
)
def preprocess(config_path: str):
    """
    Führe AIS-Preprocessing durch gemäß der JSON-Konfiguration.
    """
    # ─────────────────────────────────────────────────────────────────────────
    # 0) Config einlesen
    # ─────────────────────────────────────────────────────────────────────────
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    input_csv       = cfg["input_csv"]
    output_csv      = cfg["output_clean_csv"]
    ais_filters     = cfg["ais_filters"]
    ts_col          = cfg["timestamp_column"]
    ship_type_col   = cfg["ship_type_column"]
    cargo_value     = cfg["cargo_value"]
    dropna_features = cfg["dropna_features"]

    # ─────────────────────────────────────────────────────────────────────────
    # 1) Rohdaten laden
    # ─────────────────────────────────────────────────────────────────────────
    df = pd.read_csv(
        input_csv,
        low_memory=False
    )
    n_msgs_before  = len(df)
    n_ships_before = df["MMSI"].nunique()
    log.info(f"📥 Eingelesen: {n_msgs_before:,} AIS-Meldungen von {n_ships_before:,} Schiffen")

    # ─────────────────────────────────────────────────────────────────────────
    # 2) Timestamp parsen & ungültige verwerfen
    # ─────────────────────────────────────────────────────────────────────────
    log.info(f"⏳ Parsen Timestamps in Spalte '{ts_col}' …")
    df[ts_col] = pd.to_datetime(
        df[ts_col],
        dayfirst=True,
        errors="coerce"
    )
    n_bad = df[ts_col].isna().sum()
    if n_bad:
        log.warning(f"   {n_bad:,} ungültige Timestamps verworfen")
        df = df.dropna(subset=[ts_col])
    log.info(f"   {len(df):,} Meldungen mit gültigem Timestamp verbleibend")

    # ─────────────────────────────────────────────────────────────────────────
    # 3) AIS-Filter anwenden
    # ─────────────────────────────────────────────────────────────────────────
    for col, crit in ais_filters.items():
        msgs_before  = len(df)
        ships_before = df["MMSI"].nunique()
        if isinstance(crit, list):
            df = df[df[col].isin(crit)]
            cond = f"{col} ∈ {crit}"
        else:
            df = df[df[col] == crit]
            cond = f"{col} == '{crit}'"
        msgs_after  = len(df)
        ships_after = df["MMSI"].nunique()
        log.info(
            f"🔹 Nach Filter ({cond}): "
            f"{msgs_after:,} Meldungen ({msgs_before-msgs_after:,} entfernt), "
            f"{ships_after:,} Schiffe ({ships_before-ships_after:,} entfernt)"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 4) Δt-Spalte berechnen
    # ─────────────────────────────────────────────────────────────────────────
    log.info("⏱ Berechne Δt (Sekunden) pro MMSI …")
    df = df.sort_values(["MMSI", ts_col]).reset_index(drop=True)
    df["delta_t"] = (
        df.groupby("MMSI")[ts_col]
          .diff()
          .dt.total_seconds()
          .fillna(0)
    )
    log.info(f"   Δt erfolgreich hinzugefügt für {len(df):,} Meldungen")

    # ─────────────────────────────────────────────────────────────────────────
    # 5) Zielvariable 'is_cargo' anlegen
    # ─────────────────────────────────────────────────────────────────────────
    df["is_cargo"] = (df[ship_type_col] == cargo_value).astype(int)
    counts = df["is_cargo"].value_counts().rename({1: "Cargo", 0: "Other"})
    log.info("🚢 Klassenverteilung nach Filterung:")
    for name, cnt in counts.items():
        log.info(f"   • {name}: {cnt:,}")

    # ─────────────────────────────────────────────────────────────────────────
    # 6) Fehlende Werte entfernen (dropna)
    # ─────────────────────────────────────────────────────────────────────────
    msgs_before  = len(df)
    ships_before = df["MMSI"].nunique()
    df_clean = df.dropna(subset=dropna_features)
    msgs_after   = len(df_clean)
    ships_after  = df_clean["MMSI"].nunique()
    log.info(
        f"🧹 Nach dropna({dropna_features}): "
        f"{msgs_after:,} Meldungen ({msgs_before-msgs_after:,} entfernt), "
        f"{ships_after:,} Schiffe ({ships_before-ships_after:,} entfernt)"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 7) Ergebnis speichern
    # ─────────────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_clean.to_csv(output_csv, index=False)
    log.info(f"✅ Gefilterte AIS-Daten gespeichert: {output_csv}")


if __name__ == "__main__":
    preprocess()

# python src/anomaly_detection/ships_classify/preprocess.py --config config/ships_classify.json