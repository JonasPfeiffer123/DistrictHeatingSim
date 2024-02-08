from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, QComboBox, \
    QTableWidget, QPushButton, QTableWidgetItem, QHBoxLayout, QFileDialog
import pandas as pd
import numpy as np
from heat_requirement.heat_requirement_BDEW import import_TRY
import pandapipes as pp
import os
import json


class HeatDemandEditDialog(QDialog):
    def __init__(self, gdf_HAST, hastInput, parent=None):
        super(HeatDemandEditDialog, self).__init__(parent)
        self.gdf_HAST = gdf_HAST
        self.hastInput = hastInput
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        # Erstelle eine Tabelle für die Bearbeitung
        self.heatDemandTable = QTableWidget(self)
        self.loadHeatDemandData()
        self.layout.addWidget(self.heatDemandTable)

        # Speicher-Button
        saveButton = QPushButton("Änderungen speichern", self)
        saveButton.clicked.connect(self.saveHeatDemandData)
        self.layout.addWidget(saveButton)

    def loadHeatDemandData(self):
        df = pd.DataFrame(self.gdf_HAST.drop(columns=[self.gdf_HAST.geometry.name]))
        self.heatDemandTable.setRowCount(len(df))
        self.heatDemandTable.setColumnCount(len(df.columns))
        self.heatDemandTable.setHorizontalHeaderLabels(df.columns)

        for i, row in df.iterrows():
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                self.heatDemandTable.setItem(i, j, item)

    def saveHeatDemandData(self):
        for i in range(self.heatDemandTable.rowCount()):
            for j, column_name in enumerate(self.gdf_HAST.drop(columns=[self.gdf_HAST.geometry.name]).columns):
                cell_value = self.heatDemandTable.item(i, j).text()
                self.gdf_HAST.at[i, column_name] = cell_value

        self.gdf_HAST.to_file(self.hastInput, driver='GeoJSON')
        self.accept()  # Schließt das Dialogfenster

