// Filename: main.js
// Author: Dipl.-Ing. (FH) Jonas Pfeiffer  
// Date: 2025-01-26
// Description: JavaScript-File for the main functionality of the Leaflet map

// Check if map container is already initialized
if (document.getElementById('map')._leaflet_id) {
    console.log('Map container already initialized, skipping main.js initialization');
} else {
    console.log('Initializing map from main.js...');
    
    // Initialize Leaflet map centered on Landkreis Görlitz
    const map = L.map('map').setView([51.158677, 14.740906], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'OpenStreetMap', maxZoom: 22
    }).addTo(map);

    // Store map globally
    window.map = map;

    // Polyfill for _flat if deprecated
    if (typeof L.LineUtil._flat === 'undefined') {
        L.LineUtil._flat = L.LineUtil.isFlat;
    }

    // Define allLayers globally and add to map
    const allLayers = new L.FeatureGroup();
    map.addLayer(allLayers);
    window.allLayers = allLayers;
    window.activeLayer = null; // Globale Variable für aktiven Layer
    window.updateLayerFeatureCount = null; // Wird von layerControl.js gesetzt

    // Check if Leaflet.pm is available
    if (map.pm && map.pm.addControls) {
        console.log('Leaflet.pm available, adding drawing controls');
        // Enable Leaflet.pm controls with snapping
        map.pm.addControls({
            position: 'topleft',
            drawMarker: true,
            drawLine: true,
            drawPolyline: true,
            drawRectangle: true,
            drawCircle: true,
            drawCircleMarker: true,
            drawPolygon: true,
            editMode: true,
            dragMode: true,
            cutPolygon: true,
            removalMode: true,
            rotateMode: false,
        });

        // Set global snapping options for Leaflet.pm
        map.pm.setGlobalOptions({
            snappable: true,
            snapDistance: 5, // Snap threshold in pixels
            allowSelfIntersection: false
        });
    } else {
        console.log('Leaflet.pm not available, adding basic draw controls');
        // Add basic Leaflet.draw controls if available
        if (typeof L.Control.Draw !== 'undefined') {
            var drawControl = new L.Control.Draw({
                edit: {
                    featureGroup: allLayers
                }
            });
            map.addControl(drawControl);

            // Add event listeners for Leaflet.Draw to prevent undefined listener errors
            map.on('draw:created', function(e) {
                var layer = e.layer;
                
                // Füge Layer nur zum aktiven Layer hinzu
                if (window.activeLayer && !window.activeLayer.options.locked) {
                    window.activeLayer.addLayer(layer);
                    // Setze Layer-Eigenschaften
                    if (layer.setStyle) {
                        layer.setStyle({
                            color: window.activeLayer.options.color,
                            fillOpacity: window.activeLayer.options.opacity * 0.5,
                            opacity: window.activeLayer.options.opacity
                        });
                    }
                    console.log('Geometrie zu Layer hinzugefügt:', window.activeLayer.options.name);
                    // Aktualisiere Feature-Count
                    if (typeof updateLayerFeatureCount === 'function') {
                        updateLayerFeatureCount(window.activeLayer);
                    }
                } else {
                    // KEIN Fallback - Warnung anzeigen
                    console.warn('WARNUNG: Kein aktiver Layer! Bitte wählen Sie einen Layer durch Doppelklick aus.');
                    alert('Bitte wählen Sie zuerst einen Layer durch Doppelklick aus, auf dem Sie zeichnen möchten!');
                    // Lösche die gezeichnete Geometrie wieder
                    if (layer && map.hasLayer(layer)) {
                        map.removeLayer(layer);
                    }
                }
            });

            map.on('draw:edited', function(e) {
                console.log('Layers edited:', e.layers);
            });

            map.on('draw:deleted', function(e) {
                console.log('Layers deleted:', e.layers);
            });

            // Fix for "wrong listener type: undefined" error
            map.on('draw:drawstart', function(e) {
                console.log('Draw start:', e.layerType);
            });

            map.on('draw:drawstop', function(e) {
                console.log('Draw stop:', e.layerType);
            });

            // Specifically handle the cancel event that causes the error
            map.on('draw:canceled', function(e) {
                console.log('Draw canceled:', e.layerType);
            });
        } else {
            console.log('No drawing controls available');
        }
    }

    // Toggle marker mode
    let clickMarker = null;
    let markerModeEnabled = false;
    let coordinatePickerActive = false;
    
    function toggleMarkerMode() {
        markerModeEnabled = !markerModeEnabled;
        const button = document.getElementById('toggleMarkerButton');
        if (button) {
            button.textContent = markerModeEnabled ? 'Marker setzen: Aus' : 'Marker setzen: Ein';
        }

        if (markerModeEnabled) {
            map.on('click', onMapClick); // Enable click handler
        } else {
            map.off('click', onMapClick); // Disable click handler
            if (clickMarker) {
                map.removeLayer(clickMarker); // Remove marker if needed
                clickMarker = null;
            }
            const display = document.getElementById('coordinateDisplay');
            if (display) {
                display.textContent = ''; // Clear coordinates display
            }
        }
    }

    // Click handler for the map
    function onMapClick(e) {
        var lat = e.latlng.lat.toFixed(6);
        var lng = e.latlng.lng.toFixed(6);

        const display = document.getElementById('coordinateDisplay');
        if (display) {
            display.textContent = "Latitude: " + lat + ", Longitude: " + lng;
        }

        if (!clickMarker) {
            clickMarker = L.marker([lat, lng]).addTo(map);
        } else {
            clickMarker.setLatLng([lat, lng]);
        }

        clickMarker.bindPopup("Latitude: " + lat + "<br>Longitude: " + lng).openPopup();
        
        // If coordinate picker is active, send coordinates to Python
        if (coordinatePickerActive) {
            sendCoordinateToPython(parseFloat(lat), parseFloat(lng));
            coordinatePickerActive = false;
            map.off('click', onCoordinatePickerClick);
            
            // Optional: Remove marker after picking
            setTimeout(() => {
                if (clickMarker) {
                    map.removeLayer(clickMarker);
                    clickMarker = null;
                }
            }, 2000);
        }
    }
    
    // Coordinate picker click handler (for dialog integration)
    function onCoordinatePickerClick(e) {
        var lat = e.latlng.lat;
        var lng = e.latlng.lng;
        
        console.log("Coordinate picked: ", lat, lng);
        
        // Add temporary marker
        if (clickMarker) {
            map.removeLayer(clickMarker);
        }
        clickMarker = L.marker([lat, lng]).addTo(map);
        clickMarker.bindPopup("Ausgewählte Koordinate:<br>Lat: " + lat.toFixed(6) + "<br>Lon: " + lng.toFixed(6)).openPopup();
        
        // Send to Python
        sendCoordinateToPython(lat, lng);
        
        // Deactivate picker mode
        coordinatePickerActive = false;
        map.off('click', onCoordinatePickerClick);
        
        // Reset display styling immediately
        const display = document.getElementById('coordinateDisplay');
        if (display) {
            display.textContent = "Koordinate ausgewählt: Lat " + lat.toFixed(6) + ", Lon " + lng.toFixed(6);
            display.style.backgroundColor = "#f8f9fa";
            display.style.fontWeight = "normal";
        }
    }
    
    // Function to send coordinates to Python
    function sendCoordinateToPython(lat, lng) {
        if (window.pywebview && window.pywebview.receiveCoordinateFromMap) {
            window.pywebview.receiveCoordinateFromMap(lat, lng);
            console.log("Coordinates sent to Python: ", lat, lng);
        } else {
            console.error("Python bridge not available!");
        }
    }
    
    // Function to activate coordinate picker (called from Python)
    window.activateCoordinatePicker = function() {
        console.log("Activating coordinate picker mode...");
        coordinatePickerActive = true;
        map.on('click', onCoordinatePickerClick);
        
        const display = document.getElementById('coordinateDisplay');
        if (display) {
            display.textContent = "Klicken Sie auf die Karte, um eine Koordinate auszuwählen...";
            display.style.backgroundColor = "#ffc107";
            display.style.fontWeight = "bold";
        }
        
        // Reset display styling after selection
        setTimeout(() => {
            if (display && !coordinatePickerActive) {
                display.style.backgroundColor = "#f8f9fa";
                display.style.fontWeight = "normal";
            }
        }, 30000); // Reset after 30 seconds if no click
    };

    // Event listeners
    const opacityButton = document.getElementById('opacityOkButton');
    if (opacityButton) {
        opacityButton.onclick = () => {
            const control = document.getElementById('opacityControl');
            if (control) {
                control.style.display = 'none';
            }
        };
    }

    // Event for the button to toggle marker mode
    const toggleButton = document.getElementById('toggleMarkerButton');
    if (toggleButton) {
        toggleButton.addEventListener('click', toggleMarkerMode);
    }

    // Enable snapping for each layer on creation
    if (map.pm) {
        map.on('pm:create', (e) => {
            const layer = e.layer;

            // Check if we're in polygon capture mode for dialogs
            if (window.polygonCaptureMode && layer instanceof L.Polygon) {
                console.log('Polygon captured for dialog - keeping it visible and editable');
                
                // Store the polygon layer globally so we can access it later
                window.capturedPolygonLayer = layer;
                
                // Add to map (keep it visible)
                layer.addTo(map);
                
                // Style it to show it's a temporary selection
                layer.setStyle({
                    color: '#ff6b6b',
                    fillColor: '#ff6b6b',
                    fillOpacity: 0.3,
                    opacity: 0.8,
                    weight: 3,
                    dashArray: '10, 10'
                });
                
                // Enable editing on the polygon
                if (layer.pm) {
                    layer.pm.enable({
                        allowSelfIntersection: false,
                        snappable: true,
                        snapDistance: 20
                    });
                }
                
                // Disable drawing mode but keep polygon visible
                window.disablePolygonCaptureMode();
                
                // Notify Python that polygon is ready (but don't send it yet)
                if (typeof window.pywebview !== 'undefined') {
                    // Send a signal that polygon is drawn and ready
                    window.pywebview.polygonReadyForCapture();
                }
                
                return; // Don't add to active layer
            }

            // Normal drawing mode - add to active layer
            if (window.activeLayer && !window.activeLayer.options.locked) {
                window.activeLayer.addLayer(layer);
                // Setze Layer-Eigenschaften
                if (layer.setStyle) {
                    layer.setStyle({
                        color: window.activeLayer.options.color,
                        fillOpacity: window.activeLayer.options.opacity * 0.5,
                        opacity: window.activeLayer.options.opacity
                    });
                }
                console.log('Geometrie zu aktivem Layer hinzugefügt:', window.activeLayer.options.name);
                // Aktualisiere Feature-Count
                if (typeof updateLayerFeatureCount === 'function') {
                    updateLayerFeatureCount(window.activeLayer);
                }
            } else {
                // KEIN Fallback - Warnung anzeigen
                console.warn('WARNUNG: Kein aktiver Layer! Bitte wählen Sie einen Layer durch Doppelklick aus.');
                alert('Bitte wählen Sie zuerst einen Layer durch Doppelklick aus, auf dem Sie zeichnen möchten!');
                // Lösche die gezeichnete Geometrie wieder
                if (layer && map.hasLayer(layer)) {
                    map.removeLayer(layer);
                }
                return;
            }

            if (layer.pm) {
                layer.pm.enable({
                    snappable: true,
                    snapDistance: 5 // Set snapping distance for this layer
                });

                // Real-time snapping with visual feedback
                layer.on('pm:snap', (event) => {
                    console.log('Snapped to:', event.marker.getLatLng());
                    // Optional: Add visual indication of snap points, e.g., change marker color or style
                    if (event.marker && event.marker.setStyle) {
                        event.marker.setStyle({ color: 'red' });
                    }
                });

                layer.on('pm:unsnap', (event) => {
                    console.log('Unsnap:', event.marker.getLatLng());
                    // Reset visual indication when unsnapped
                    if (event.marker && event.marker.setStyle) {
                        event.marker.setStyle({ color: 'green' });
                    }
                });
            }
        });

        // Handle cancel events properly to avoid 'wrong listener type' errors
        map.on('pm:globaldrawmodetoggled', (e) => {
            if (e.enabled === false) {
                console.log('Draw mode disabled');
            }
        });

        map.on('pm:remove', (e) => {
            console.log('Layer removed:', e.layer);
        });

        // Fix for 'wrong listener type: undefined' error with text tool
        map.on('pm:drawstart', (e) => {
            console.log('Draw started:', e.shape);
        });

        map.on('pm:drawend', (e) => {
            console.log('Draw ended:', e.shape);
        });
    }

    console.log('Main.js initialization completed');
}

// Global function to enable polygon capture mode for dialogs
window.enablePolygonCaptureMode = function() {
    console.log('Polygon capture mode enabled');
    window.polygonCaptureMode = true;
    
    // Show info message
    if (map.pm) {
        // Enable polygon drawing
        map.pm.enableDraw('Polygon', {
            snappable: true,
            snapDistance: 20,
            finishOn: 'dblclick'
        });
    }
};

// Global function to disable polygon capture mode
window.disablePolygonCaptureMode = function() {
    console.log('Polygon capture mode disabled');
    window.polygonCaptureMode = false;
    
    if (map.pm) {
        map.pm.disableDraw();
    }
};

// Global function to get captured polygon as GeoJSON
window.getCapturedPolygon = function() {
    if (window.capturedPolygonLayer) {
        console.log('Getting captured polygon');
        return window.capturedPolygonLayer.toGeoJSON();
    }
    console.warn('No polygon captured');
    return null;
};

// Global function to clear captured polygon from map
window.clearCapturedPolygon = function() {
    if (window.capturedPolygonLayer) {
        console.log('Clearing captured polygon');
        map.removeLayer(window.capturedPolygonLayer);
        window.capturedPolygonLayer = null;
        return true;
    }
    return false;
};
