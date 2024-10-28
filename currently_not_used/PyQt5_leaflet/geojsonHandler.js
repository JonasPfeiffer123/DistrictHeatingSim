// Definieren von EPSG:25833 (ETRS89 / UTM Zone 33N)
if (typeof proj4 !== 'undefined') {
    proj4.defs("EPSG:25833", "+proj=utm +zone=33 +ellps=GRS80 +units=m +no_defs");
} else {
    console.error("proj4 is not defined");
}

// Funktion zum Importieren von GeoJSON und Hinzufügen als eine einzelne Layer-Gruppe
function importGeoJSON(geojsonData, fileName) {
    const crs = geojsonData.crs ? geojsonData.crs.properties.name : 'EPSG:4326';
    // Transformiere Koordinaten, falls das CRS nicht WGS84 ist
    if (crs === "urn:ogc:def:crs:EPSG::25833") {
        geojsonData.features.forEach(feature => transformCoordinates(feature));
    }

    // Erstelle eine einzige Layer-Gruppe aus allen Features im GeoJSON
    const layerGroup = L.geoJSON(geojsonData, {
        style: (feature) => ({
            color: feature.properties.color || "#3388ff",
            fillOpacity: feature.properties.opacity ? feature.properties.opacity * 0.5 : 0.5,
            opacity: feature.properties.opacity || 1.0
        })
    }).addTo(allLayers);

    // Setze den Namen und Farbe der Layer-Gruppe
    layerGroup.options.name = fileName || "Imported Layer";
    layerGroup.options.color = geojsonData.features[0].properties.color || "#3388ff";
    layerGroup.options.opacity = geojsonData.features[0].properties.opacity || 1.0;

    // Füge die gesamte Layer-Gruppe zur Layer-Liste hinzu
    addLayerToList(layerGroup);

    // Passe den Kartenausschnitt an, um alle Features anzuzeigen
    if (layerGroup.getBounds().isValid()) {
        map.fitBounds(layerGroup.getBounds());
    }
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

// Exportiert alle GeoJSON-Daten an Python oder speichert sie lokal
function exportGeoJSON() {
    const data = allLayers.toGeoJSON();
    console.log("All layers as GeoJSON: " + JSON.stringify(data));
    if (window.pywebchannel) {
        window.pywebchannel.sendGeoJSONToPython(JSON.stringify(data));
    }
}

window.importGeoJSON = importGeoJSON; // Funktion global verfügbar machen
