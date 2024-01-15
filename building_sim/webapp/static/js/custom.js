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

function calculateCOPYearly() {
    var heiztemperatur = document.getElementById("heiztemperatur").value;
    var wärmequelle = document.getElementById("wärmequelle").value;
    var erdreichTemperatur = document.getElementById("erdreichTemperatur").value;

    $.ajax({
        url: '/calculate_cop_yearly',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ 
            Heiztemperatur: heiztemperatur,
            wärmequelle: wärmequelle,
            ErdreichTemperatur: erdreichTemperatur 
        }),
        success: function(response) {
            // Zeichnen Sie das Diagramm mit den abgerufenen Daten
            drawCOPChart(response);
        },
        error: function(error) {
            console.log(error);
        }
    });
}

function drawCOPChart(data) {
    const ctx = document.getElementById('copChart').getContext('2d'); // Stellen Sie sicher, dass im HTML ein Canvas-Element mit der ID 'copChart' vorhanden ist.
    if (window.copChartInstance) {
        window.copChartInstance.destroy(); // Zerstören Sie die vorherige Instanz, wenn sie existiert.
    }
    window.copChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.time_steps, // Dies sind Ihre X-Achsen-Daten
            datasets: [{
                label: 'COP',
                data: data.COP,
                borderColor: 'blue',
                borderWidth: 1,
                yAxisID: 'y',
                pointRadius: 0
            }, {
                label: 'Stündliche Temperatur (°C)',
                data: data.hourly_temperatures,
                borderColor: 'red',
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

function calculateStrombedarf() {
    var heiztemperatur = document.getElementById("heiztemperatur").value;
    var JEB_Wärme_ges_kWh = document.getElementById("JEB_Wärme_ges_kWh").value;
    var buildingType = document.getElementById("buildingType").value;

    $.ajax({
        url: '/calculate_strombedarf',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ 
            JEB_Wärme_ges_kWh: JEB_Wärme_ges_kWh,
            buildingType: buildingType, 
            Heiztemperatur: heiztemperatur,
            wärmequelle: wärmequelle,
            ErdreichTemperatur: erdreichTemperatur 
        }),
        success: function(response) {
            // Zeichnen Sie das Diagramm mit den abgerufenen Daten
            drawStromChart(response);
        },
        error: function(error) {
            console.log(error);
        }
    });
}

function drawStromChart(data) {
    const ctx = document.getElementById('stromChart').getContext('2d');
    if (window.stromChartInstance) {
        window.stromChartInstance.destroy();
    }
    window.stromChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.time_steps, // Dies sind Ihre X-Achsen-Daten
            datasets: [{
                label: 'Wärmebedarf Gebäude (kW)',
                data: data.waerme_ges_kW,
                borderColor: 'red',
                borderWidth: 1,
                yAxisID: 'y',
                pointRadius: 0
            }, {
                label: 'Stromverbrauch Wärmepumpe (kW)',
                data: data.strom_ges_kW,
                borderColor: 'blue',
                borderWidth: 1,
                yAxisID: 'y',
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
