import os
import osmium

def merge_pbf(input_files: list[str], output_file: str) -> None:
    """
    Merge multiple OSM .pbf files into a single .pbf.

    :param input_files: Liste mit Pfaden zu den Eingabe-PBF-Dateien
    :param output_file: Pfad zur Zieldatei
    """
    # Sicherstellen, dass das Zielverzeichnis existiert
    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Writer initialisieren (überschreibt, falls existierend)
    writer = osmium.SimpleWriter(output_file, overwrite=True)
    try:
        # Jede Eingabedatei sequentiell einlesen
        for fname in input_files:
            print(f"Merging {fname} into {output_file}...")
            for entity in osmium.FileProcessor(fname):
                writer.add(entity)
    finally:
        writer.close()


if __name__ == '__main__':
    import json
    import sys
    # CLI für schnelles Testen: json-Datei und Ausgabepfad übergeben
    cfg = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
    merge_pbf(cfg['raw_pbf_files'], cfg['merged_pbf'])