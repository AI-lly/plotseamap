import os
import json
import shutil
import pytest
from click.testing import CliRunner
from src.plotseamap.cli import main


def prepare_test_environment(tmp_path):
    # Verzeichnisstruktur anlegen
    base = tmp_path
    data_dir = base / "tests_data"
    processed = base / "processed"
    output = base / "output"
    data_dir.mkdir()
    processed.mkdir()
    output.mkdir()

    # Beispiel-Polygon als GeoJSON
    poly = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[0,0],[0,1],[1,1],[1,0],[0,0]]]}, "properties": {}}
        ]
    }
    polyfile = data_dir / "poly.geojson"
    with open(polyfile, 'w', encoding='utf-8') as f:
        json.dump(poly, f)

    # Dummy OSM-PBF: wir simulieren durch leeres GeoJSON um Fiona nicht abstürzen zu lassen
    dummy_osm = {
        "type": "FeatureCollection",
        "features": []
    }
    osm_pbf = data_dir / "dummy.osm.pbf"
    with open(osm_pbf, 'w', encoding='utf-8') as f:
        json.dump(dummy_osm, f)

    # Konfigurationsdatei
    config = {
        "polyfile": str(polyfile),
        "osm_pbf": str(osm_pbf),
        "extracted_geojson": str(processed / "extracted.geojson"),
        "output_gpkg": str(processed / "data.gpkg"),
        "layer_name": "osm",
        "input_gpkg": str(processed / "data.gpkg"),
        "buffer_distance": 10,
        "output_buffer_geojson": str(processed / "buffer.geojson")
    }
    cfg_file = base / "config.json"
    with open(cfg_file, 'w', encoding='utf-8') as f:
        json.dump(config, f)

    return str(cfg_file), processed


def test_full_pipeline(tmp_path):
    cfg_file, processed = prepare_test_environment(tmp_path)
    runner = CliRunner()

    # extract
    result = runner.invoke(main, ["--config", cfg_file, "extract"])
    assert result.exit_code == 0
    assert os.path.exists(processed / "extracted.geojson")

    # convert
    result = runner.invoke(main, ["--config", cfg_file, "convert"])
    assert result.exit_code == 0
    assert os.path.exists(processed / "data.gpkg")

    # buffer
    result = runner.invoke(main, ["--config", cfg_file, "buffer"])
    assert result.exit_code == 0
    assert os.path.exists(processed / "buffer.geojson")
