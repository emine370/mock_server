import time, json
from shapely.geometry import Point, Polygon

def load_hss_polygons(path):
    d = json.load(open(path))
    polys = {}
    for z in d["zones"]:
        polys[z["id"]] = Polygon([(p[1], p[0]) for p in z["polygon"]])  # (lon, lat)
    return polys

def is_in_hss(lat, lon, polygons):
    pt = Point(lon, lat)
    for pid, poly in polygons.items():
        if poly.contains(pt):
            return True, pid
    return False, None

def now():
    return time.time()
