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

@app.route('/calculate_cop', methods=['POST'])
def calculate_cop():
    try:
        data = request.json
        QT = float(data['quelltemperatur'])
        HT = float(data['heiztemperatur'])

        # Verhindern Sie eine Division durch Null, wenn HT und QT gleich sind
        if HT == QT:
            return jsonify({'error': 'Heiztemperatur und Quelltemperatur dürfen nicht gleich sein'}), 400

        COP_id = (HT + 273.15) / (HT - QT)
        COP = COP_id * 0.6  # Anpassen Sie diese Formel nach Bedarf
        return jsonify({'cop': COP})
    
    except (ValueError, ZeroDivisionError) as e:
        return jsonify({'error': str(e)}), 400

@app.route('/calculate_cop_yearly', methods=['POST'])
def calculate_cop_yearly():
    try:
        data = request.json
        HT = float(data['Heiztemperatur'])
        JEB_Wärme_ges_kWh = 1
        building_type = "HMF"
        time_steps, _, hourly_temperatures  = heat_requirement_BDEW.calculate(JEB_Wärme_ges_kWh, building_type, subtyp="03")
        
        wärmequelle = data['wärmequelle']
        if wärmequelle == "Erdreich":
            hourly_temperatures = np.full(8760, float(data['ErdreichTemperatur']))

        COP_id = (HT + 273.15) / (HT - hourly_temperatures)
        COP = COP_id * 0.6

        result = {
            "time_steps": time_steps.tolist(),
            "COP": COP.tolist(),
            "hourly_temperatures": hourly_temperatures.tolist()
        }

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/calculate_strombedarf', methods=['POST'])
def calculate_strombedarf():
    try:
        data = request.json
        JEB_Wärme_ges_kWh = float(data['JEB_Wärme_ges_kWh'])

        building_type = data['buildingType']

        time_steps, waerme_ges_kW, hourly_temperatures  = heat_requirement_BDEW.calculate(JEB_Wärme_ges_kWh, building_type, subtyp="03")
        
        waerme_ges_kW = np.array(waerme_ges_kW)

        HT = float(data['Heiztemperatur'])

        wärmequelle = data['wärmequelle']
        if wärmequelle == "Erdreich":
            hourly_temperatures = np.full(8760, float(data['ErdreichTemperatur']))

        COP_id = (HT + 273.15) / (HT - hourly_temperatures)
        COP = COP_id * 0.6

        strom_ges_kW = waerme_ges_kW / COP

        strombedarf_gesamt_kWh = np.sum(strom_ges_kW)
        JAZ = JEB_Wärme_ges_kWh/strombedarf_gesamt_kWh

        result = {
            "time_steps": time_steps.tolist(),
            "waerme_ges_kW": waerme_ges_kW.tolist(),
            "strom_ges_kW": strom_ges_kW.tolist(),
            "strombedarf_gesamt_kWh": strombedarf_gesamt_kWh,
            "JAZ": JAZ
        }

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})
    
if __name__ == '__main__':
    app.run(debug=True, port=8000)
