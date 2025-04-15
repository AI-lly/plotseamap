#!/bin/bash
set -e

FILE1=$1
FILE2=$2
OUT=$3

RAW="data/osm/tmp_merge_raw.pbf"

echo "🔗 Merging $FILE1 + $FILE2 ..."
osmium merge data/osm/$FILE1 data/osm/$FILE2 -o $RAW --overwrite

echo "↕️ Sorting and cleaning file ..."
osmium cat $RAW -o data/osm/$OUT --overwrite --output-sort-type=type_then_id

echo "✅ Cleaned & merged OSM file ready: data/osm/$OUT"
rm $RAW

#chmod +x scripts/merge_and_sort_osm.sh
#bash scripts/merge_and_sort_osm.sh denmark-latest.osm.pbf schleswig-holstein-latest.osm.pbf denmark_sh.pbf