import subprocess
import argparse
import json
import os

# Argumente parsen
parser = argparse.ArgumentParser(description="Geo-Workflow für beliebige Regionen")
parser.add_argument("--config", type=str, help="Pfad zur JSON-Konfigurationsdatei")
args_cli = parser.parse_args()

# JSON einlesen
if args_cli.config:
    if not os.path.exists(args_cli.config):
        print(f"❌ Konfigurationsdatei nicht gefunden: {args_cli.config}")
        exit(1)

    with open(args_cli.config, "r") as f:
        config = json.load(f)
else:
    print("❌ Bitte verwende --config <datei.json>")
    exit(1)

# Parameter aus JSON
name = config["name"].lower()
lon = config["lon"]
lat = config["lat"]
radius_m = config["radius"] * 1000
source = config["source"]

# Schritt 1: Buffer
subprocess.run(f"python scripts/create_buffer.py --lon {lon} --lat {lat} --radius {radius_m} --name {name}", shell=True)

# Schritt 2: Poly
subprocess.run(f"python scripts/convert_to_poly.py --name {name}", shell=True)

# Schritt 3: Clip
subprocess.run(f"bash scripts/extract_clip.sh {name} {source}", shell=True)

# Schritt 4: GPKG
subprocess.run(f"bash scripts/convert_to_gpkg.sh {name}", shell=True)

print(f"\n✅ Workflow abgeschlossen für Region: {name}")