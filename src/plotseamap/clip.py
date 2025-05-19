import osmium
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BBoxHandler(osmium.SimpleHandler):
    def __init__(self, bbox, writer):
        super().__init__()
        self.minx, self.miny, self.maxx, self.maxy = bbox
        self.writer = writer

    def _in_bbox(self, lon, lat):
        return self.minx <= lon <= self.maxx and self.miny <= lat <= self.maxy

    def node(self, n):
        if n.location.valid() and self._in_bbox(n.location.lon, n.location.lat):
            self.writer.add_node(n)

    def way(self, w):
        # einfacher Test: irgendeinen Knoten im bbox?
        if any(self._in_bbox(n.lon, n.lat) for n in w.nodes):
            self.writer.add_way(w)

    def relation(self, r):
        # fallback: schreib Relations pauschal mit
        self.writer.add_relation(r)

# src/plotseamap/clip_bbox.py

def clip_bbox(input_pbf: str, output_pbf: str, bbox: tuple[float, float, float, float]):
    """
    Clipt mit osmium C++-Geschwindigkeit eine bounding box aus dem großen PBF
    """
    # Hier einfügen:
    out_dir = os.path.dirname(output_pbf)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    logger.info(f"Clipping {input_pbf} → {output_pbf} mit BBox {bbox}")
    writer = osmium.SimpleWriter(output_pbf, overwrite=True)
    handler = BBoxHandler(bbox, writer)
    handler.apply_file(input_pbf, locations=True)
    writer.close()
    logger.info("BBox‑Clip abgeschlossen")