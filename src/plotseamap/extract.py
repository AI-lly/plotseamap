import os
import time
import logging
import osmium
import shapely.wkb as wkblib
from shapely.geometry import Point, Polygon, MultiPolygon, mapping
import geopandas as gpd
import fiona
from fiona.crs import CRS

# ───────────────────────────────────────────────────────────────
# Logging konfigurieren
# ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

_wkb = osmium.geom.WKBFactory()
BATCH_DEFAULT    = 20_000  # Standard Batch-Größe
DEFAULT_LAYERS   = ["points", "lines", "multilinestrings", "multipolygons", "other_relations"]

# ───────────────────────────────────────────────────────────────
class Counter(osmium.SimpleHandler):
    def __init__(self, poly, layers):
        super().__init__()
        self.poly    = poly
        self.keys    = set()
        self.layers  = layers
        self.counts  = {layer: 0 for layer in layers}

    def _process_tags(self, tags):
        for t in tags:
            try:
                self.keys.add(t.k)
            except AttributeError:
                k, _ = t
                self.keys.add(k)

    def _categorize(self, geom):
        t = geom.geom_type
        if t == "Point":            layer = "points"
        elif t == "LineString":     layer = "lines"
        elif t == "MultiLineString":layer = "multilinestrings"
        elif t in ("Polygon","MultiPolygon"):
                                     layer = "multipolygons"
        else:                       layer = "other_relations"
        if layer in self.layers:
            self.counts[layer] += 1

    def node(self, n):
        if n.location.valid():
            pt = Point(n.location.lon, n.location.lat)
            if pt.within(self.poly):
                self._process_tags(n.tags)
                self._categorize(pt)

    def way(self, w):
        try:
            wkb  = _wkb.create_linestring(w)
            geom = wkblib.loads(wkb, hex=True)
            if geom.is_ring:
                geom = Polygon(geom)
        except Exception:
            return
        if geom.within(self.poly):
            self._process_tags(w.tags)
            self._categorize(geom)

    def relation(self, r):
        try:
            wkb  = _wkb.create_multipolygon(r)
            geom = wkblib.loads(wkb, hex=True)
        except Exception:
            return
        if isinstance(geom,(Polygon,MultiPolygon)) and geom.within(self.poly):
            self._process_tags(r.tags)
            self._categorize(geom)


# ───────────────────────────────────────────────────────────────
class MultiWriter:
    def __init__(self, out_path, layer, keys, total, batch_size):
        prop_schema = {k: "str" for k in sorted(keys)}
        prop_schema["osm_id"] = "int"
        schema = {"geometry": "Unknown", "properties": prop_schema}

        # Ordner anlegen und loggen
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        log.info(f"Öffne GPKG-Layer '{layer}' -> {out_path}")

        self.sink = fiona.open(
            out_path,
            mode="w",
            driver="GPKG",
            layer=layer,
            crs=CRS.from_epsg(4326),
            schema=schema,
        )
        self.total      = total
        self.written    = 0
        self.batch      = []
        self.batch_size = batch_size
        self.t0         = time.time()
        log.info(f"  → Erwarte {total} Features (Batch-Size={batch_size})")

    def add(self, geom, osm_id, tags):
        props = {k: tags.get(k) for k in self.sink.schema["properties"] if k != "geometry"}
        props["osm_id"] = osm_id
        self.batch.append({"geometry": mapping(geom), "properties": props})
        if len(self.batch) >= self.batch_size:
            self._flush()

    def _flush(self):
        if not self.batch:
            return
        self.sink.writerecords(self.batch)
        self.written += len(self.batch)
        elapsed = time.time() - self.t0
        pct     = 100 * self.written / self.total if self.total else 0
        speed   = self.written / elapsed if elapsed else 0
        log.info(f"    → {self.written:,}/{self.total:,} ({pct:5.1f}%) | {speed:,.0f} feat/s")
        self.batch.clear()

    def close(self):
        self._flush()
        self.sink.close()
        log.info("  → Writer geschlossen")


