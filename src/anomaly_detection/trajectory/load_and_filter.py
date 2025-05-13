#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/anomaly_detection/trajectory/load_and_filter.py

Lädt die AIS-Rohdaten, wendet alle konfigurierten Filter an,
erstellt eine binäre Zielspalte für den ausgewählten Schiffstyp
und speichert das Ergebnis als "cleaned" CSV für die weitere
Trajektorie-Analyse.
"""
import os
import json
import logging

import click
import pandas as pd

# ───────────────────────────────────────────────────────────────────────
# Logging konfigurieren
# ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)


@click.command()
@click.option(
    "--config", "config_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur JSON-Konfigurationsdatei"
)
def cli(config_path: str):
    """
    Lädt AIS-Daten, filtert sie gemäß Config, berechnet is_cargo und delta_t,
    und schreibt das gefilterte Ergebnis in eine CSV.
    """
    # 1) Config einlesen
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    log.info(f"→ Config geladen: {config_path}")

    # 2) Parameter aus Config
    input_csv        = cfg["input_csv"]
    filters          = cfg["ais_filters"]
    ts_col           = cfg["timestamp"]["column"]
    dayfirst         = cfg["timestamp"].get("dayfirst", True)
    drop_invalid_ts  = cfg["timestamp"].get("drop_invalid", True)
    delta_group      = cfg["delta_t"]["group_by"]
    target_type      = cfg["target_ship_type"]
    output_clean_csv = cfg["output"]["cleaned_csv"]
    
    # 3) Rohdaten einlesen
    log.info(f"📥 Lade Rohdaten: {input_csv}")
    df = pd.read_csv(
        input_csv,
        parse_dates=[ts_col],
        dayfirst=dayfirst,
        low_memory=False
    )
    log.info(f"→ Ursprüngliche Zeilen: {len(df):,}")

    # 4) OSM‐ähnliche Filter anwenden
    before = len(df)
    for col, crit in filters.items():
        if isinstance(crit, list):
            df = df[df[col].isin(crit)]
        else:
            df = df[df[col] == crit]
        removed = before - len(df)
        log.info(f"🔹 Filter {col!r}: entfernt {removed:,}, verbleibend {len(df):,}")
        before = len(df)

    # 5) Zielvariable 'is_cargo' anlegen
    df["is_cargo"] = (df["Ship type"] == target_type).astype(int)
    counts = df["is_cargo"].value_counts().rename({1: target_type, 0: "Other"})
    log.info("🚢 Klassenverteilung nach allen Filtern:")
    for cls, cnt in counts.items():
        pct = cnt / len(df) * 100
        log.info(f"    • {cls:<5}: {cnt:,} ({pct:.1f} %)")

    # 6) Optional: nur Zielklasse behalten
    df = df[df["is_cargo"] == 1]
    log.info(f"✅ Auf '{target_type}' eingeschränkt: {len(df):,} Zeilen verbleibend")

    # 7) Timestamp‐Bereinigung
    if drop_invalid_ts:
        n0 = len(df)
        df = df.dropna(subset=[ts_col])
        n1 = len(df)
        log.info(f"🕒 Ungültige Timestamps verworfen: {n0-n1:,} → {n1:,} verbleibend")

    # 8) Δt‐Spalte berechnen (in Sekunden)
    df = df.sort_values([delta_group, ts_col]).reset_index(drop=True)
    df["delta_t"] = (
        df.groupby(delta_group)[ts_col]
          .diff()
          .dt.total_seconds()
          .fillna(0)
    )
    log.info(f"⏱ Δt berechnet für {len(df):,} Meldungen")

    # 9) Ergebnis speicher
    os.makedirs(os.path.dirname(output_clean_csv), exist_ok=True)
    df.to_csv(output_clean_csv, index=False)
    log.info(f"✅ Gefilterte und angereicherte AIS-Daten gespeichert: {output_clean_csv}")


if __name__ == "__main__":
    cli()


# python src/anomaly_detection/trajectory/load_and_filter.py --config config/trajectory.json