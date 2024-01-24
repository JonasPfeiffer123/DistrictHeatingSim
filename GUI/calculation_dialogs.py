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

class GeojsonDialog(QDialog):
    def __init__(self, generate_callback, edit_hast_callback, import_layers_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Netz aus GeoJSON generieren")
        self.generate_callback = generate_callback
        self.edit_hast_callback = edit_hast_callback
        self.import_layers_callback = import_layers_callback
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Standardpfade
        default_paths = {
            'Erzeugeranlagen': 'net_generation/Erzeugeranlagen.geojson',
            'HAST': 'net_generation/HAST.geojson',
            'Vorlauf': 'net_generation/Vorlauf.geojson',
            'Rücklauf': 'net_generation/Rücklauf.geojson'
        }

        # Eingabefelder und Dateiauswahl-Buttons
        self.vorlaufInput = self.createFileInput("Vorlauf GeoJSON:", default_paths['Vorlauf'])
        self.ruecklaufInput = self.createFileInput("Rücklauf GeoJSON:", default_paths['Rücklauf'])
        self.hastInput = self.createFileInput("HAST GeoJSON:", default_paths['HAST'])
        self.erzeugeranlagenInput = self.createFileInput("Erzeugeranlagen GeoJSON:", default_paths['Erzeugeranlagen'])

        layout.addLayout(self.vorlaufInput)
        layout.addLayout(self.ruecklaufInput)
        layout.addLayout(self.hastInput)
        layout.addLayout(self.erzeugeranlagenInput)

        # Hinzufügen der Berechnungsmethoden-Auswahl
        self.calcMethodInput = QComboBox(self)
        self.calcMethodInput.addItems(["Datensatz", "BDEW", "VDI4655"])
        layout.addWidget(QLabel("Berechnungsmethode:"))
        layout.addWidget(self.calcMethodInput)

        # Hinzufügen der Gebäudetypen-Auswahl
        self.buildingTypeInput = QComboBox(self)
        layout.addWidget(QLabel("Gebäudetyp:"))
        layout.addWidget(self.buildingTypeInput)
        self.updateBuildingType()  # Initialisiert die Gebäudetypen basierend auf der Berechnungsmethode

        self.calcMethodInput.currentIndexChanged.connect(self.updateBuildingType)

        # Button für "Hausanschlussstationen bearbeiten"
        self.editHASTButton = QPushButton("Hausanschlussstationen bearbeiten", self)
        self.editHASTButton.clicked.connect(self.editHAST)
        layout.addWidget(self.editHASTButton)

        # Button für "Layers in Karte importieren"
        self.importLayersButton = QPushButton("Layers in Karte importieren", self)
        self.importLayersButton.clicked.connect(self.importLayers)
        layout.addWidget(self.importLayersButton)

        # Hinzufügen der Temperaturvorgabe-Auswahl
        self.temperatureControlInput = QComboBox(self)
        self.temperatureControlInput.addItems(["Statisch", "Gleitend"])
        layout.addWidget(QLabel("Vorlauftemperatur-Regelung:"))
        layout.addWidget(self.temperatureControlInput)
        self.temperatureControlInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)

        # Hinzufügen zusätzlicher Eingabefelder für die neuen Parameter
        # Statisch VL
        self.supplyTemperatureInput = QLineEdit("85")
        layout.addWidget(QLabel("Vorlauftemperatur:"))
        layout.addWidget(self.supplyTemperatureInput)

        # Gleitend VL
        self.maxSupplyTemperatureInput = QLineEdit("85")
        layout.addWidget(QLabel("Maximale Vorlauftemperatur:"))
        layout.addWidget(self.maxSupplyTemperatureInput)

        self.minSupplyTemperatureInput = QLineEdit("70")
        layout.addWidget(QLabel("Minimale Vorlauftemperatur:"))
        layout.addWidget(self.minSupplyTemperatureInput)

        self.maxAirTemperatureInput = QLineEdit("15")
        layout.addWidget(QLabel("Obere Grenze der Lufttemperatur:"))
        layout.addWidget(self.maxAirTemperatureInput)

        self.minAirTemperatureInput = QLineEdit("-10")
        layout.addWidget(QLabel("Untere Grenze der Lufttemperatur:"))
        layout.addWidget(self.minAirTemperatureInput)

        # RL
        self.returnTemperatureInput = QLineEdit("60")
        layout.addWidget(QLabel("Rücklauftemperatur:"))
        layout.addWidget(self.returnTemperatureInput)

        self.flowPressureInput = QLineEdit("4")
        layout.addWidget(QLabel("Vorlaufdruck:"))
        layout.addWidget(self.flowPressureInput)
        
        self.liftPressureInput = QLineEdit("1.5")
        layout.addWidget(QLabel("Druckdifferenz Vorlauf/Rücklauf:"))
        layout.addWidget(self.liftPressureInput)

        # Button zum Starten der Netzgenerierung
        self.generateButton = QPushButton("Netz generieren", self)
        self.generateButton.clicked.connect(self.generateNetwork)
        layout.addWidget(self.generateButton)

        self.updateInputFieldsVisibility()

    def updateInputFieldsVisibility(self):
        control_mode = self.temperatureControlInput.currentText()

        # Zeige alle Eingabefelder an
        self.supplyTemperatureInput.setVisible(True)
        self.maxSupplyTemperatureInput.setVisible(True)
        self.minSupplyTemperatureInput.setVisible(True)
        self.maxAirTemperatureInput.setVisible(True)
        self.minAirTemperatureInput.setVisible(True)

        # Blende nicht benötigte Eingabefelder basierend auf der ausgewählten Methode aus
        if control_mode == "Statisch":
            self.maxSupplyTemperatureInput.setVisible(False)
            self.minSupplyTemperatureInput.setVisible(False)
            self.maxAirTemperatureInput.setVisible(False)
            self.minAirTemperatureInput.setVisible(False)

        elif control_mode == "Gleitend":
            self.supplyTemperatureInput.setVisible(False)

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

    def selectFilename(self, line_edit):
        fname, _ = QFileDialog.getOpenFileName(self, 'Datei auswählen', '', 'GeoJSON Files (*.geojson);;All Files (*)')
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

    def importLayers(self):
        if self.import_layers_callback:
            self.import_layers_callback(
                self.vorlaufInput.itemAt(1).widget().text(),
                self.ruecklaufInput.itemAt(1).widget().text(),
                self.hastInput.itemAt(1).widget().text(),
                self.erzeugeranlagenInput.itemAt(1).widget().text()
            )

    def calculateTemperatureCurve(self):
        control_mode = self.temperatureControlInput.currentText()
        if control_mode == "Statisch":
            return float(self.supplyTemperatureInput.text())
        elif control_mode == "Gleitend":
            max_supply_temperature = float(self.maxSupplyTemperatureInput.text())
            min_supply_temperature = float(self.minSupplyTemperatureInput.text())
            max_air_temperature = float(self.maxAirTemperatureInput.text())
            min_air_temperature = float(self.minAirTemperatureInput.text())

            air_temperature_data = import_TRY("heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat")

            # Berechnung der Temperaturkurve basierend auf den ausgewählten Einstellungen
            temperature_curve = []

            for air_temperature in air_temperature_data:
                if air_temperature < min_air_temperature:
                    temperature_curve.append(max_supply_temperature)
                elif air_temperature > max_air_temperature:
                    temperature_curve.append(min_supply_temperature)
                else:
                    # Lineare Anpassung zwischen min_supply_temperature und max_supply_temperature
                    temperature_range = max_air_temperature - min_air_temperature
                    temperature_ratio = (air_temperature - min_air_temperature) / temperature_range
                    temperature = min_supply_temperature + temperature_ratio * (max_supply_temperature - min_supply_temperature)
                    temperature_curve.append(temperature)

            return np.array(temperature_curve)
    
    def generateNetwork(self):
        if self.generate_callback:
            self.generate_callback(
                self.vorlaufInput.itemAt(1).widget().text(),
                self.ruecklaufInput.itemAt(1).widget().text(),
                self.hastInput.itemAt(1).widget().text(),
                self.erzeugeranlagenInput.itemAt(1).widget().text(),
                self.calcMethodInput.currentText(),
                self.buildingTypeInput.currentText() if self.calcMethodInput.currentText() != "Datensatz" else None,
                float(self.returnTemperatureInput.text()),
                self.calculateTemperatureCurve(),
                float(self.flowPressureInput.text()),
                float(self.liftPressureInput.text())
            )
        self.accept()

class StanetDialog(QDialog):
    def __init__(self, generate_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Netz aus Stanet-CSV generieren")
        self.generate_callback = generate_callback
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Standardpfad
        default_path = "net_simulation_pandapipes/stanet files/Beleg_1/Beleg_1.CSV"

        # Eingabefeld und Dateiauswahl-Button
        self.stanetCsvInputLayout = self.createFileInput("Stanet CSV:", default_path)
        layout.addLayout(self.stanetCsvInputLayout)

        # Button zum Starten der Netzgenerierung
        self.generateButton = QPushButton("Netz generieren", self)
        self.generateButton.clicked.connect(self.generateNetwork)
        layout.addWidget(self.generateButton)

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

    def selectFilename(self, line_edit):
        fname, _ = QFileDialog.getOpenFileName(self, 'Datei auswählen', '', 'CSV Files (*.csv);;All Files (*)')
        if fname:
            line_edit.setText(fname)

    def generateNetwork(self):
        if self.generate_callback:
            self.generate_callback(self.stanetCsvInputLayout.itemAt(1).widget().text())
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