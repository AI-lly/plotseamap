#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/load_and_clean.py

Lädt die Roh-AIS-Daten, wendet alle in der Config definierten Filter an
(inkl. Klasse, Status, Positionstyp, Ship type, Cargo type),
säubert ungültige Timestamps, und schreibt das Ergebnis in eine "cleaned" CSV.
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
    help="Pfad zur JSON-Config (bearing.json)"
)
def cli(config_path: str):
    """
    1) Config laden
    2) Rohdaten einlesen
    3) AIS-Filter anwenden
    4) Ungültige Timestamps verwerfen
    5) Gefilterte Daten speichern
    """
    # 1) Config laden
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    log.info(f"→ Config geladen: {config_path}")

    # 2) Parameter aus Config
    input_csv       = cfg["input_csv"]
    ts_col          = cfg["timestamp_column"]
    dayfirst        = cfg.get("dayfirst", True)
    drop_invalid_ts = cfg.get("drop_invalid_ts", True)
    filters         = cfg.get("ais_filters", {})
    output_csv      = cfg["output"]["cleaned_csv"]
    usecols         = cfg.get("columns", None)  # falls nicht gesetzt: None

    # 3) Rohdaten einlesen
    log.info(f"📥 Lade Rohdaten: {input_csv}")
    df = pd.read_csv(
        input_csv,
        usecols=usecols,
        parse_dates=[ts_col],
        dayfirst=dayfirst,
        low_memory=False
    )
    log.info(f"→ Eingelesene Spalten: {df.columns.tolist()}")
    log.info(f"📥 Ursprüngliche AIS-Zeilen: {len(df):,}")
    log.info(f"📥 Ursprüngliche Schiffe: {df['MMSI'].nunique():,}")

    # 4) OSM-artige Filter anwenden × alle ais_filters
    for col, crit in filters.items():
        before_rows = len(df)
        before_ships = df["MMSI"].nunique()

        if isinstance(crit, list):
            df = df[df[col].isin(crit)]
        else:
            df = df[df[col] == crit]

        after_rows = len(df)
        after_ships = df["MMSI"].nunique()
        log.info(
            f"🔹 Filter {col!r}: "
            f"Zeilen {before_rows:,} → {after_rows:,} "
            f"(-{before_rows-after_rows:,}); "
            f"Schiffe {before_ships:,} → {after_ships:,} "
            f"(-{before_ships-after_ships:,})"
        )

    # 5) Timestamp-Bereinigung
    if drop_invalid_ts:
        n0 = len(df)
        df = df.dropna(subset=[ts_col])
        n1 = len(df)
        log.info(f"🕒 Ungültige Timestamps verworfen: {n0-n1:,} → {n1:,} verbleibend")

    # 6) Ergebnis speichern
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    log.info(f"✅ Gefilterte AIS-Daten gespeichert: {output_csv}")


if __name__ == "__main__":
    cli()

# python src/bearing/load_and_clean.py --config src/bearing/config/bearing.json