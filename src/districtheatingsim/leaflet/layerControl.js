// Filename: layerControl.js
// Author: Dipl.-Ing. (FH) Jonas Pfeiffer
// Date: 2025-01-26
// Description: JavaScript-File for the layer control functionality of the Leaflet map

// Polyfill für _flat, falls es veraltet ist
if (typeof L.LineUtil._flat === 'undefined') {
    L.LineUtil._flat = L.LineUtil.isFlat;
}

// Array zur Verwaltung der Layer
var layerList = [];
let selectedLayer = null;

function createNewLayer() {
    const layerName = prompt("Geben Sie den Namen des neuen Layers ein:");
    if (layerName) {
        const newLayer = L.layerGroup();
        newLayer.options = {
            name: layerName,
            color: getRandomColor(),
            opacity: 1.0
        };
        addLayerToList(newLayer);
        allLayers.addLayer(newLayer);
        map.addLayer(newLayer);
        selectedLayer = newLayer;
        console.log("Neuer Layer erstellt:", layerName);
    } else {
        console.warn("Layer-Erstellung abgebrochen.");
    }
}

function addLayerToList(layer) {
    // Überprüfe, ob Layer bereits in der Liste existiert
    if (layerList.includes(layer)) {
        console.warn("Layer ist bereits in der Liste:", layer.options.name);
        return;
    }

    layerList.push(layer); // Füge den Layer zur Liste hinzu

    const li = document.createElement('li');
    li.classList.add('layer-item');
    li.layer = layer; // Verknüpfe den Listeneintrag mit dem Layer

    const colorIndicator = document.createElement('div');
    colorIndicator.classList.add('color-indicator');
    colorIndicator.style.backgroundColor = layer.options.color || "#3388ff";
    li.appendChild(colorIndicator);

    const layerName = document.createElement('span');
    layerName.textContent = layer.options.name || "Layer";
    li.appendChild(layerName);

    // Links-Klick zum Auswählen des Layers
    li.onclick = () => selectLayer(layer, li);

    // Rechts-Klick für Kontextmenü
    li.oncontextmenu = (event) => {
        event.preventDefault();
        selectLayer(layer, li);
        openContextMenu(event);
    };

    document.getElementById('layerList').appendChild(li);
}

// Funktion, um die Darstellung des Layers in der Liste nur visuell anzupassen
function updateLayerVisuals(layer) {
    const listItems = document.querySelectorAll('.layer-item');
    listItems.forEach(item => {
        if (item.layer === layer) {
            item.querySelector('.color-indicator').style.backgroundColor = layer.options.color;
            item.querySelector('span').textContent = layer.options.name;
        }
    });
}

document.getElementById('opacityOkButton').onclick = () => {
    document.getElementById('opacityControl').style.display = 'none';
};

function openOpacitySlider(layer) {
    selectedLayer = layer;
    document.getElementById('opacitySlider').value = layer.options.opacity || 1.0;
    document.getElementById('opacityControl').style.display = 'flex';
}

document.getElementById('opacitySlider').oninput = (event) => {
    const opacity = event.target.value;
    if (selectedLayer) {
        selectedLayer.setStyle({ opacity: parseFloat(opacity) });
        selectedLayer.options.opacity = parseFloat(opacity);
        console.log("Opazität geändert:", opacity);
    }
};

// Kontextmenü öffnen und Aktionen auf den ausgewählten Layer anwenden
function openContextMenu(event) {
    let contextMenu = document.getElementById('layerContextMenu');
    if (!contextMenu) {
        contextMenu = document.createElement('div');
        contextMenu.id = 'layerContextMenu';
        contextMenu.classList.add('context-menu');

        // Umbenennen-Option
        const renameOption = document.createElement('div');
        renameOption.textContent = 'Layernamen Umbenennen';
        renameOption.onclick = () => {
            const newName = prompt("Geben sie einen neuen Namen:", selectedLayer.options.name || "Layer");
            if (newName) {
                selectedLayer.options.name = newName;
                updateLayerVisuals(selectedLayer);
            }
            closeContextMenu();
        };
        contextMenu.appendChild(renameOption);

        // Farbe ändern-Option
        const colorOption = document.createElement('div');
        colorOption.textContent = 'Layerfarbe Ändern';
        colorOption.onclick = () => {
            document.getElementById('colorPicker').click();
            closeContextMenu();
        };
        contextMenu.appendChild(colorOption);

        // Opazität ändern-Option
        const opacityOption = document.createElement('div');
        opacityOption.textContent = 'Layerdichte ändern';
        opacityOption.onclick = () => {
            openOpacitySlider(selectedLayer);
            closeContextMenu();
        };
        contextMenu.appendChild(opacityOption);

        // Export-Option
        const exportOption = document.createElement('div');
        exportOption.textContent = 'Layer Exportieren';
        exportOption.onclick = () => {
            exportSingleLayer(selectedLayer);
            closeContextMenu();
        };
        contextMenu.appendChild(exportOption);

        // Delete-Option
        const deleteOption = document.createElement('div');
        deleteOption.textContent = 'Layer Löschen';
        deleteOption.onclick = () => {
            deleteLayer(selectedLayer);
            closeContextMenu();
        };
        contextMenu.appendChild(deleteOption);

        document.body.appendChild(contextMenu);
    }

    contextMenu.style.top = `${event.clientY}px`;
    contextMenu.style.left = `${event.clientX}px`;
    contextMenu.style.display = 'block';

    document.addEventListener('click', closeContextMenu);
}

