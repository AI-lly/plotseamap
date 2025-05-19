#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/bearing/pipeline.py

Führt die komplette Bearing-Pipeline mit einem Aufruf aus.

Beispiel:
    python src/bearing/pipeline.py \
        --config src/bearing/config/bearing.json
"""
import subprocess
import sys
from pathlib import Path
import logging
import click

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

# Hilfsfunktion, um ein Teilskript als Sub-Prozess zu starten
def run_step(script: Path, cfg: Path) -> None:
    cmd = [sys.executable, str(script), "--config", str(cfg)]
    log.info(f"▶️  {' '.join(Path(c).name for c in cmd)}")
    subprocess.check_call(cmd)

@click.command()
@click.option(
    "--config", "cfg_path", required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Pfad zur bearing.json",
)
def main(cfg_path):
    base = Path(__file__).resolve().parent

    steps = [
        "load_and_clean.py",
        "interpolate_timeseries.py",
        "compute_bearing.py",
        "compute_rate.py",
        "compute_distance.py",
    ]

    for script_name in steps:
        run_step(base / script_name, cfg_path)

    log.info("🎉 Pipeline fertig – End-CSV liegt unter "
             f"{Path(cfg_path).parents[2] / 'data/processed/bearing/ais_with_distance.csv'}")

if __name__ == "__main__":
    main()

# python src/bearing/pipeline.py --config src/bearing/config/bearing.json