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
