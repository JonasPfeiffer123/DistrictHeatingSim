// Filename: main.js
// Author: Dipl.-Ing. (FH) Jonas Pfeiffer  
// Date: 2025-01-26
// Description: JavaScript-File for the main functionality of the Leaflet map

// Check if map container is already initialized
if (document.getElementById('map')._leaflet_id) {
    console.log('Map container already initialized, skipping main.js initialization');
} else {
    console.log('Initializing map from main.js...');
    
    // Initialize Leaflet map
    const map = L.map('map').setView([51.1657, 10.4515], 6);
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
                allLayers.addLayer(layer);
                console.log('Draw created:', e.layerType);
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
    }

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

            if (window.selectedLayer) {
                window.selectedLayer.addLayer(layer);
                console.log("Element zum ausgewählten Layer hinzugefügt:", window.selectedLayer.options.name);
            } else {
                console.warn("Kein Layer ausgewählt. Erstelle einen neuen Layer.");
                if (typeof createNewLayer === 'function') {
                    createNewLayer();
                    if (window.selectedLayer) {
                        window.selectedLayer.addLayer(layer);
                    }
                } else {
                    allLayers.addLayer(layer);
                }
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
