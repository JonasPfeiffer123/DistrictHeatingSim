// Filename: layerControl.js
// Author: Dipl.-Ing. (FH) Jonas Pfeiffer
// Date: 2024-10-20
// Description: JavaScript-File for the layer control functionality of the Leaflet map

// Polyfill für _flat, falls es veraltet ist
if (typeof L.LineUtil._flat === 'undefined') {
    L.LineUtil._flat = L.LineUtil.isFlat;
}

// Array zur Verwaltung der Layer
var layerList = [];
let selectedLayer = null;

function addLayerToList(layer) {
    // Überprüfe, ob Layer bereits in der Liste existiert
    if (layerList.includes(layer)) {
        console.warn("Layer ist bereits in der Liste:", layer.options.name);
        return;
    }

    const li = document.createElement('li');
    li.classList.add('layer-item'); 

    const colorIndicator = document.createElement('div');
    colorIndicator.classList.add('color-indicator');
    colorIndicator.style.backgroundColor = layer.options.color || "#3388ff";
    li.appendChild(colorIndicator);

    const layerName = document.createElement('span');
    layerName.textContent = layer.options.name || "Layer";
    li.appendChild(layerName);

    li.layer = layer;

    // Links-Klick zum Auswählen des Layers
    li.onclick = () => selectLayer(layer, li);

    // Rechts-Klick für Kontextmenü
    li.oncontextmenu = (event) => {
        event.preventDefault();
        selectLayer(layer, li);
        openContextMenu(event);
    };

    document.getElementById('layerList').appendChild(li);
    layerList.push(layer);
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

// Kontextmenü öffnen und Aktionen auf den ausgewählten Layer anwenden
function openContextMenu(event) {
    let contextMenu = document.getElementById('layerContextMenu');
    if (!contextMenu) {
        contextMenu = document.createElement('div');
        contextMenu.id = 'layerContextMenu';
        contextMenu.classList.add('context-menu');

        // Umbenennen-Option
        const renameOption = document.createElement('div');
        renameOption.textContent = 'Rename';
        renameOption.onclick = () => {
            const newName = prompt("Enter new name:", selectedLayer.options.name || "Layer");
            if (newName) {
                selectedLayer.options.name = newName;
                updateLayerVisuals(selectedLayer);
            }
            closeContextMenu();
        };
        contextMenu.appendChild(renameOption);

        // Farbe ändern-Option
        const colorOption = document.createElement('div');
        colorOption.textContent = 'Change Color';
        colorOption.onclick = () => {
            document.getElementById('colorPicker').click();
            closeContextMenu();
        };
        contextMenu.appendChild(colorOption);

        // Opazität ändern-Option
        const opacityOption = document.createElement('div');
        opacityOption.textContent = 'Change Opacity';
        opacityOption.onclick = () => {
            document.getElementById('opacitySlider').value = selectedLayer.options.opacity || 1.0;
            document.getElementById('opacitySlider').style.display = 'block';
            closeContextMenu();
        };
        contextMenu.appendChild(opacityOption);

        // Export-Option
        const exportOption = document.createElement('div');
        exportOption.textContent = 'Export';
        exportOption.onclick = () => {
            exportSingleLayer(selectedLayer);
            closeContextMenu();
        };
        contextMenu.appendChild(exportOption);

        // Delete-Option
        const deleteOption = document.createElement('div');
        deleteOption.textContent = 'Delete';
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

// Funktion zum Exportieren eines einzelnen Layers als GeoJSON
function exportSingleLayer(layer) {
    if (layer) {
        const singleLayerGeoJSON = layer.toGeoJSON();
        singleLayerGeoJSON.properties = {
            name: layer.options.name,
            color: layer.options.color,
            opacity: layer.options.opacity
        };
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(singleLayerGeoJSON));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", (layer.options.name || "layer") + ".geojson");
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
        console.log("Layer exportiert:", layer.options.name);
    }
}

// Funktion zum Aktualisieren der Layer-Liste
function updateLayerList() {
    document.getElementById('layerList').innerHTML = '';
    layerList.forEach(layer => addLayerToList(layer));
}

// Löschen des Layers und Aktualisieren der Liste
function deleteLayer(layer) {
    if (allLayers.hasLayer(layer)) {
        allLayers.removeLayer(layer);
    }
    layerList = layerList.filter(l => l !== layer);
    document.getElementById('layerList').innerHTML = '';
    layerList.forEach(layer => addLayerToList(layer)); // Liste neu erstellen
    selectedLayer = null;
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
