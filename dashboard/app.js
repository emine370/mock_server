const socket = io("http://localhost:8000");

const blueIcon = L.icon({
  iconUrl: "./icons/marker-icon-blue.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34]
});

const redIcon = L.icon({
  iconUrl: "./icons/marker-icon-red.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34]
});

const yellowIcon = L.icon({
  iconUrl: "./icons/marker-icon-yellow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34]
});

const map = L.map("map").setView([38.7640, 30.5235], 18);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "Map data © OpenStreetMap contributors",
}).addTo(map);

// ✅ Çoklu drone marker saklama alanı
const droneMarkers = {};
const lastPositions = {}; // Son pozisyonları sakla
const lastUpdateTime = {}; // Son güncelleme zamanlarını sakla

socket.on("telemetry", (data) => {
  const { id, lat, lon, status, timestamp } = data;

  // Eğer bu drone için marker yoksa oluştur:
  if (!droneMarkers[id]) {
    droneMarkers[id] = L.marker([lat, lon], {
      icon: blueIcon
    }).addTo(map)
      .bindTooltip(id, { permanent: true, direction: "right" })
      .openTooltip();
    lastPositions[id] = { lat, lon, timestamp: timestamp || Date.now() };
    lastUpdateTime[id] = Date.now();
    return;
  }

  // Eski mesajları filtrele (timestamp kontrolü)
  const currentTime = timestamp || Date.now();
  if (lastPositions[id] && lastPositions[id].timestamp > currentTime) {
    return; // Eski mesaj, görmezden gel
  }

  // Çok sık güncellemeleri throttle et (minimum 500ms aralık - 1 Hz güncelleme için güvenli)
  const timeSinceLastUpdate = Date.now() - (lastUpdateTime[id] || 0);
  if (timeSinceLastUpdate < 500) {
    return; // Çok sık güncelleme, atla
  }

  // Pozisyon değişikliğini kontrol et
  const currentPos = droneMarkers[id].getLatLng();
  const distance = Math.sqrt(
    Math.pow(lat - currentPos.lat, 2) + Math.pow(lon - currentPos.lng, 2)
  );

  // Sadece mantıklı mesafe içindeki güncellemeleri kabul et (çok büyük sıçramaları filtrele)
  // 0.0001 derece ≈ 11 metre - normal drone hareketi için makul bir limit
  if (distance > 0.0001) {
    console.warn(`[${id}] Anormal pozisyon sıçraması tespit edildi (${distance.toFixed(6)}), atlanıyor`);
    return;
  }

  // Marker'ı güncelle
  droneMarkers[id].setLatLng([lat, lon]);
  lastPositions[id] = { lat, lon, timestamp: currentTime };
  lastUpdateTime[id] = Date.now();

  // Renk güncelle
  if (status && (status.startsWith("AUTO_AVOID") || status.startsWith("HSS_ALERT"))) {
    droneMarkers[id].setIcon(redIcon);  // HSS içinde veya kaçınma → kırmızı
  }
  else if (status === "NEAR_COLLISION") {
    droneMarkers[id].setIcon(yellowIcon); // Çarpışma uyarısı → sarı
  }
  else {
    droneMarkers[id].setIcon(blueIcon);   // Normal uçuş → mavi
  }

});

// ✅ HSS polygon yükleme
fetch("./hss_zones.json")
  .then(resp => resp.json())
  .then(data => {
    data.zones.forEach(zone => {
      const polyCoords = zone.polygon.map(([lat, lon]) => [lat, lon]);
      L.polygon(polyCoords, {
        color: "red",
        weight: 2,
        fillColor: "red",
        fillOpacity: 0.25
      }).addTo(map);
    });
  });