// Farbe ändern und nur die Darstellung aktualisieren
function applyColorChange(newColor) {
    if (selectedLayer && newColor) {
        selectedLayer.setStyle({ color: newColor });
        selectedLayer.options.color = newColor;
        updateLayerVisuals(selectedLayer); // Nur visuell aktualisieren
    }
}

// Opazität ändern und nur die Darstellung aktualisieren
function applyOpacityChange(newOpacity) {
    if (selectedLayer && newOpacity) {
        selectedLayer.setStyle({ opacity: parseFloat(newOpacity), fillOpacity: parseFloat(newOpacity) * 0.5 });
        selectedLayer.options.opacity = parseFloat(newOpacity);
        updateLayerVisuals(selectedLayer); // Nur visuell aktualisieren
    }
}

// Schließt das Kontextmenü
function closeContextMenu() {
    const contextMenu = document.getElementById('layerContextMenu');
    if (contextMenu) {
        contextMenu.style.display = 'none';
    }
    document.removeEventListener('click', closeContextMenu);
}

// Auswahl und visuelle Aktualisierung eines Layers
function selectLayer(layer, listItem) {
    document.querySelectorAll('.layer-item').forEach(item => item.classList.remove('selected-layer'));
    listItem.classList.add('selected-layer');
    selectedLayer = layer;
}

// Funktion zum Speichern der Änderungen am Layer (Name und Farbe)
function saveLayerChanges() {
    if (selectedLayer) {
        const newName = document.getElementById('layerName').value;
        const newColor = document.getElementById('layerColor').value;

        console.log("Änderungen speichern für Layer:", selectedLayer.options.name);
        console.log("Neuer Name:", newName);
        console.log("Neue Farbe:", newColor);

        // Ändere den Namen des Layers in den Optionen
        selectedLayer.options.name = newName;

        // Ändere die Farbe des Layers auf der Karte
        if (selectedLayer.setStyle) {
            selectedLayer.setStyle({ color: newColor }); // Ändere die Farbe sofort auf der Karte
        } else if (selectedLayer instanceof L.Marker) {
            // Falls es sich um einen Marker handelt, ändere das Icon entsprechend
            const icon = L.divIcon({
                className: 'custom-icon',
                html: `<div style="background-color:${newColor}; width:12px; height:12px; border-radius:50%;"></div>`
            });
            selectedLayer.setIcon(icon);
        }

        // Speichere die Farbe in den Layer-Optionen für zukünftige Verwendungen
        selectedLayer.options.color = newColor;

        // Aktualisiere den Listeneintrag mit dem neuen Namen
        document.querySelectorAll('.layer-item').forEach(item => {
            if (item.layer === selectedLayer) {
                item.textContent = newName || "Layer";
            }
        });
    } else {
        console.warn("Kein Layer ausgewählt, bitte einen Layer auswählen, bevor Änderungen gespeichert werden.");
    }
}

// Funktion zur Anpassung der Opazität
function updateLayerOpacity() {
    if (selectedLayer && selectedLayer.setStyle) {
        const opacity = document.getElementById('layerOpacity').value;
        selectedLayer.setStyle({ opacity: parseFloat(opacity) });
        selectedLayer.options.opacity = parseFloat(opacity);
        console.log("Opazität geändert:", opacity);
    }
}

