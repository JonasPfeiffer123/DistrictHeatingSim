// Leaflet Karte initialisieren
const map = L.map('map').setView([51.1657, 10.4515], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: 'OpenStreetMap'
}).addTo(map);

// Definiere allLayers global und füge es zur Karte hinzu
const allLayers = new L.FeatureGroup();
map.addLayer(allLayers);

// Three.js Renderer und Szene initialisieren
const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.getElementById('map').appendChild(renderer.domElement);

// Synchronisiere die Größe des Renderers mit der Karte
function updateRendererSize() {
    const mapSize = map.getSize(); // Hole die aktuelle Größe der Karte
    renderer.setSize(mapSize.x, mapSize.y);  // Setze die Renderer-Größe auf die Kartengröße
}

// Führe die Größenänderung einmal bei der Initialisierung aus
updateRendererSize();

// Aktualisiere die Renderer-Größe bei Kartengrößenänderungen
map.on('resize', updateRendererSize);

// Three.js Szene und Kamera
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 2000);
camera.position.set(0, 0, 1000);  // Setze die Kamera weiter nach oben (Z-Achse)
camera.lookAt(new THREE.Vector3(0, 0, 0));  // Richte die Kamera auf das Zentrum der Szene

// Lichtquelle hinzufügen
const light = new THREE.DirectionalLight(0xffffff, 1);
light.position.set(500, 500, 1000).normalize();
scene.add(light);

// Eventlistener für das Anpassen der Kameraposition bei Größenänderung des Fensters
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// Hier fügst du die Eventlistener für Bewegung und Zoom der Karte hinzu:
map.on('move', update3DObjects);
map.on('zoom', update3DObjects);

// Implementierung von update3DObjects, um die Position der 3D-Objekte anzupassen
function update3DObjects() {
    const zoomScale = Math.pow(2, map.getZoom());  // Berechne den Zoom-Faktor der Karte

    // Durchlaufe alle 3D-Objekte in der Szene
    scene.children.forEach(function (object) {
        if (object instanceof THREE.Mesh) {
            const latLng = object.userData.latLng;  // Hole die gespeicherten Lat/Lng-Koordinaten
            const point = map.latLngToLayerPoint(latLng);  // Konvertiere in Layer-Koordinaten
            
            // Aktualisiere die Position des Mesh-Objekts basierend auf der Kartenverschiebung und dem Zoom
            object.position.set(point.x, -point.y, object.position.z);
            
            // Optional: Aktualisiere die Skalierung basierend auf dem Zoom
            object.scale.set(zoomScale, zoomScale, zoomScale);  // Passe die Skalierung an den Zoomfaktor an
        }
    });

    renderer.render(scene, camera);  // Aktualisiere die Szene
}


// Animationsschleife für das Rendering der Szene
function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
}
animate();
