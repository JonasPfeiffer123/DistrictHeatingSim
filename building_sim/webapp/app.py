from flask import Flask, render_template, request, jsonify
import heat_requirement_BDEW
import numpy as np

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        JEB_Wärme_ges_kWh = float(data['JEB_Wärme_ges_kWh'])
        building_type = data['building_type']

        # Hier würden Sie die gleiche Logik wie in Ihrer PyQt5-App verwenden
        # Beispiel:
        time_steps, waerme_ges_kW, hourly_temperatures = heat_requirement_BDEW.calculate(JEB_Wärme_ges_kWh, building_type, subtyp="03")

        # Konvertieren Sie die Daten in ein Format, das an das Frontend gesendet werden kann
        result = {
            "time_steps": time_steps.tolist(),
            "waerme_ges_kW": waerme_ges_kW.tolist(),
            "hourly_temperatures": hourly_temperatures.tolist()
        }

        return jsonify(result)
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=8000)
