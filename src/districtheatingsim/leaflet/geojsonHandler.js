// Filename: geojsonHandler.js
// Author: Dipl.-Ing. (FH) Jonas Pfeiffer
// Date: 2025-01-26
// Description: JavaScript-File for the  import and export of GeoJSON data

// Definieren von EPSG:25833 (ETRS89 / UTM Zone 33N)
if (typeof proj4 !== 'undefined') {
    proj4.defs("EPSG:25833", "+proj=utm +zone=33 +ellps=GRS80 +units=m +no_defs");
} else {
    console.error("proj4 is not defined");
}

// Polyfill für _flat, falls es veraltet ist
if (typeof L.LineUtil._flat === 'undefined') {
    L.LineUtil._flat = L.LineUtil.isFlat;
}

function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

// Funktion zum Importieren von GeoJSON und Hinzufügen als eine einzelne Layer-Gruppe
function importGeoJSON(geojsonData, fileName) {
    const crs = geojsonData.crs ? geojsonData.crs.properties.name : 'EPSG:4326';

    // Transformiere Koordinaten, falls das CRS nicht WGS84 ist
    if (crs === "urn:ogc:def:crs:EPSG::25833") {
        geojsonData.features.forEach(feature => transformCoordinates(feature));
    }

    // Generiere eine zufällige Farbe
    const randomColor = getRandomColor();

    // Erstelle eine einzelne Layer-Gruppe aus allen Features im GeoJSON
    const layerGroup = L.geoJSON(geojsonData, {
        style: (feature) => ({
            color: randomColor,
            fillOpacity: feature.properties.opacity ? feature.properties.opacity * 0.5 : 0.5,
            opacity: feature.properties.opacity || 1.0
        })
    });

    // Setze Gruppenoptionen und Namen
    layerGroup.options.name = fileName || "Imported Layer";
    layerGroup.options.color = randomColor;
    layerGroup.options.opacity = geojsonData.features[0].properties.opacity || 1.0;

    addLayerToList(layerGroup); // Zur Layer-Liste hinzufügen, aber nur als ein Eintrag
    map.addLayer(layerGroup);

    // Layer in den Kartenausschnitt anpassen
    if (layerGroup.getBounds().isValid()) {
        map.fitBounds(layerGroup.getBounds());
    }

    console.log("Layer-Gruppe importiert:", layerGroup.options.name);
    console.log("Anzahl der Layer in allLayers nach dem Hinzufügen:", allLayers.getLayers().length);
}

// Funktion zur Transformation von Koordinaten
function transformCoordinates(feature) {
    const transformCoord = coord => proj4("EPSG:25833", "EPSG:4326", coord).concat(coord[2] || 0);
    const transformRing = ring => ring.map(transformCoord);

    if (feature.geometry.type === "Polygon") {
        feature.geometry.coordinates = feature.geometry.coordinates.map(transformRing);
    } else if (feature.geometry.type === "MultiPolygon") {
        feature.geometry.coordinates = feature.geometry.coordinates.map(polygon => polygon.map(transformRing));
    } else if (feature.geometry.type === "LineString") {
        feature.geometry.coordinates = transformRing(feature.geometry.coordinates);
    } else if (feature.geometry.type === "Point") {
        feature.geometry.coordinates = transformCoord(feature.geometry.coordinates);
    }
}

function focusMapOnFeature(feature) {
    if (feature.geometry && feature.geometry.coordinates) {
        const firstCoord = feature.geometry.coordinates[0][0][0]; // Annahme: Feature hat gültige Koordinaten
        const latLng = L.latLng(firstCoord[1], firstCoord[0]);
        map.setView(latLng, 18);  // Zoom auf die Position des 3D-Features, 18 = hoher Zoom-Level
    }
}

// Funktion zum Hinzufügen von 2D-Geometrie zur Leaflet-Karte und zum Erstellen des Layers
function add2DLayer(feature) {
    const color = feature.properties.color || "#3388ff";
    const opacity = feature.properties.opacity || 1.0;
    const layerOptions = {
        color: color,
        fillOpacity: opacity * 0.5,
        opacity: opacity
    };

    // Erstelle und füge den Layer hinzu
    const layer = L.geoJSON(feature, {
        style: layerOptions
    }).addTo(allLayers);

    // Speichere Layer-Informationen in den Optionen für spätere Bearbeitungen
    layer.options.name = feature.properties.name || "Layer";
    layer.options.color = color;
    layer.options.opacity = opacity;

    return layer;
}

window.importGeoJSON = importGeoJSON; // Funktion global verfügbar machen
