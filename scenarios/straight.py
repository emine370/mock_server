import math
import time

def straight_generator(id="rakip_1", start=(38.7640, 30.5235, 120), heading_deg=90, speed=6, rate_hz=5):
    lat, lon, alt = start
    dt = 1.0 / rate_hz
    curr_yaw = heading_deg

    while True:
        # Yaw'ı her döngüde server'ın gönderdiği değerden almayı desteklemek için:
        heading = math.radians(curr_yaw)

        d_lat = (speed * math.cos(heading)) * dt / 111_320
        d_lon = (speed * math.sin(heading)) * dt / (111_320 * math.cos(math.radians(lat)))

        lat += d_lat
        lon += d_lon

        msg = {
            "timestamp": time.time(),
            "id": id,
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "vx": speed * math.cos(heading),
            "vy": speed * math.sin(heading),
            "vz": 0,
            "yaw": curr_yaw
        }

        # Server kaçınma yaptıysa yaw değişmiş olabilir
        if "yaw" in msg:
            curr_yaw = msg["yaw"]

        yield msg
        time.sleep(dt)
