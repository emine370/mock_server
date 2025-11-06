import time, math
from .base_generator import now

def approach_generator(
    id="rakip_1",
    start=(38.7655, 30.5230, 120),
    target=(38.7640, 30.5235, 120),   # Bizim İHA konumu
    speed=6,
    rate_hz=5
):
    lat, lon, alt = start
    dt = 1.0 / rate_hz
    meters_lat = 111320

    while True:
        meters_lon = meters_lat * math.cos(math.radians(lat))

        dlat = (target[0] - lat) * meters_lat
        dlon = (target[1] - lon) * meters_lon
        dist = math.hypot(dlat, dlon)

        if dist < 1.0:
            vx = vy = 0  # hedefe ulaştı → hover
        else:
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
