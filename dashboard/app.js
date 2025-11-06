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

socket.on("telemetry", (data) => {
  const { id, lat, lon, status } = data;

  // Eğer bu drone için marker yoksa oluştur:
  if (!droneMarkers[id]) {
    droneMarkers[id] = L.marker([lat, lon], {
      icon: blueIcon
    }).addTo(map)
      .bindTooltip(id, { permanent: true, direction: "right" })
      .openTooltip();
  }

  // Marker'ı hareket ettir
  droneMarkers[id].setLatLng([lat, lon]);

  // Renk güncelle
  if (status && status.startsWith("AUTO_AVOID")) {
  droneMarkers[id].setIcon(redIcon);  // HSS kaçınma → kırmızı
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
