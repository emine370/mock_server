import eventlet
eventlet.monkey_patch()   # <-- EN ÜSTE MUTLAKA

from math import radians, sin, cos, sqrt, atan2
from flask import Flask
from flask_socketio import SocketIO, emit

from scenarios.straight import straight_generator
from scenarios.circular import circular_generator
from scenarios.approach import approach_generator
from scenarios.avoidance import avoidance_generator

from scenarios.base_generator import load_hss_polygons, is_in_hss


# ----------------------------------------------------------
# Haversine Mesafe Hesabı (metre cinsinden)
# ----------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Dünya yarıçapı (metre)
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


# ----------------------------------------------------------
# Sunucu Kurulumu
# ----------------------------------------------------------
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

HSS = load_hss_polygons("config/hss_zones.json")

# Tüm İHA pozisyonlarını saklayan sözlük
active_positions = {}


# ----------------------------------------------------------
# Telemetri Yayını
# ----------------------------------------------------------
def broadcast(gen):
    for msg in gen:
        inside, zone_id = is_in_hss(msg["lat"], msg["lon"], HSS)

        # Pozisyon kaydı
        active_positions[msg["id"]] = (msg["lat"], msg["lon"])

        # Çarpışma kontrolü
        msg["collision"] = False
        for other_id, (olat, olon) in active_positions.items():
            if other_id != msg["id"]:
                d = haversine(msg["lat"], msg["lon"], olat, olon)
                if d < 30:  # 30m yaklaşım
                    msg["collision"] = True
                    msg["status"] = "NEAR_COLLISION"

        # HSS kaçınma
        if inside:
            msg["status"] = f"HSS_ALERT:{zone_id}"
        else:
            msg["status"] = "NORMAL"   # setdefault yerine direkt set

        msg["hss_violation"] = inside
        socketio.emit("telemetry", msg)


# ----------------------------------------------------------
# Çoklu İHA Başlatma
# ----------------------------------------------------------
@socketio.on("start_multiple")
def start_multiple(data):
    global active_positions
    active_positions = {}   # ✅ önceki uçuşlardan kalan pozisyonları sıfırla

    drones = data.get("drones", [])
    print(f"[SERVER] starting MULTI SCENARIO for {len(drones)} drones")

    for d in drones:
        uav_id = d.get("id", "rakip_1")
        scenario = d.get("scenario", "straight")

        # ✅ Başlangıç koordinatlarını al
        lat = d.get("lat", 38.7640)
        lon = d.get("lon", 30.5235)

        # ✅ Senaryo seç + pozisyonu yerleştir
        if scenario == "straight":
            gen = straight_generator(id=uav_id, start=(lat, lon, 120))

        elif scenario == "circular":
            gen = circular_generator(
                id=uav_id,
                center=(lat, lon, 120),
                radius_m=30          # ✅ doğru parametre adı
            )

        elif scenario == "approach":
            gen = approach_generator(id=uav_id, start=(lat, lon, 120))

        elif scenario == "avoidance":
            gen = avoidance_generator(id=uav_id, start=(lat, lon, 120))

        else:
            gen = straight_generator(id=uav_id, start=(lat, lon, 120))

        socketio.start_background_task(broadcast, gen)

    emit("info", {"status": "multi start OK"})


# ----------------------------------------------------------
# Sunucuyu çalıştır
# ----------------------------------------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000)
