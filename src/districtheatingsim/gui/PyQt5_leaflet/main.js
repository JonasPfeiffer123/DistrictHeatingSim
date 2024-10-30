// Filename: main.js
// Author: Dipl.-Ing. (FH) Jonas Pfeiffer
// Date: 2024-10-20
// Description: JavaScript-File for the main functionality of the Leaflet map

// Initialize Leaflet map
const map = L.map('map').setView([51.1657, 10.4515], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: 'OpenStreetMap', maxZoom: 22
}).addTo(map);

// Polyfill for _flat if deprecated
if (typeof L.LineUtil._flat === 'undefined') {
    L.LineUtil._flat = L.LineUtil.isFlat;
}

// Define allLayers globally and add to map
const allLayers = new L.FeatureGroup();
map.addLayer(allLayers);

// Enable Leaflet.pm controls with snapping
map.pm.addControls({
    position: 'topleft',
    drawMarker: true,
    drawPolyline: true,
    editMode: true,
    dragMode: true,
    cutPolygon: false,
    removalMode: true
});

// Set global snapping options for Leaflet.pm
map.pm.setGlobalOptions({
    snappable: true,
    snapDistance: 5, // Snap threshold in pixels
    allowSelfIntersection: false
});

// Toggle marker mode
let clickMarker = null;
let markerModeEnabled = false;
function toggleMarkerMode() {
    markerModeEnabled = !markerModeEnabled;
    document.getElementById('toggleMarkerButton').textContent = markerModeEnabled ? 'Marker setzen: Aus' : 'Marker setzen: Ein';

    if (markerModeEnabled) {
        map.on('click', onMapClick); // Enable click handler
    } else {
        map.off('click', onMapClick); // Disable click handler
        if (clickMarker) {
            map.removeLayer(clickMarker); // Remove marker if needed
            clickMarker = null;
        }
        document.getElementById('coordinateDisplay').textContent = ''; // Clear coordinates display
    }
}

// Click handler for the map
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

// Event for the button to toggle marker mode
document.getElementById('toggleMarkerButton').addEventListener('click', toggleMarkerMode);

// Enable snapping for each layer on creation
map.on('pm:create', (e) => {
    const layer = e.layer;
    allLayers.addLayer(layer);

    layer.pm.enable({
        snappable: true,
        snapDistance: 5 // Set snapping distance for this layer
    });

    // Real-time snapping with visual feedback
    layer.on('pm:snap', (event) => {
        console.log('Snapped to:', event.marker.getLatLng());
        // Optional: Add visual indication of snap points, e.g., change marker color or style
        if (event.marker) {
            event.marker.setStyle({ color: 'red' });
        }
    });

    layer.on('pm:unsnap', (event) => {
        console.log('Unsnap:', event.marker.getLatLng());
        // Reset visual indication when unsnapped
        if (event.marker) {
            event.marker.setStyle({ color: 'green' });
        }
    });
});
