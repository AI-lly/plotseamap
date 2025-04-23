import os
import glob
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
    "--input-dir", "input_dir",
    default="data/raw/ais",
    type=click.Path(exists=True),
    help="Verzeichnis mit den AIS-CSV-Dateien"
)
@click.option(
    "--output-csv", "output_csv",
    default="data/processed/ais/combined_ais.csv",
    type=click.Path(),
    help="Pfad zur zusammengeführten AIS-CSV-Datei"
)
def merge_ais(input_dir, output_csv):
    """
    Liest alle CSV-Dateien im angegebenen Verzeichnis ein,
    hängt sie zusammen und schreibt eine kombinierte CSV-Datei.
    """
    # Alle CSV-Dateien im Ordner finden
    pattern = os.path.join(input_dir, "*.csv")
    files = glob.glob(pattern)
    if not files:
        log.error(f"Keine CSV-Dateien gefunden in {input_dir}")
        return

    log.info(f"Gefundene AIS-Dateien: {len(files)}")
    dfs = []
    for fp in files:
        log.info(f"Lese {fp}")
        df = pd.read_csv(fp, parse_dates=['# Timestamp'], low_memory=False)
        dfs.append(df)

    # Zusammenführen
    combined = pd.concat(dfs, ignore_index=True)
    log.info(f"Kombinierte Länge: {len(combined)} Zeilen")

    # Ausgabepfad sicherstellen
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    combined.to_csv(output_csv, index=False)
    log.info(f"Gespeichert: {output_csv}")

if __name__ == '__main__':
    merge_ais()

# python src/ais/merge.py --input-dir data/raw/ais --output-csv data/processed/ais/combined_ais.csv