function calculate() {
    const JEB_Wärme_ges_kWh = document.getElementById('JEB_Wärme_ges_kWh').value;
    const building_type = document.getElementById('buildingType').value;

    fetch('/calculate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ JEB_Wärme_ges_kWh, building_type }),
    })
    .then(response => response.json())
    .then(data => {
        const convertedDates = data.time_steps.map(t => new Date(t));

        console.log("Umgewandelte Zeitstempel:", convertedDates);
        drawChart(data);
    })
    .catch(error => {
        console.error('Error during fetch operation:', error);
    });
}

function drawChart(data) {
    const ctx = document.getElementById('myChart').getContext('2d');
    if (window.myChartInstance) {
        window.myChartInstance.destroy();
    }
    window.myChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.time_steps, // Dies sind Ihre X-Achsen-Daten
            datasets: [{
                label: 'Gesamtlast Gebäude (kW)',
                data: data.waerme_ges_kW,
                borderColor: 'blue',
                borderWidth: 1,
                yAxisID: 'y',
                pointRadius: 0
            }, {
                label: 'Lufttemperatur (°C)',
                data: data.hourly_temperatures,
                borderColor: 'green',
                borderWidth: 1,
                yAxisID: 'y1',
                pointRadius: 0
            }]
        },
        options: {
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',

                    // Spiegeln der Y-Achse auf die rechte Seite des Diagramms
                    grid: {
                        drawOnChartArea: false, // Nur Gitterlinien für diese Achse ausblenden
                    },
                },
                x: {
                    ticks: {
                        // Das automatische Überspringen und die Begrenzung der Anzeige der Ticks
                        autoSkip: true,
                        maxTicksLimit: 12 // Begrenzen Sie die Anzahl der X-Achsen-Ticks
                    }
                }
            }
        }
    });
}

// Event-Listener für den COP-Berechnungsknopf
document.getElementById('calculateCOPButton').addEventListener('click', function() {
    const quelltemperatur = document.getElementById('QuelltemperaturInput').value;
    const heiztemperatur = document.getElementById('HeiztemperaturInput').value;

    fetch('/calculate_cop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ quelltemperatur, heiztemperatur }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            document.getElementById('resultOutput').value = data.error;
        } else {
            document.getElementById('resultOutput').value = data.cop.toFixed(2);
        }
    })
    .catch(error => {
        console.error('Error during fetch operation:', error);
        document.getElementById('resultOutput').value = 'Fehler bei der Berechnung';
    });
});

document.getElementById('calculateHeatGenButton').addEventListener('click', function() {
    const heiztemperatur = document.getElementById('HeiztemperaturInput').value;
    const waermequelle = document.getElementById('wärmequelleInput').value;
    const erdreich_temperatur = document.getElementById('ErdreichTemperaturInput').value;

    fetch('/calculate_heatgen', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ heiztemperatur, waermequelle, erdreich_temperatur }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error('Error:', data.error);
            // Fehlerbehandlung
        } else {
            updateHeatGenResults(data);
            drawHeatGenChart(data);
        }
    })
    .catch(error => {
        console.error('Error during fetch operation:', error);
        // Fehlerbehandlung
    });
});

function updateHeatGenResults(data) {
    // Ergebnisse aus dem Antwortobjekt abrufen
    const cop = data.cop;
    const stromverbrauch = data.stromverbrauch;

    // Elemente im DOM mit den neuen Werten aktualisieren
    document.getElementById('resultCOP').innerText = cop.toFixed(2); // Formatieren Sie die Zahl auf 2 Dezimalstellen
    document.getElementById('resultStromverbrauch').innerText = stromverbrauch.toFixed(2); // Formatieren Sie die Zahl auf 2 Dezimalstellen
}

function drawHeatGenChart(data) {
    const ctx = document.getElementById('heatGenChart').getContext('2d');
    if (window.heatGenChartInstance) {
        window.heatGenChartInstance.destroy();
    }
    window.heatGenChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.time_steps, // Ersetzen Sie dies durch Ihre Zeitachsen-Daten
            datasets: [{
                label: 'COP',
                data: data.cop, // Ersetzen Sie dies durch Ihre COP-Daten
                borderColor: 'blue',
                borderWidth: 1
            }, {
                label: 'Stromverbrauch',
                data: data.stromverbrauch, // Ersetzen Sie dies durch Ihre Stromverbrauchsdaten
                borderColor: 'red',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            title: {
                display: true,
                text: 'Heizungsauslegung'
            },
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero: true
                    }
                }]
            }
        }
    });
}