#!/bin/bash

# Unterordner im aktuellen Verzeichnis erstellen
mkdir -p data/osm
mkdir -p data/ais
mkdir -p processed/geopackage
mkdir -p processed/geojson
mkdir -p processed/shapefiles
mkdir -p scripts
mkdir -p notebooks
mkdir -p output/plots

# Leere README falls noch nicht vorhanden
touch README.md

# Übersicht anzeigen
echo "✅ Projektstruktur wurde erstellt:"
tree -d -L 2 .

# 1. Ausführbar machen
#chmod +x init_subfolders.sh

# 2. Ausführen (im fehmarnbelt_project-Ordner):
#./init_subfolders.sh