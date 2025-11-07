import eventlet
eventlet.monkey_patch()   # <-- EN ÜSTE MUTLAKA

from math import radians, sin, cos, sqrt, atan2
from flask import Flask
from flask_socketio import SocketIO, emit

from scenarios.straight import straight_generator
from scenarios.circular import circular_generator
from scenarios.approach import approach_generator
from scenarios.avoidance import avoidance_generator
from scenarios.hss_approach import hss_approach_generator

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

# Çalışan generator'ları takip et (drone_id -> stop_flag)
active_generators = {}

# HSS içindeki drone'ları takip et (drone_id -> entry_time)
hss_entry_times = {}

# HSS içindeyken çıkış için son pozisyonları sakla (drone_id -> (lat, lon))
hss_escape_positions = {}


# ----------------------------------------------------------
# Telemetri Yayını
# ----------------------------------------------------------
def broadcast(gen, drone_id, stop_flag):
    for msg in gen:
        # Eğer bu generator durdurulduysa, döngüyü kır
        if stop_flag.get("stop", False):
            print(f"[SERVER] Generator durduruldu: {drone_id}")
            break
            
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

        # HSS kaçınma - anında çıkış (bekleme yok)
        if inside:
            # HSS içine girdiği anda hemen çıkışa geç
            hss_center_lat = 38.76395
            hss_center_lon = 30.52375
            
            # İlk girişte pozisyonu kaydet
            if drone_id not in hss_escape_positions:
                hss_escape_positions[drone_id] = (msg["lat"], msg["lon"])
                print(f"[SERVER] {drone_id} HSS içine girdi, çıkış moduna geçiliyor")
            
            # Çıkış pozisyonunu al (generator'ın pozisyonunu kullanma, sadece çıkış hareketi)
            escape_lat, escape_lon = hss_escape_positions[drone_id]
            
            # HSS merkezinden dışarı doğru yön hesapla
            dlat = escape_lat - hss_center_lat
            dlon = escape_lon - hss_center_lon
            dist = sqrt(dlat**2 + dlon**2)
            
            if dist > 0:
                # HSS merkezinden dışarı doğru (ters yönde) hareket - çok hızlı çıkış
                escape_speed = 10.0  # m/s (çok hızlı çıkış)
                dt = 1.0  # 1 saniye (rate_hz=1)
                meters_lat = 111320
                meters_lon = meters_lat * cos(radians(escape_lat))
                
                # Normalize edilmiş yön vektörü (dışarı doğru)
                norm = sqrt((dlat * meters_lat)**2 + (dlon * meters_lon)**2)
                if norm > 0:
                    # Çıkış pozisyonunu güncelle (sürekli dışarı doğru)
                    new_lat = escape_lat + (escape_speed * dlat * meters_lat / norm) * dt / meters_lat
                    new_lon = escape_lon + (escape_speed * dlon * meters_lon / norm) * dt / meters_lon
                    
                    # Generator'ın pozisyonunu tamamen override et
                    msg["lat"] = new_lat
                    msg["lon"] = new_lon
                    
                    # Çıkış pozisyonunu güncelle (bir sonraki iterasyon için)
                    hss_escape_positions[drone_id] = (new_lat, new_lon)
                    
                    # Hız vektörlerini de güncelle (çıkış yönünde)
                    msg["vx"] = escape_speed * (dlon * meters_lon / norm)
                    msg["vy"] = escape_speed * (dlat * meters_lat / norm)
            
            # Kırmızı durumda göster ve çıkış modunda
            msg["status"] = f"AUTO_AVOID:{zone_id}"  # Kaçınma modu (kırmızı)
        else:
            # HSS dışında - çıkış modunu temizle
            if drone_id in hss_escape_positions:
                print(f"[SERVER] {drone_id} HSS'den çıktı")
                del hss_escape_positions[drone_id]
            if drone_id in hss_entry_times:
                del hss_entry_times[drone_id]
            msg["status"] = "NORMAL"

        msg["hss_violation"] = inside
        socketio.emit("telemetry", msg)
    
    # Generator bittiğinde temizle
    if drone_id in active_generators:
        del active_generators[drone_id]
        print(f"[SERVER] Generator temizlendi: {drone_id}")


# ----------------------------------------------------------
# Çoklu İHA Başlatma
# ----------------------------------------------------------
@socketio.on("start_multiple")
def start_multiple(data):
    global active_positions

    drones = data.get("drones", [])
    print(f"[SERVER] starting MULTI SCENARIO for {len(drones)} drones")

    for d in drones:
        uav_id = d.get("id", "rakip_1")
        scenario = d.get("scenario", "straight")

        # ✅ Eğer bu ID için zaten çalışan bir generator varsa, önce durdur
        if uav_id in active_generators:
            print(f"[SERVER] Durduruluyor: {uav_id} (yeni başlatma için)")
            active_generators[uav_id]["stop"] = True
            # Kısa bir bekleme (generator'ın durması için)
            eventlet.sleep(0.1)
        
        # HSS entry time ve escape pozisyonlarını temizle (yeni başlatma için)
        if uav_id in hss_entry_times:
            del hss_entry_times[uav_id]
        if uav_id in hss_escape_positions:
            del hss_escape_positions[uav_id]

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

        elif scenario == "hss_approach":
            gen = hss_approach_generator(id=uav_id, start=(lat, lon, 120))

        else:
            gen = straight_generator(id=uav_id, start=(lat, lon, 120))

        # ✅ Yeni stop flag oluştur
        stop_flag = {"stop": False}
        active_generators[uav_id] = stop_flag

        # ✅ Background task başlat
        socketio.start_background_task(broadcast, gen, uav_id, stop_flag)

    emit("info", {"status": "multi start OK"})


# ----------------------------------------------------------
# Sunucuyu çalıştır
# ----------------------------------------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000)
