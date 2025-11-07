import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("Bağlantı kuruldu ✅ Çoklu İHA başlatılıyor...")

    sio.emit("start_multiple", {
    "drones": [
        {"id": "rakip_1", "scenario": "hss_approach",  "lat": 38.76480, "lon": 30.52390},  # HSS'ye doğru gidecek
        {"id": "rakip_2", "scenario": "circular",  "lat": 38.76320, "lon": 30.52460}
    ]
})

@sio.event
def telemetry(data):
    print(data)

sio.connect("http://localhost:8000")
sio.wait()
