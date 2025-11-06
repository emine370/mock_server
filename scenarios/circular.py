import math
import time

def circular_generator(id="rakip_1", center=(38.7640, 30.5235, 120), radius_m=30, angular_speed_deg_s=20, rate_hz=5):
    lat0, lon0, alt = center
    dt = 1.0 / rate_hz
    angle = 0

    # Metre → derece dönüşümü
    deg_lat_per_m = 1 / 111_320
    deg_lon_per_m = 1 / (111_320 * math.cos(math.radians(lat0)))

    while True:
        angle_rad = math.radians(angle)

        lat = lat0 + radius_m * deg_lat_per_m * math.cos(angle_rad)
        lon = lon0 + radius_m * deg_lon_per_m * math.sin(angle_rad)

        yield {
            "timestamp": time.time(),
            "id": id,
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "yaw": (angle + 90) % 360
        }

        angle = (angle + angular_speed_deg_s * dt) % 360
        time.sleep(dt)
