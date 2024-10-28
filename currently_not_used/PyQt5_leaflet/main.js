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
renderer.domElement.style.position = "absolute";  // Überlappt die Leaflet-Karte
renderer.domElement.style.top = "0";
renderer.domElement.style.left = "0";
document.getElementById('map').appendChild(renderer.domElement);

// Synchronisiere die Größe des Renderers mit der Karte
function updateRendererSize() {
    const mapSize = map.getSize();
    renderer.setSize(mapSize.x, mapSize.y);
}
updateRendererSize();
map.on('resize', updateRendererSize);

// Three.js Szene und Kamera
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 5000);
camera.position.set(0, 0, 1000);  // Höhere Z-Position für besseres Sichtfeld
camera.lookAt(new THREE.Vector3(0, 0, 0));

const light = new THREE.DirectionalLight(0xffffff, 1);
light.position.set(500, 500, 1000).normalize();
scene.add(light);

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// Kartenbewegung und Zoom
map.on('move', update3DObjects);
map.on('zoom', update3DObjects);

// Update-Funktion für 3D-Objekte
function update3DObjects() {
    const zoomScale = Math.pow(2, map.getZoom());

    scene.children.forEach(object => {
        if (object instanceof THREE.Mesh) {
            const latLng = object.userData.latLng;
            const point = map.latLngToLayerPoint(latLng);

            object.position.set(point.x, -point.y, object.position.z);
            object.scale.set(zoomScale, zoomScale, zoomScale);
        }
    });

    renderer.render(scene, camera);
}

// Animationsschleife
function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
}
animate();