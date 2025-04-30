#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/anomaly_detection/ships_classify/sequences.py

Erzeugt nicht-überlappende Sequenzen der Länge L aus vorverarbeiteten AIS-Daten,
teilt in Train/Test-Splits auf Schiffebene und skaliert Features.
Speichert die Arrays als NumPy-Dateien.
"""
import os
import json
import logging

import click
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm

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
    help="Pfad zur JSON-Config (ships_classify.json)"
)
def main(config_path):
    """
    1) Liest AIS-CSV (cleaned) ein
    2) Filtert Schiffe mit < min_sequence_length Meldungen heraus
    3) Erzeugt nicht-überlappende Sequenzen der Länge sequence_length
    4) Teilt auf Train/Test (GroupShuffleSplit auf MMSI)
    5) Skaliert Features mit StandardScaler
    6) Speichert X_train, X_test, y_train, y_test als .npy
    """
    # --- 1) Config einlesen ---
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    log.info(f"Config geladen: {config_path}")

    input_csv        = cfg["output_clean_csv"]
    output_dir       = cfg.get("output_dir", "data/processed/sequences")
    ts_col           = cfg["timestamp_column"]
    min_seq_length   = cfg["min_sequence_length"]
    L                = cfg["sequence_length"]
    test_size        = cfg.get("test_size", 0.2)
    random_state     = cfg.get("random_state", 42)
    features         = cfg["dropna_features"] + (["delta_t"] if "delta_t" not in cfg["dropna_features"] else [])

    os.makedirs(output_dir, exist_ok=True)
    log.info(f"→ Ausgabeverzeichnis: {output_dir}")

    # --- 2) CSV einlesen ---
    df = pd.read_csv(
        input_csv,
        parse_dates=[ts_col],
        dtype={"MMSI": str},
        low_memory=False
    )
    log.info(f"📥 {len(df):,} Zeilen aus '{input_csv}' geladen")

    # --- 3) Mindestsequenzlänge filtern ---
    seq_lens = df.groupby("MMSI").size()
    valid_mmsi = seq_lens[seq_lens >= min_seq_length].index
    before_ships = df["MMSI"].nunique()
    df = df[df["MMSI"].isin(valid_mmsi)].copy()
    after_ships = df["MMSI"].nunique()
    log.info(f"✅ ≥{min_seq_length} Meldungen: {after_ships:,} Schiffe (−{before_ships - after_ships:,})")

    # --- 4) Sequenzen erzeugen (nicht-überlappend) ---
    X, y = [], []
    log.info(f"🔄 Erstelle Sequenzen (L={L}) aus {after_ships:,} Schiffen …")
    for mmsi, group in tqdm(df.groupby("MMSI"), desc="Schiffe", unit="Schiff"):
        g = group.sort_values(ts_col).reset_index(drop=True)
        label = int(g["is_cargo"].any())
        n = len(g)
        for start in range(0, n - L + 1, L):
            seq = g.iloc[start:start+L][features].values
            X.append(seq)
            y.append(label)

    X = np.array(X)  # (n_sequences, L, n_features)
    y = np.array(y)  # (n_sequences,)
    log.info(f"→ {X.shape[0]:,} Sequenzen erzeugt; Features={X.shape[2]}")

    # --- 5) Train/Test-Split auf MMSI-Ebene ---
    # jede MMSI so oft wiederholen, wie sie Sequenzen erzeugt hat
    mmsis = df["MMSI"].unique()
    seq_counts = [len(df[df.MMSI == m]) // L for m in mmsis]
    groups = np.repeat(mmsis, seq_counts)

    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(gss.split(X, y, groups=groups))

    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    train_ships = np.unique(groups[train_idx]).size
    test_ships  = np.unique(groups[test_idx]).size
    log.info(f"✅ Split: Train {X_train.shape[0]:,} seq von {train_ships:,} Schiffen; "
             f"Test {X_test.shape[0]:,} seq von {test_ships:,} Schiffen")

    # --- 6) Feature-Skalierung ---
    scaler = StandardScaler()
    flat = X_train.reshape(-1, X_train.shape[-1])
    scaler.fit(flat)
    def scale_arr(arr):
        flat_arr = arr.reshape(-1, arr.shape[-1])
        scaled  = scaler.transform(flat_arr)
        return scaled.reshape(arr.shape)

    X_train = scale_arr(X_train)
    X_test  = scale_arr(X_test)
    log.info("✅ Daten skaliert mit StandardScaler")

    # --- 7) Speichern als NumPy-Arrays ---
    np.save(os.path.join(output_dir, "X_train.npy"), X_train)
    np.save(os.path.join(output_dir, "X_test.npy"),  X_test)
    np.save(os.path.join(output_dir, "y_train.npy"), y_train)
    np.save(os.path.join(output_dir, "y_test.npy"),  y_test)
    log.info("💾 Sequenzen gespeichert in NumPy-Format")

if __name__ == "__main__":
    main()

# python src/anomaly_detection/ships_classify/sequences.py --config config/ships_classify.json