// Funktion zum Exportieren eines einzelnen Layers als GeoJSON und Senden an PyQt5
function exportSingleLayer(layer) {
    if (layer) {
        let singleLayerGeoJSON = layer.toGeoJSON();

        // Prüfe, ob das Ergebnis ein FeatureCollection oder ein einzelnes Feature ist
        let geojsonToSend;
        if (singleLayerGeoJSON.type === "FeatureCollection") {
            // Füge die Properties zu jedem Feature hinzu
            geojsonToSend = singleLayerGeoJSON;
            geojsonToSend.features.forEach(feature => {
                feature.properties = feature.properties || {};
                feature.properties.name = layer.options.name;
                feature.properties.color = layer.options.color;
                feature.properties.opacity = layer.options.opacity;
            });
        } else if (singleLayerGeoJSON.type === "Feature") {
            // Wandle in FeatureCollection um
            geojsonToSend = {
                type: "FeatureCollection",
                features: [singleLayerGeoJSON]
            };
            geojsonToSend.features[0].properties = geojsonToSend.features[0].properties || {};
            geojsonToSend.features[0].properties.name = layer.options.name;
            geojsonToSend.features[0].properties.color = layer.options.color;
            geojsonToSend.features[0].properties.opacity = layer.options.opacity;
        } else {
            console.error("Unbekannter GeoJSON-Typ:", singleLayerGeoJSON.type);
            return;
        }

        const geojsonString = JSON.stringify(geojsonToSend);

        // Senden der GeoJSON-Daten an PyQt5
        if (window.pywebview) {
            window.pywebview.exportGeoJSON(geojsonString).then(response => {
                console.log("Layer exportiert:", layer.options.name);
            }).catch(error => {
                console.error("Fehler beim Exportieren des Layers:", error);
            });
        } else {
            console.error("PyWebView API nicht verfügbar.");
        }
    }
}

// Funktion zum Aktualisieren der Layer-Liste
function updateLayerList() {
    const layerListElement = document.getElementById('layerList');
    layerListElement.innerHTML = '';
    layerList.forEach(layer => addLayerToList(layer));
}

// Löschen des Layers und Aktualisieren der Liste
function deleteLayer(layer) {
    console.log("Versuche, Layer zu löschen:", layer.options.name);

    // Überprüfen des Typs und Inhalts von allLayers
    console.log("Typ von allLayers:", typeof allLayers);
    console.log("Anzahl der Layer in allLayers:", allLayers.getLayers().length);

    // Überprüfen des Typs und Inhalts von layer
    console.log("Typ von layer:", typeof layer);
    console.log("Layer-Name:", layer.options.name);

    if (allLayers.hasLayer(layer)) {
        console.log("Layer in allLayers gefunden. Entferne Layer aus allLayers.");
        allLayers.removeLayer(layer); // Entferne die Layer aus der allLayers-Gruppe
    } else {
        console.log("Layer nicht in allLayers gefunden.");
    }

    if (map.hasLayer(layer)) {
        console.log("Layer in der Karte gefunden. Entferne Layer aus der Karte.");
        map.removeLayer(layer); // Entferne die Layer direkt aus der Karte
    } else {
        console.log("Layer nicht in der Karte gefunden.");
    }

    layerList = layerList.filter(l => l !== layer); // Entferne die Layer aus der Liste

    // Entferne den entsprechenden Listeneintrag aus der Anzeige
    const listItems = document.querySelectorAll('.layer-item');
    listItems.forEach(item => {
        if (item.layer === layer) {
            item.remove();
        }
    });

    selectedLayer = null;
    // updateLayerList(); // Aktualisiere die Layer-Liste
}

// Funktion zum automatischen Verbinden von Linienendpunkten nach dem Bearbeiten
function snapLineEndpoints(layerGroup, threshold = 0.0001) {
    const layers = [];
    
    // Speichere alle Liniensegmente in einer Liste
    layerGroup.eachLayer(layer => {
        if (layer instanceof L.Polyline) {
            layers.push(layer);
        }
    });

    // Vergleiche alle Endpunkte miteinander
    layers.forEach(layerA => {
        const latlngsA = layerA.getLatLngs();
        const startA = latlngsA[0];
        const endA = latlngsA[latlngsA.length - 1];

        layers.forEach(layerB => {
            if (layerA === layerB) return;

            const latlngsB = layerB.getLatLngs();
            const startB = latlngsB[0];
            const endB = latlngsB[latlngsB.length - 1];

            // Überprüfe, ob die Endpunkte nahe beieinander liegen und "snappe" sie
            if (startA.distanceTo(endB) < threshold) {
                layerB.setLatLngs([startA, ...latlngsB.slice(1)]);
            }
            if (endA.distanceTo(startB) < threshold) {
                layerA.setLatLngs([...latlngsA.slice(0, -1), startB]);
            }
        });
    });
}