# ───────────────────────────────────────────────────────────────
class StreamHandler(osmium.SimpleHandler):
    def __init__(self, poly, writers):
        super().__init__()
        self.poly    = poly
        self.writers = writers

    def _add(self, geom, osm_id, tags):
        if not geom.within(self.poly):
            return
        t = geom.geom_type
        if t == "Point":            layer = "points"
        elif t == "LineString":     layer = "lines"
        elif t == "MultiLineString":layer = "multilinestrings"
        elif t in ("Polygon","MultiPolygon"):
                                     layer = "multipolygons"
        else:                       layer = "other_relations"
        if layer in self.writers:
            self.writers[layer].add(geom, osm_id, tags)

    def node(self, n):
        if n.location.valid():
            self._add(Point(n.location.lon, n.location.lat), n.id, dict(n.tags))

    def way(self, w):
        try:
            wkb  = _wkb.create_linestring(w)
            geom = wkblib.loads(wkb, hex=True)
            if geom.is_ring:
                geom = Polygon(geom)
        except Exception:
            return
        self._add(geom, w.id, dict(w.tags))

    def relation(self, r):
        try:
            wkb  = _wkb.create_multipolygon(r)
            geom = wkblib.loads(wkb, hex=True)
        except Exception:
            return
        self._add(geom, r.id, dict(r.tags))


# ───────────────────────────────────────────────────────────────
def extract_stream(cfg):
    """
    Extrahiere OSM-Features in konfigurierbare GPKG-Layern mit Fortschritt.
    Config:
      - extract_layers: Liste von Layer-Namen aus DEFAULT_LAYERS
      - batch_size: Optional int für Flush-Größe
      - lon, lat, radius, bbox_pbf, output_gpkg
    """
    inp     = cfg.get("bbox_pbf")
    out     = cfg.get("output_gpkg")
    layers  = cfg.get("extract_layers", DEFAULT_LAYERS)
    batch   = cfg.get("batch_size", BATCH_DEFAULT)
    lon     = cfg.get("lon")
    lat     = cfg.get("lat")
    radius  = cfg.get("radius")

    # Validierung & Logging
    if not all([inp, out, lon is not None, lat is not None, radius is not None]):
        raise ValueError("Config benötigt 'bbox_pbf','output_gpkg','lon','lat','radius'")
    log.info(f"Starte Extraction:\n  Input PBF:    {inp}\n  Output GPKG:  {out}")
    log.info(f"  Layers:       {layers}\n  Batch-Size:   {batch}")

    # altes GPKG entfernen
    if os.path.exists(out):
        log.info(f"Entferne vorhandenes GPKG: {out}")
        os.remove(out)

    # Kreis-Polygon erstellen
    center = Point(lon, lat)
    circle = (
        gpd.GeoSeries([center], crs="EPSG:4326")
           .to_crs(3857)
           .buffer(radius*1000)
           .to_crs("EPSG:4326")
           .iloc[0]
    )
    log.info(f"Kreis um ({lon}, {lat}) mit Radius {radius} km erzeugt")

    # ─── Pass 1: Tags zählen ───────────────────────────────
    log.info("Pass 1: Zähle Features und sammle Tag-Keys …")
    ctr = Counter(circle, layers)
    ctr.apply_file(inp, locations=True)
    keys, counts = ctr.keys, ctr.counts
    log.info(f"  → Erwartete Features je Layer: {counts}")

    # ─── Pass 2: Features schreiben ───────────────────────
    log.info("Pass 2: Schreibe Features in GPKG mit Fortschritt …")
    writers = {
        layer: MultiWriter(out, layer, keys, counts.get(layer, 0), batch)
        for layer in layers
    }
    hd = StreamHandler(circle, writers)
    hd.apply_file(inp, locations=True)
    for w in writers.values():
        w.close()

    log.info("Extraktion abgeschlossen ✓")
