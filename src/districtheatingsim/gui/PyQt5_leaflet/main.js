// Leaflet Karte initialisieren
const map = L.map('map').setView([51.1657, 10.4515], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: 'OpenStreetMap'
}).addTo(map);

// Polyfill für _flat, falls es veraltet ist
if (typeof L.LineUtil._flat === 'undefined') {
    L.LineUtil._flat = L.LineUtil.isFlat;
}

// Definiere allLayers global und füge es zur Karte hinzu
const allLayers = new L.FeatureGroup();
map.addLayer(allLayers);

// Aktivieren der Bearbeitung
allLayers.eachLayer(layer => {
    if (layer.editing) {
        layer.editing.enable();
    }
});

// Deaktivieren der Bearbeitung
allLayers.eachLayer(layer => {
    if (layer.editing) {
        layer.editing.disable();
    }
});


let clickMarker = null;
let markerModeEnabled = false;

// Funktion zum Ein-/Ausschalten des Marker-Modus
function toggleMarkerMode() {
    markerModeEnabled = !markerModeEnabled;
    document.getElementById('toggleMarkerButton').textContent = markerModeEnabled ? 'Marker setzen: Aus' : 'Marker setzen: Ein';

    if (markerModeEnabled) {
        map.on('click', onMapClick);  // Aktiviert den Klick-Handler
    } else {
        map.off('click', onMapClick); // Deaktiviert den Klick-Handler
        if (clickMarker) {
            map.removeLayer(clickMarker); // Entfernt den Marker, wenn gewünscht
            clickMarker = null;
        }
        document.getElementById('coordinateDisplay').textContent = ''; // Löscht Koordinatenanzeige
    }
}

// Klick-Handler für die Karte
function onMapClick(e) {
    var lat = e.latlng.lat.toFixed(6);
    var lng = e.latlng.lng.toFixed(6);

    document.getElementById('coordinateDisplay').textContent = "Latitude: " + lat + ", Longitude: " + lng;

    if (!clickMarker) {
        clickMarker = L.marker([lat, lng]).addTo(map);
    } else {
        clickMarker.setLatLng([lat, lng]);
    }

    clickMarker.bindPopup("Latitude: " + lat + "<br>Longitude: " + lng).openPopup();
}

function setMapCenter(lat, lng, zoom) {
    map.setView([lat, lng], zoom);
}

window.setMapCenter = setMapCenter;

// Event für den Button, um den Marker-Modus umzuschalten
document.getElementById('toggleMarkerButton').addEventListener('click', toggleMarkerMode);

// Animationsschleife
function animate() {
    requestAnimationFrame(animate);
}
animate();

// Leaflet.draw-Steuerung
var drawControl = new L.Control.Draw({
    edit: {
        featureGroup: allLayers,
        remove: true,
        edit: true  // Aktivieren oder Deaktivieren von Editieren
    },
    draw: {
        polygon: true,
        polyline: true,
        rectangle: false,
        circle: false,
        marker: true,
        circlemarker: false
    }
});

map.addControl(drawControl);

// Event-Listener für gezeichnete Shapes
map.on(L.Draw.Event.CREATED, function (e) {
    var layer = e.layer;
    allLayers.addLayer(layer);
    addLayerToList(layer);
    console.log("Neuer Layer hinzugefügt:", layer);
});

// Event für das `editstop`-Ereignis hinzufügen, um das automatische Verbinden zu aktivieren
map.on('draw:editstop', () => {
    snapLineEndpoints(allLayers);
});