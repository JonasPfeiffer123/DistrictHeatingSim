// Definieren von EPSG:25833 (ETRS89 / UTM Zone 33N)
if (typeof proj4 !== 'undefined') {
    proj4.defs("EPSG:25833", "+proj=utm +zone=33 +ellps=GRS80 +units=m +no_defs");
} else {
    console.error("proj4 is not defined");
}

// Funktion zum Importieren von GeoJSON und Hinzufügen zur Karte
function importGeoJSON(geojsonData) {
    const crs = geojsonData.crs ? geojsonData.crs.properties.name : 'EPSG:4326';
    console.log("CRS of the imported GeoJSON:", crs);

    if (crs === "urn:ogc:def:crs:EPSG::25833") {
        geojsonData.features.forEach(feature => transformCoordinates(feature));
    }

    // In deiner importGeoJSON Funktion:
    geojsonData.features.forEach(feature => {
        if (is3DFeature(feature)) {
            console.log("3D feature detected");
            create3DObject(feature); // 3D-Objekt in Three.js erstellen
            focusMapOnFeature(feature);  // Karte auf das Feature fokussieren
            focusCameraOn3DObjects();  // Kamera auf 3D-Objekte fokussieren
        } else {
            console.log("2D feature detected");
            // add2DLayer(feature); // 2D-Objekt in Leaflet hinzufügen
            create3DObject(feature); // 3D-Objekt in Three.js erstellen
            focusMapOnFeature(feature);  // Karte auf das Feature fokussiere
            focusCameraOn3DObjects();  // Kamera auf 3D-Objekte fokussieren
        }
    });

    // Map bounds nur für 2D-Features
    if (allLayers.getBounds().isValid()) {
        map.fitBounds(allLayers.getBounds());
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

function focusCameraOn3DObjects() {
    const box = new THREE.Box3().setFromObject(scene);
    const center = box.getCenter(new THREE.Vector3());
    camera.position.set(center.x, center.y, camera.position.z);
    camera.lookAt(center);
}

// Funktion zur Erstellung von 3D-Objekten
function create3DObject(feature) {
    const colors = { Ground: 0x00ff00, Wall: 0xff0000, Roof: 0x0000ff, Closure: 0xffff00 };
    const type = feature.properties.Geometr_3D;
    const color = colors[type] || 0xffffff;

    feature.geometry.coordinates.forEach(polygon => {
        polygon.forEach(ring => {
            const vertices = ring.map(coord => {
                const [lng, lat, altitude] = coord;
                const latLng = L.latLng(lat, lng);
                const point = map.latLngToLayerPoint(latLng);
                const z = altitude ? altitude / 100 : 0;  // Höhe reduziert

                // console.log(`Vertex at X: ${point.x}, Y: ${-point.y}, Z: ${z}`);
                return new THREE.Vector3(point.x, -point.y, z);
            });

            const shape = new THREE.Shape(vertices.slice(0, -1));
            const geometry = new THREE.ExtrudeGeometry(shape, { depth: 10, bevelEnabled: false });
            const material = new THREE.MeshBasicMaterial({ color });
            const mesh = new THREE.Mesh(geometry, material);

            mesh.userData.latLng = L.latLng(vertices[0].y, vertices[0].x);
            scene.add(mesh);
        });
    });

    renderer.render(scene, camera);
}

// Überprüfen, ob das Feature 3D-Koordinaten enthält
function is3DFeature(feature) {
    function has3DCoordinates(coords) {
        return Array.isArray(coords[0]) ? coords.some(has3DCoordinates) : coords.length === 3 && coords[2];
    }
    return has3DCoordinates(feature.geometry.coordinates);
}


// Funktion zum Hinzufügen von 2D-Geometrie zur Leaflet-Karte
function add2DLayer(feature) {
    // Entferne Z-Komponente aus den Koordinaten für Leaflet
    const trimmedFeature = {
        ...feature,
        geometry: {
            ...feature.geometry,
            coordinates: feature.geometry.coordinates.map(ring =>
                ring.map(coord => [coord[0], coord[1]]) // Verwende nur X und Y (Longitude, Latitude)
            )
        }
    };

    // Füge das 2D-Feature der Karte hinzu
    const layer = L.geoJSON(trimmedFeature, {
        style: function () { return { color: "#3388ff" }; }
    }).addTo(allLayers); // Hinzufügen zu allLayers für spätere Verwendung

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
