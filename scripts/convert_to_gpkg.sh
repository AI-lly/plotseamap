# scripts/convert_to_gpkg.sh
#!/bin/bash
set -e

REGION=$1
INPUT="processed/clipped_osm/cut_${REGION}.osm.pbf"
OUTPUT="processed/geopackage/${REGION}.gpkg"

mkdir -p processed/geopackage

echo "📦 Konvertiere $INPUT → $OUTPUT ..."
ogr2ogr -f GPKG -overwrite "$OUTPUT" "$INPUT"
echo "✅ GeoPackage gespeichert unter: $OUTPUT"
