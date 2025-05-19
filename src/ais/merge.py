# src/ais/merge.py
import os
import glob
import json
import logging
import pandas as pd
import click

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

@click.command()
@click.option(
    "--config", "config_path",
    required=True,
    type=click.Path(exists=True),
    help="Pfad zur AIS-Config-JSON"
)
def merge_ais(config_path):
    """
    Liest alle CSV-Dateien im in der Config
    unter 'ais_folder' angegebenen Verzeichnis ein,
    hängt sie zusammen und schreibt sie nach 'merged_csv'.
    """
    # Config laden
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    input_dir  = cfg.get("ais_folder")
    output_csv = cfg.get("merged_csv")

    if not input_dir or not os.path.isdir(input_dir):
        log.error(f"Ungültiges AIS-Verzeichnis: {input_dir!r}")
        raise click.Abort()

    if not output_csv:
        log.error("Config muss 'merged_csv' enthalten.")
        raise click.Abort()

    # CSV-Dateien suchen
    pattern = os.path.join(input_dir, "*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        log.error(f"Keine CSV-Dateien gefunden in {input_dir}")
        raise click.Abort()

    log.info(f"Gefundene AIS-Dateien: {len(files)}")
    dfs = []
    for fp in files:
        log.info(f"Lese {fp}")
        df = pd.read_csv(fp, parse_dates=['# Timestamp'], low_memory=False)
        dfs.append(df)

    # zusammenführen
    combined = pd.concat(dfs, ignore_index=True)
    log.info(f"Kombinierte Länge: {len(combined):,} Zeilen")

    # ausgeben
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    combined.to_csv(output_csv, index=False)
    log.info(f"Zusammengeführte CSV geschrieben: {output_csv}")

if __name__ == "__main__":
    merge_ais()