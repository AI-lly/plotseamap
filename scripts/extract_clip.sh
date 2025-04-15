# scripts/extract_clip.sh
#!/bin/bash
set -e

REGION=$1
SOURCE=$2

POLY_FILE="processed/poly/${REGION}.poly"
PBF_INPUT="data/osm/${SOURCE}"
PBF_OUTPUT="processed/clipped_osm/cut_${REGION}.osm.pbf"

mkdir -p processed/clipped_osm

if [ ! -f "$POLY_FILE" ]; then
  echo "❌ .poly-Datei nicht gefunden: $POLY_FILE"
  exit 1
fi

if [ ! -f "$PBF_INPUT" ]; then
  echo "❌ Eingabedatei nicht gefunden: $PBF_INPUT"
  exit 1
fi

echo "✂️  Schneide ${REGION} aus $PBF_INPUT ..."
osmium extract --polygon "$POLY_FILE" -o "$PBF_OUTPUT" "$PBF_INPUT" --overwrite
echo "✅ Gespeichert unter: $PBF_OUTPUT"