class NetGenerationDialog(QDialog):
    def __init__(self, generate_callback, edit_hast_callback, base_path,parent=None):
        super().__init__(parent)
        self.generate_callback = generate_callback
        self.edit_hast_callback = edit_hast_callback
        self.base_path = base_path
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        self.setWindowTitle("Netz generieren")

        # Importtyp-Auswahl
        self.importTypeComboBox = QComboBox(self)
        self.importTypeComboBox.addItems(["GeoJSON", "Stanet"])
        layout.addWidget(QLabel("Importtyp:"))
        layout.addWidget(self.importTypeComboBox)

        # GeoJSON-spezifische Eingabefelder
        self.geojsonInputs = self.createGeojsonInputs()

        # Stanet-spezifische Eingabefelder
        self.stanetInputs = self.createStanetInputs()

        # Hinzufügen der Eingabefelder zum Layout
        for input_layout in self.geojsonInputs + self.stanetInputs:
            layout.addLayout(input_layout)

        temperature_control_layout = self.createTemperatureControlInput()
        layout.addLayout(temperature_control_layout)

        parameter_inputs_layout = self.createParameterInputs()
        layout.addLayout(parameter_inputs_layout)

        # Button zum Starten der Netzgenerierung
        self.generateButton = QPushButton("Netz generieren", self)
        self.generateButton.clicked.connect(self.generateNetwork)
        layout.addWidget(self.generateButton)

        # Update der Sichtbarkeit basierend auf dem gewählten Importtyp
        self.importTypeComboBox.currentIndexChanged.connect(self.updateInputFieldsVisibility)
        self.updateInputFieldsVisibility()

    def createGeojsonInputs(self):
        default_paths = {
            'Erzeugeranlagen': f'{self.base_path}/Wärmenetz/Erzeugeranlagen.geojson',
            'HAST': f'{self.base_path}/Wärmenetz/HAST.geojson',
            'Vorlauf': f'{self.base_path}/Wärmenetz/Vorlauf.geojson',
            'Rücklauf': f'{self.base_path}/Wärmenetz/Rücklauf.geojson'
        }

        file_inputs_layout = self.createFileInputsGeoJSON(default_paths)
        calculation_method_layout = self.createCalculationMethodInput()
        building_type_layout = self.createBuildingTypeInput()
        edit_hast_layout = self.createEditHASTButton()

        inputs = [
            file_inputs_layout,
            calculation_method_layout,
            building_type_layout,
            edit_hast_layout
        ]
        return inputs

    def createStanetInputs(self):
        default_path = f'{self.base_path}/Wärmenetz/Beleg_1.CSV'

        self.stanetinput = self.createFileInput("Stanet CSV:", default_path)
        inputs = [
           self.stanetinput
        ]
        return inputs
    
    def createFileInputsGeoJSON(self, default_paths):
        layout = QVBoxLayout()
        self.vorlaufInput = self.createFileInput("Vorlauf GeoJSON:", default_paths['Vorlauf'])
        layout.addLayout(self.vorlaufInput)
        
        self.ruecklaufInput = self.createFileInput("Rücklauf GeoJSON:", default_paths['Rücklauf'])
        layout.addLayout(self.ruecklaufInput)

        self.hastInput = self.createFileInput("HAST GeoJSON:", default_paths['HAST'])
        layout.addLayout(self.hastInput)

        self.erzeugeranlagenInput = self.createFileInput("Erzeugeranlagen GeoJSON:", default_paths['Erzeugeranlagen'])
        layout.addLayout(self.erzeugeranlagenInput)

        return layout
    
    def createFileInput(self, label_text, default_text):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        line_edit = QLineEdit(default_text)
        button = QPushButton("Datei auswählen")
        button.clicked.connect(lambda: self.selectFilename(line_edit))
        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return layout
    
    def createCalculationMethodInput(self):
        layout = QVBoxLayout()
        self.calcMethodInput = QComboBox(self)
        self.calcMethodInput.addItems(["Datensatz", "BDEW", "VDI4655"])
        layout.addWidget(QLabel("Berechnungsmethode:"))
        layout.addWidget(self.calcMethodInput)
        return layout

    def createBuildingTypeInput(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Gebäudetyp:"))
        self.buildingTypeInput = QComboBox(self)
        layout.addWidget(self.buildingTypeInput)
        self.updateBuildingType()
        self.calcMethodInput.currentIndexChanged.connect(self.updateBuildingType)
        return layout

    def createEditHASTButton(self):
        layout = QVBoxLayout()
        self.editHASTButton = QPushButton("Hausanschlussstationen bearbeiten", self)
        self.editHASTButton.clicked.connect(self.editHAST)
        layout.addWidget(self.editHASTButton)
        return layout
    
    def createTemperatureControlInput(self):
        layout = QVBoxLayout()
        self.temperatureControlInput = QComboBox(self)
        self.temperatureControlInput.addItems(["Statisch", "Gleitend"])
        layout.addWidget(QLabel("Vorlauftemperatur-Regelung:"))
        layout.addWidget(self.temperatureControlInput)
        self.temperatureControlInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)
        return layout

    def createParameterInputs(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Parameter:"))

        self.parameter_rows = []

        # Parameterzeile für Vorlauftemperatur
        supply_temp_row = self.createParameterRow("Vorlauftemperatur:", "85")
        self.parameter_rows.append(supply_temp_row)
        layout.addLayout(supply_temp_row)

        # Parameterzeile für Maximale Vorlauftemperatur
        max_supply_temp_row = self.createParameterRow("Maximale Vorlauftemperatur:", "85")
        self.parameter_rows.append(max_supply_temp_row)
        layout.addLayout(max_supply_temp_row)

        # Parameterzeile für Minimale Vorlauftemperatur
        min_supply_temp_row = self.createParameterRow("Minimale Vorlauftemperatur:", "70")
        self.parameter_rows.append(min_supply_temp_row)
        layout.addLayout(min_supply_temp_row)

        # Parameterzeile für Obere Grenze der Lufttemperatur
        max_air_temp_row = self.createParameterRow("Obere Grenze der Lufttemperatur:", "15")
        self.parameter_rows.append(max_air_temp_row)
        layout.addLayout(max_air_temp_row)

        # Parameterzeile für Untere Grenze der Lufttemperatur
        min_air_temp_row = self.createParameterRow("Untere Grenze der Lufttemperatur:", "-10")
        self.parameter_rows.append(min_air_temp_row)
        layout.addLayout(min_air_temp_row)

        # Parameterzeile für Rücklauftemperatur
        return_temp_row = self.createParameterRow("Rücklauftemperatur:", "60")
        self.parameter_rows.append(return_temp_row)
        layout.addLayout(return_temp_row)

        # Parameterzeile für Vorlaufdruck
        flow_pressure_row = self.createParameterRow("Vorlaufdruck:", "4")
        self.parameter_rows.append(flow_pressure_row)
        layout.addLayout(flow_pressure_row)

        # Parameterzeile für Druckdifferenz Vorlauf/Rücklauf
        lift_pressure_row = self.createParameterRow("Druckdifferenz Vorlauf/Rücklauf:", "1.5")
        self.parameter_rows.append(lift_pressure_row)
        layout.addLayout(lift_pressure_row)

        return layout

    def createParameterRow(self, label_text, default_text):
        row_layout = QHBoxLayout()
        label = QLabel(label_text)
        line_edit = QLineEdit(default_text)
        row_layout.addWidget(label)
        row_layout.addWidget(line_edit)
        return row_layout
    
    def set_layout_visibility(self, layout, visible):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.setVisible(visible)
            elif item.layout():
                self.set_layout_visibility(item.layout(), visible)

    def updateInputFieldsVisibility(self):
        is_geojson = self.importTypeComboBox.currentText() == "GeoJSON"
        is_stanet = self.importTypeComboBox.currentText() == "Stanet"

        # GeoJSON-spezifische Eingabefelder
        for input_layout in self.geojsonInputs:
            self.set_layout_visibility(input_layout, is_geojson)

        # Stanet-spezifische Eingabefelder
        for input_layout in self.stanetInputs:
            self.set_layout_visibility(input_layout, is_stanet)


        # Stanet-spezifische Eingabefelder
        for input_layout in self.stanetInputs:
            for i in range(input_layout.count()):
                widget = input_layout.itemAt(i).widget()
                if widget:
                    widget.setVisible(is_stanet)

        control_mode = self.temperatureControlInput.currentText()

        if control_mode == "Statisch":
            # Zeige die Widgets für Vorlauftemperatur (Index 0)
            for i in range(self.parameter_rows[0].count()):
                widget = self.parameter_rows[0].itemAt(i).widget()
                if widget:
                    widget.setVisible(True)
            
            # Blende die Widgets für Maximale Vorlauftemperatur, Minimale Vorlauftemperatur,
            # Obere Grenze der Lufttemperatur und Untere Grenze der Lufttemperatur (Index 1 bis 4) aus
            for parameter_row in self.parameter_rows[1:5]:
                for i in range(parameter_row.count()):
                    widget = parameter_row.itemAt(i).widget()
                    if widget:
                        widget.setVisible(False)

        elif control_mode == "Gleitend":
            # Blende die Widgets für Vorlauftemperatur (Index 0) aus
            for i in range(self.parameter_rows[0].count()):
                widget = self.parameter_rows[0].itemAt(i).widget()
                if widget:
                    widget.setVisible(False)

            # Zeige die Widgets für Maximale Vorlauftemperatur, Minimale Vorlauftemperatur,
            # Obere Grenze der Lufttemperatur und Untere Grenze der Lufttemperatur (Index 1 bis 4)
            for parameter_row in self.parameter_rows[1:5]:
                for i in range(parameter_row.count()):
                    widget = parameter_row.itemAt(i).widget()
                    if widget:
                        widget.setVisible(True)

    def selectFilename(self, line_edit):
        fname, _ = QFileDialog.getOpenFileName(self, 'Datei auswählen', '', 'All Files (*);;CSV Files (*.csv);;GeoJSON Files (*.geojson)')
        if fname:
            line_edit.setText(fname)

    def updateBuildingType(self):
        self.buildingTypeInput.clear()
        if self.calcMethodInput.currentText() == "VDI4655":
            self.buildingTypeInput.setDisabled(False)
            self.buildingTypeInput.addItems(["EFH", "MFH"])
        elif self.calcMethodInput.currentText() == "BDEW":
            self.buildingTypeInput.setDisabled(False)
            self.buildingTypeInput.addItems(["HEF", "HMF", "GKO", "GHA", "GMK", "GBD", "GBH", "GWA", "GGA", "GBA", "GGB", "GPD", "GMF", "GHD"])
        else:
            self.buildingTypeInput.setDisabled(True)

    def editHAST(self):
        hast_path = self.hastInput.itemAt(1).widget().text()  # Annahme: QLineEdit ist das zweite Widget im Layout
        if self.edit_hast_callback:
            self.edit_hast_callback(hast_path)

    def calculateTemperatureCurve(self):
        control_mode = self.temperatureControlInput.currentText()
        if control_mode == "Statisch":
            return float(self.parameter_rows[0].itemAt(1).widget().text())
        elif control_mode == "Gleitend":
            max_supply_temperature = float(self.parameter_rows[1].itemAt(1).widget().text())
            min_supply_temperature = float(self.parameter_rows[2].itemAt(1).widget().text())
            max_air_temperature = float(self.parameter_rows[3].itemAt(1).widget().text())
            min_air_temperature = float(self.parameter_rows[4].itemAt(1).widget().text())


            air_temperature_data = import_TRY("heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat")

            # Berechnung der Temperaturkurve basierend auf den ausgewählten Einstellungen
            temperature_curve = []

            # Berechnen der Steigung der linearen Gleichung
            slope = (max_supply_temperature - min_supply_temperature) / (min_air_temperature - max_air_temperature)

            for air_temperature in air_temperature_data:
                if air_temperature <= min_air_temperature:
                    temperature_curve.append(max_supply_temperature)
                elif air_temperature >= max_air_temperature:
                    temperature_curve.append(min_supply_temperature)
                else:
                    # Anwendung der linearen Gleichung für die Temperaturberechnung
                    temperature = max_supply_temperature + slope * (air_temperature - min_air_temperature)
                    temperature_curve.append(temperature)

            return np.array(temperature_curve)
        
    def generateNetwork(self):
        rl_temp = float(self.parameter_rows[5].itemAt(1).widget().text())
        supply_temperature = self.calculateTemperatureCurve()
        flow_pressure_pump = float(self.parameter_rows[6].itemAt(1).widget().text())
        lift_pressure_pump = float(self.parameter_rows[7].itemAt(1).widget().text())
        
        import_type = self.importTypeComboBox.currentText()
        if import_type == "GeoJSON":
            # Extrahiere GeoJSON-spezifische Daten
            vorlauf_path = self.vorlaufInput.itemAt(1).widget().text()
            ruecklauf_path = self.ruecklaufInput.itemAt(1).widget().text()
            hast_path = self.hastInput.itemAt(1).widget().text()
            erzeugeranlagen_path = self.erzeugeranlagenInput.itemAt(1).widget().text()

            calc_method = self.calcMethodInput.currentText()
            building_type = self.buildingTypeInput.currentText() if self.calcMethodInput.currentText() != "Datensatz" else "HMF"

            # Führen Sie die Netzgenerierung für GeoJSON durch
            if self.generate_callback:
                self.generate_callback(vorlauf_path, ruecklauf_path, hast_path, erzeugeranlagen_path, calc_method, building_type, rl_temp, supply_temperature, flow_pressure_pump, lift_pressure_pump, import_type)

        elif import_type == "Stanet":
            # Sammeln Sie den Dateipfad für Stanet und rufen Sie generate_callback auf
            stanet_csv = self.stanetInputs[0].itemAt(1).widget().text()
            # Hier können Sie Standardwerte oder vom Benutzer eingegebene Werte verwenden
            self.generate_callback(stanet_csv, rl_temp, supply_temperature, flow_pressure_pump, lift_pressure_pump, import_type)

        self.accept()

class SaveLoadNetDialog(QDialog):
    def __init__(self, net_data, parent=None):
        super().__init__(parent)
        self.net_data = net_data
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        save_button = QPushButton("Netz speichern", self)
        load_button = QPushButton("Netz laden", self)

        layout.addWidget(save_button)
        layout.addWidget(load_button)

        save_button.clicked.connect(self.saveNet)
        load_button.clicked.connect(self.loadNet)

    def saveNet(self):
        if self.net_data:  # Überprüfe, ob das Netzwerk vorhanden ist
            net, yearly_time_steps, waerme_ges_W = self.net_data
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "Pandapipes-Netz als JSON speichern", "", "JSON Files (*.json)", options=options)
            if file_name:
                # Überführe Fluid-Objekte in JSON-serialisierbaren Zustand
                net_fluid_data = {}
                for fluid_name, fluid_obj in net.fluid.items():
                    fluid_data = {
                        "name": fluid_obj.name,
                        "temperature": fluid_obj.temperature,
                        # Füge weitere Attribute hinzu, die du benötigst
                    }
                    net_fluid_data[fluid_name] = fluid_data

                # Erstelle ein Dictionary, das die Daten enthält
                saved_data = {
                    "net_fluid_data": net_fluid_data,
                    "yearly_time_steps": yearly_time_steps,
                    "waerme_ges_W": waerme_ges_W
                }

                # Speichere das Dictionary im JSON-Format
                with open(file_name, "w") as json_file:
                    json.dump(saved_data, json_file, indent=2)
                print("Pandapipes-Netz erfolgreich gespeichert als JSON:", file_name)
        else:
            print("Kein Pandapipes-Netzwerk zum Speichern vorhanden.")

    def loadNet(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Netz laden", "", "JSON Files (*.json)", options=options)
        if file_name and os.path.isfile(file_name):
            # Lade das JSON-Datei in ein Dictionary
            with open(file_name, "r") as json_file:
                loaded_data = json.load(json_file)

            if loaded_data:
                # Extrahiere die Fluid-Objekte aus dem geladenen JSON-Daten
                loaded_net_fluid_data = loaded_data.get("net_fluid_data", {})
                # Erstelle Fluid-Objekte aus den geladenen Daten
                loaded_net_fluids = {}
                for fluid_name, fluid_data in loaded_net_fluid_data.items():
                    fluid_obj = pp.fluid.Fluid(
                        name=fluid_data["name"],
                        temperature=fluid_data["temperature"],
                        # Füge weitere Attribute hinzu, die du benötigst
                    )
                    loaded_net_fluids[fluid_name] = fluid_obj

                # Extrahiere die übrigen Daten aus dem geladenen JSON-Daten
                loaded_yearly_time_steps = loaded_data.get("yearly_time_steps")
                loaded_waerme_ges_W = loaded_data.get("waerme_ges_W")

                # Aktualisiere die net_data-Variable mit den geladenen Daten
                self.net_data = (loaded_net_fluids, loaded_yearly_time_steps, loaded_waerme_ges_W)
                # Führen Sie die erforderlichen Aktionen für das geladene Netzwerk aus
                # Zum Beispiel: Aktualisieren Sie die Ansicht des Netzwerks
                print("Netz erfolgreich geladen.")