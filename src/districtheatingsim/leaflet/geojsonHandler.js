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
function importGeoJSON(geojsonData, fileName, editable) {
    // editable parameter: true = Layer kann bearbeitet werden, false = geschützt
    if (typeof editable === 'undefined') {
        editable = true; // Default: editierbar
    }
    
    const crs = geojsonData.crs ? geojsonData.crs.properties.name : 'EPSG:4326';

    // Transformiere Koordinaten, falls das CRS nicht WGS84 ist
    if (crs === "urn:ogc:def:crs:EPSG::25833") {
        console.log("Transforming coordinates from EPSG:25833 to WGS84 for", geojsonData.features.length, "features");
        geojsonData.features.forEach(feature => {
            if (feature.geometry && feature.geometry.coordinates) {
                const beforeCoord = JSON.stringify(feature.geometry.coordinates[0]);
                transformCoordinates(feature);
                const afterCoord = JSON.stringify(feature.geometry.coordinates[0]);
                console.log("Transformed:", beforeCoord, "->", afterCoord);
            }
        });
    } else {
        console.log("CRS is", crs, "- no transformation needed");
    }

    // Generiere eine zufällige Farbe
    const randomColor = getRandomColor();

    // Erstelle einen FeatureGroup (nicht nur geoJSON) für bessere Verwaltung
    const layerGroup = L.featureGroup();
    
    // Füge alle Features als separate Layer hinzu
    const geoJsonLayer = L.geoJSON(geojsonData, {
        style: (feature) => ({
            color: randomColor,
            fillOpacity: feature.properties.opacity ? feature.properties.opacity * 0.5 : 0.5,
            opacity: feature.properties.opacity || 1.0
        }),
        onEachFeature: (feature, layer) => {
            // Wenn Layer nicht editierbar sein soll
            if (!editable) {
                // Deaktiviere Geoman editing für diesen Layer
                if (layer.pm) {
                    layer.pm.disable();
                }
                
                // Markiere als nicht editierbar
                layer.options.editable = false;
                
                // Verhindere Drag & Drop
                if (layer.dragging) {
                    layer.dragging.disable();
                }
            } else {
                layer.options.editable = true;
            }
            
            layerGroup.addLayer(layer);
        }
    });

    // Setze Gruppenoptionen und Namen
    layerGroup.options = {
        name: fileName || "Imported Layer",
        color: randomColor,
        opacity: (geojsonData.features.length > 0 && geojsonData.features[0].properties) 
            ? (geojsonData.features[0].properties.opacity || 1.0) 
            : 1.0,
        visible: true,
        locked: !editable,  // Gesperrte Layer sind nicht editierbar
        editable: editable  // Speichere editierbar-Status
    };

    addLayerToList(layerGroup); // Zur Layer-Liste hinzufügen
    allLayers.addLayer(layerGroup);
    map.addLayer(layerGroup);

    // Layer in den Kartenausschnitt anpassen
    if (layerGroup.getBounds && layerGroup.getBounds().isValid()) {
        map.fitBounds(layerGroup.getBounds());
    }

    console.log("Layer-Gruppe importiert:", layerGroup.options.name, 
                "Features:", layerGroup.getLayers().length,
                "Editable:", editable);
}

