import time, math
from .base_generator import now

def hss_approach_generator(
    id="rakip_1",
    start=(38.76480, 30.52390, 120),  # HSS dışından başla
    target=(38.76395, 30.52375, 120),  # HSS bölgesinin merkezi
    speed=2,
    rate_hz=1
):
    """
    HSS bölgesine doğru giden senaryo
    """
    lat, lon, alt = start
    dt = 1.0 / rate_hz
    meters_lat = 111320

    while True:
        meters_lon = meters_lat * math.cos(math.radians(lat))

        dlat = (target[0] - lat) * meters_lat
        dlon = (target[1] - lon) * meters_lon
        dist = math.hypot(dlat, dlon)

        if dist < 1.0:
            # HSS merkezine ulaştı, orada kal
            vx = vy = 0
        else:
            # HSS'ye doğru ilerle
            vx = speed * (dlon / dist)
            vy = speed * (dlat / dist)
            lat += (vy / meters_lat) * dt
            lon += (vx / meters_lon) * dt

        yield {
            "timestamp": now(),
            "id": id,
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "vx": vx,
            "vy": vy,
            "vz": 0,
            "yaw": 0,
        }

        time.sleep(dt)

