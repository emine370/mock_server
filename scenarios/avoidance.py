import time
from .base_generator import now, is_in_hss

def avoidance_generator(base_gen, polygons, rate_hz=5):
    """
    base_gen: başka bir senaryodan gelen telemetri generator'ı
    polygons: HSS alanları (sunucudan alınacak)
    """
    dt = 1.0 / rate_hz

    for msg in base_gen:   # gelen her telemetri mesajını kontrol et
        lat = msg["lat"]
        lon = msg["lon"]

        inside, zone_id = is_in_hss(lat, lon, polygons)

        if inside:
            # ✅ Kaçınma davranışı
            msg["yaw"] = (msg.get("yaw", 0) + 90) % 360
            msg["lat"] += 0.00005    # ~5 metre yukarı kay
            msg["lon"] += 0.00005    # ~5 metre sağa kay
            msg["status"] = f"AUTO_AVOID:{zone_id}"
        else:
            msg["status"] = "NORMAL"

        yield msg
        time.sleep(dt)
