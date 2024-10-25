// Array zur Verwaltung der Layer
var layerList = [];
let selectedLayer = null;
function addLayerToList(layer) {
    const li = document.createElement('li');
    li.textContent = "Layer " + (layerList.length + 1);
    li.onclick = () => selectLayer(layer);
    document.getElementById('layerList').appendChild(li);
    layerList.push(layer);
}

function selectLayer(layer) {
    selectedLayer = layer;
    document.getElementById('layerName').value = layer.options.name || "Layer";
    document.getElementById('layerColor').value = layer.options.color || "#3388ff";
}

function saveLayerChanges() {
    if (selectedLayer) {
        const newName = document.getElementById('layerName').value;
        const newColor = document.getElementById('layerColor').value;
        selectedLayer.setStyle({ color: newColor });
        selectedLayer.options.name = newName;
    }
}

// Leaflet.draw-Steuerung
var drawControl = new L.Control.Draw({
    edit: {
        featureGroup: allLayers,  // Alle Layer können bearbeitet werden
        remove: true
    },
    draw: {
        polygon: true,
        polyline: true,  // Linien hinzufügen
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
    allLayers.addLayer(layer);  // Füge den neuen Layer zur Gruppe hinzu
    addLayerToList(layer);      // Füge den Layer zur Liste hinzu
});