// Funktion zur Transformation von Koordinaten von EPSG:25833 zu WGS84
function transformCoordinates(feature) {
    if (typeof proj4 === 'undefined') {
        console.error("proj4 is not defined - cannot transform coordinates");
        return;
    }
    
    const transformCoord = coord => {
        // coord ist [x, y] oder [x, y, z] in UTM (EPSG:25833)
        // proj4 transformiert [x, y] zu [lon, lat] in WGS84
        const transformed = proj4("EPSG:25833", "EPSG:4326", [coord[0], coord[1]]);
        // Behalte Z-Koordinate wenn vorhanden
        return coord.length > 2 ? [transformed[0], transformed[1], coord[2]] : transformed;
    };
    
    const transformRing = ring => ring.map(transformCoord);

    if (feature.geometry.type === "Polygon") {
        feature.geometry.coordinates = feature.geometry.coordinates.map(transformRing);
    } else if (feature.geometry.type === "MultiPolygon") {
        feature.geometry.coordinates = feature.geometry.coordinates.map(polygon => polygon.map(transformRing));
    } else if (feature.geometry.type === "LineString") {
        feature.geometry.coordinates = transformRing(feature.geometry.coordinates);
    } else if (feature.geometry.type === "MultiLineString") {
        feature.geometry.coordinates = feature.geometry.coordinates.map(transformRing);
    } else if (feature.geometry.type === "Point") {
        feature.geometry.coordinates = transformCoord(feature.geometry.coordinates);
    } else if (feature.geometry.type === "MultiPoint") {
        feature.geometry.coordinates = feature.geometry.coordinates.map(transformCoord);
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

// Funktion zum Sammeln aller Layer als unified GeoJSON
function getAllLayersAsGeoJSON() {
    const allFeatures = [];
    
    // Durchlaufe alle Layer in allLayers
    if (typeof allLayers !== 'undefined') {
        allLayers.eachLayer(function(layerGroup) {
            // Für jede FeatureGroup
            if (layerGroup.getLayers) {
                layerGroup.eachLayer(function(layer) {
                    // Konvertiere jeden Layer zu GeoJSON
                    if (layer.toGeoJSON) {
                        const feature = layer.toGeoJSON();
                        
                        // Füge zusätzliche Eigenschaften hinzu
                        if (!feature.properties) {
                            feature.properties = {};
                        }
                        
                        // Übernehme Layer-Optionen
                        if (layerGroup.options) {
                            feature.properties.layer_name = layerGroup.options.name;
                            feature.properties.color = layerGroup.options.color;
                            feature.properties.opacity = layerGroup.options.opacity;
                            feature.properties.editable = layerGroup.options.editable;
                        }
                        
                        // Transformiere zurück zu EPSG:25833 wenn nötig
                        transformCoordinatesToUTM(feature);
                        
                        allFeatures.push(feature);
                    }
                });
            }
        });
    }
    
    // Erstelle FeatureCollection
    const geojson = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:EPSG::25833"
            }
        },
        "metadata": {
            "version": "2.0",
            "state": "edited",
            "exported": new Date().toISOString()
        },
        "features": allFeatures
    };
    
    console.log("Exported", allFeatures.length, "features as GeoJSON");
    return geojson;
}

// Funktion zur Rücktransformation von WGS84 zu EPSG:25833
function transformCoordinatesToUTM(feature) {
    if (typeof proj4 === 'undefined') {
        console.error("proj4 is not defined - cannot transform coordinates");
        return;
    }
    
    const transformCoord = coord => {
        // coord ist [lon, lat] in WGS84, transformiere zu [x, y] in UTM
        const transformed = proj4("EPSG:4326", "EPSG:25833", coord);
        // Behalte Z-Koordinate wenn vorhanden
        return coord.length > 2 ? [transformed[0], transformed[1], coord[2]] : transformed;
    };
    
    const transformRing = ring => ring.map(transformCoord);
    
    if (feature.geometry.type === "Polygon") {
        feature.geometry.coordinates = feature.geometry.coordinates.map(transformRing);
    } else if (feature.geometry.type === "MultiPolygon") {
        feature.geometry.coordinates = feature.geometry.coordinates.map(polygon => polygon.map(transformRing));
    } else if (feature.geometry.type === "LineString") {
        feature.geometry.coordinates = transformRing(feature.geometry.coordinates);
    } else if (feature.geometry.type === "MultiLineString") {
        feature.geometry.coordinates = feature.geometry.coordinates.map(transformRing);
    } else if (feature.geometry.type === "Point") {
        feature.geometry.coordinates = transformCoord(feature.geometry.coordinates);
    } else if (feature.geometry.type === "MultiPoint") {
        feature.geometry.coordinates = feature.geometry.coordinates.map(transformCoord);
    }
}

window.importGeoJSON = importGeoJSON; // Funktion global verfügbar machen
window.getAllLayersAsGeoJSON = getAllLayersAsGeoJSON; // Export-Funktion verfügbar machen
