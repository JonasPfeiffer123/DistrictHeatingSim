// Leaflet Karte initialisieren
const map = L.map('map').setView([51.1657, 10.4515], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: 'OpenStreetMap'
}).addTo(map);

// Definiere allLayers global und füge es zur Karte hinzu
const allLayers = new L.FeatureGroup();
map.addLayer(allLayers);

// Animationsschleife
function animate() {
    requestAnimationFrame(animate);
}
animate();