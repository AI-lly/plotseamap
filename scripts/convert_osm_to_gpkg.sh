#!/bin/bash

ogr2ogr -f GPKG processed/geopackage/fehmarnbelt.gpkg data/osm/cut_fehmarnbelt.osm.pbf

echo "✅ Konvertierung abgeschlossen: processed/geopackage/fehmarnbelt.gpkg"