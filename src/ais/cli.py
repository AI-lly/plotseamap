import click
import logging
from loader import load_and_process_ais

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

@click.command()
@click.option(
    "--config", "config_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur AIS-Filter-Config-JSON-Datei"
)
def cli(config_path):
    """
    CLI für AIS-Datenverarbeitung:
    Lädt CSV, wendet BBox und Filter an und speichert das Ergebnis.
    """
    log.info(f"Starte AIS-Verarbeitung mit Config: {config_path}")
    gdf_filtered = load_and_process_ais(config_path)
    log.info(f"Verarbeitung abgeschlossen: {len(gdf_filtered)} Punkte")

if __name__ == "__main__":
    cli()
