"""
Filename: calculation_dialogs.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-30
Description: Contains the Dialogs for the CalculationTab.
"""

import os
import sys

import numpy as np
import geopandas as gpd

from shapely import Point

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, QComboBox, QWidget, QScrollArea, \
    QPushButton, QHBoxLayout, QFileDialog, QCheckBox, QMessageBox, QGroupBox

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import pandapipes as pp

from heat_requirement.heat_requirement_BDEW import import_TRY

def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, relative_path)

class NetGenerationDialog(QDialog):
    def __init__(self, generate_callback, base_path, parent=None):
        super().__init__(parent)
        self.generate_callback = generate_callback
        self.base_path = base_path
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Netz generieren")
        self.resize(1400, 1000)

        main_layout = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QHBoxLayout(scroll_content)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Erste Layout-Spalte
        left_layout = QVBoxLayout()

        # Import-Bereich
        importGroup = QGroupBox("Import Netzdaten und Wärmebedarfsrechnung")
        importGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")  # Setzt die Schriftgröße und macht den Text fett
        importLayout = QVBoxLayout()
        importLayout.addWidget(QLabel("Importtyp Netz:"))
        self.importTypeComboBox = QComboBox()
        self.importTypeComboBox.addItems(["GeoJSON"])
        importLayout.addWidget(self.importTypeComboBox)
        self.importTypeComboBox.currentIndexChanged.connect(self.updateInputFieldsVisibility)

        # Dynamische Eingabefelder hinzufügen
        self.geojsonInputs = self.createGeojsonInputs()
        for input_layout in self.geojsonInputs:
            importLayout.addLayout(input_layout)

        # JSON Eingabe
        jsonImportLayout = QHBoxLayout()
        jsonLabel = QLabel("JSON mit Daten:")
        jsonImportLayout.addWidget(jsonLabel)
        self.jsonLineEdit = QLineEdit(f"{self.base_path}/Lastgang/Gebäude Lastgang.json")
        jsonImportLayout.addWidget(self.jsonLineEdit)
        jsonBrowseButton = QPushButton("Datei auswählen")
        jsonBrowseButton.clicked.connect(self.browseJsonFile)
        jsonImportLayout.addWidget(jsonBrowseButton)
        importLayout.addLayout(jsonImportLayout)

        importGroup.setLayout(importLayout)
        left_layout.addWidget(importGroup)

        # Netzkonfiguration und Temperatursteuerung
        netConfigGroup = QGroupBox("Netzkonfiguration und Temperatursteuerung")
        netConfigGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")  # Setzt die Schriftgröße und macht den Text fett
        netConfigLayout = QVBoxLayout()
        netConfigLayout.addLayout(self.createNetconfigurationControlInput())
        netConfigLayout.addLayout(self.createTemperatureControlInput())
        netConfigLayout.addLayout(self.createNetParameterInputs())
        netConfigLayout.addLayout(self.createSupplyTemperatureCheckbox())
        netConfigLayout.addLayout(self.createReturnTemperatureCheckbox())
        netConfigLayout.addLayout(self.createHeatConsumerParameterInputs())
        netConfigLayout.addLayout(self.createBuildingTemperatureCheckbox())
        netConfigLayout.addLayout(self.createinitialpipetypeInput())
        netConfigGroup.setLayout(netConfigLayout)
        left_layout.addWidget(netConfigGroup)

        # Netz generieren Button
        self.generateButton = QPushButton("Netz generieren")
        self.generateButton.clicked.connect(self.generateNetwork)
        left_layout.addWidget(self.generateButton)

        # Zweite Layout-Spalte
        right_layout = QVBoxLayout()

        # Einstellungen Durchmesseroptimierung
        OptDiameterGroup = QGroupBox("Durchmesseroptimierung im Netz")
        OptDiameterGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")  # Setzt die Schriftgröße und macht den Text fett
        OptDiameterLayout = QVBoxLayout()
        OptDiameterLayout.addLayout(self.createDiameterOptCheckbox())
        OptDiameterLayout.addLayout(self.createDiameterOptInput())
        OptDiameterGroup.setLayout(OptDiameterLayout)
        right_layout.addWidget(OptDiameterGroup)

        DiagramsGroup = QGroupBox("Vorschau Netz und zeitlicher Verlauf")
        DiagramsGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")  # Setzt die Schriftgröße und macht den Text fett
        DiagramsLayout = QVBoxLayout()

        self.figure1 = Figure()
        self.canvas1 = FigureCanvas(self.figure1)
        self.canvas1.setMinimumSize(350, 350)  # Setze eine Mindestgröße für die Canvas
        self.toolbar1 = NavigationToolbar(self.canvas1, self)

        self.figure2 = Figure()
        self.canvas2 = FigureCanvas(self.figure2)
        self.canvas2.setMinimumSize(350, 350)  # Setze eine Mindestgröße für die Canvas
        self.toolbar2 = NavigationToolbar(self.canvas2, self)

        DiagramsLayout.addWidget(self.canvas1)
        DiagramsLayout.addWidget(self.toolbar1)
        DiagramsLayout.addWidget(self.canvas2)
        DiagramsLayout.addWidget(self.toolbar2)

        DiagramsGroup.setLayout(DiagramsLayout)
        right_layout.addWidget(DiagramsGroup)

        # Hauptlayout anpassen
        scroll_layout.addLayout(left_layout)
        scroll_layout.addLayout(right_layout)

        # Update der Sichtbarkeit
        self.updateInputFieldsVisibility()
        self.update_plot()

    def createGeojsonInputs(self):
        default_paths = {
            'Erzeugeranlagen': f'{self.base_path}\Wärmenetz\Erzeugeranlagen.geojson',
            'HAST': f'{self.base_path}\Wärmenetz\HAST.geojson',
            'Vorlauf': f'{self.base_path}\Wärmenetz\Vorlauf.geojson',
            'Rücklauf': f'{self.base_path}\Wärmenetz\Rücklauf.geojson'
        }

        file_inputs_layout = self.createFileInputsGeoJSON(default_paths)

        inputs = [
            file_inputs_layout
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
    
    def browseJsonFile(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Select JSON File', f"{self.base_path}/Lastgang", 'JSON Files (*.json);;All Files (*)')
        if fname:
            self.jsonLineEdit.setText(fname)
    
    def createNetconfigurationControlInput(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Netzkonfiguration:"))
        self.netconfigurationControlInput = QComboBox(self)
        self.netconfigurationControlInput.addItems(["Niedertemperaturnetz", "kaltes Netz"])#, "wechselwarmes Netz"])
        layout.addWidget(self.netconfigurationControlInput)
        self.netconfigurationControlInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)
        return layout
    
    def createTemperatureControlInput(self):
        layout = QVBoxLayout()
        self.temperatureControlInput = QComboBox(self)
        self.temperatureControlInput.addItems(["Gleitend", "Statisch"])
        layout.addWidget(QLabel("Vorlauftemperatur-Regelung:"))
        layout.addWidget(self.temperatureControlInput)
        self.temperatureControlInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)
        return layout
    
    def createSupplyTemperatureCheckbox(self):
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Temperaturregelung HAST:"))

        self.supplyTempCheckbox = QCheckBox("Mindestvorlauftemperatur für die Gebäude berücksichtigen.")
        self.supplyTempCheckbox.setToolTip("""Aktivieren Sie diese Option, um eine Mindestvorlauftemperatur für alle Gebäude festzulegen.\nDas können beispielsweise 60 °C sein um die Warmwasserbereitung zu gewährleisten.\nÜber die Temperaturdifferenz zwischen HAST und Netz ergibt sich dann eine Mindestvorlauftemperatur welche in der Simulation erreicht werden muss.\nWenn nicht definiert, wird keine Mindesttemperatur berücksichtigt.""")  # Tooltip hinzufügen
        layout.addWidget(self.supplyTempCheckbox)

        # Verbinde das stateChanged Signal der Checkbox mit der update-Methode
        self.supplyTempCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)
        
        return layout

    def createReturnTemperatureCheckbox(self):
        layout = QVBoxLayout()

        self.returnTempCheckbox = QCheckBox("Rücklauftemperatur für alle HA-Stationen festlegen.")
        self.returnTempCheckbox.setToolTip("""Aktivieren Sie diese Option, um die Rücklauftemperatur für alle HA-Stationen zentral festzulegen.\nStandardmäßig erfolgt die Berechung der Rücklauftemperaturen der HA-Station aus den Rücklauftemperaturen der Gebäude sowie der vorgegebenen Temperaturdifferenz zwischen Netz und HAST.""")  # Tooltip hinzufügen
        layout.addWidget(self.returnTempCheckbox)

        # Verbinde das stateChanged Signal der Checkbox mit der update-Methode
        self.returnTempCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)
        
        return layout
    
    def createBuildingTemperatureCheckbox(self):
        layout = QVBoxLayout()
        self.buildingTempCheckbox = QCheckBox("Gebäudeheizungstemperaturen im zeitlichen Verlauf berücksichtigen.")
        self.buildingTempCheckbox.setToolTip("""Aktivieren Sie diese Option, um die Vor- und Rücklauftemperaturen in den Gebäuden mittels Temperaturregelung entsprechend der definierten Temperaturen und der Steigung in Abhängigkeit der Außentemperatur zu berechnen.\nIst eine Mindestvorlauftemperatur vorgegeben wird diese berücksichtigt.\nDie vorgabe einer zentralen Rücklauftemperatur ergibt nur bei einem kalten Netz Sinn.""")  # Tooltip hinzufügen
        layout.addWidget(self.buildingTempCheckbox)

        # Verbinde das stateChanged Signal der Checkbox mit der update-Methode
        self.buildingTempCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)
        
        return layout

    def createNetParameterInputs(self):
        layout = QVBoxLayout()
        self.parameter_rows_net = []

        # Parameterzeile für Vorlauftemperatur
        self.supply_temp_row = self.createParameterRow("Vorlauftemperatur Heizzentrale:", "85")
        self.parameter_rows_net.append(self.supply_temp_row)
        layout.addLayout(self.supply_temp_row)

        # Parameterzeile für Maximale Vorlauftemperatur
        self.max_supply_temp_row = self.createParameterRow("Maximale Vorlauftemperatur Heizzentrale:", "85")
        self.parameter_rows_net.append(self.max_supply_temp_row)
        layout.addLayout(self.max_supply_temp_row)

        # Parameterzeile für Minimale Vorlauftemperatur
        self.min_supply_temp_row = self.createParameterRow("Minimale Vorlauftemperatur Heizzentrale:", "70")
        self.parameter_rows_net.append(self.min_supply_temp_row)
        layout.addLayout(self.min_supply_temp_row)

        # Parameterzeile für Obere Grenze der Lufttemperatur
        self.max_air_temp_row = self.createParameterRow("Obere Grenze der Lufttemperatur:", "15")
        self.parameter_rows_net.append(self.max_air_temp_row)
        layout.addLayout(self.max_air_temp_row)

        # Parameterzeile für Untere Grenze der Lufttemperatur
        self.min_air_temp_row = self.createParameterRow("Untere Grenze der Lufttemperatur:", "-10")
        self.parameter_rows_net.append(self.min_air_temp_row)
        layout.addLayout(self.min_air_temp_row)

        layout.addWidget(QLabel("Druckregelung Heizzentrale:"))

        # Parameterzeile für Vorlaufdruck
        self.flow_pressure_row = self.createParameterRow("Vorlaufdruck:", "4")
        self.parameter_rows_net.append(self.flow_pressure_row)
        layout.addLayout(self.flow_pressure_row)

        # Parameterzeile für Druckdifferenz Vorlauf/Rücklauf
        lift_pressure_row = self.createParameterRow("Druckdifferenz Vorlauf/Rücklauf:", "1.5")
        self.parameter_rows_net.append(lift_pressure_row)
        layout.addLayout(lift_pressure_row)

        return layout
    
    def createHeatConsumerParameterInputs(self):
        layout = QVBoxLayout()
        self.parameter_rows_heat_consumer = []

        # Parameterzeile für Rücklauftemperatur
        self.supply_temperature_heat_consumer_row = self.createParameterRow("Minimale Vorlauftemperatur Gebäude:", "60")
        self.parameter_rows_heat_consumer.append(self.supply_temperature_heat_consumer_row)
        layout.addLayout(self.supply_temperature_heat_consumer_row)

        # Parameterzeile für Rücklauftemperatur
        self.return_temp_row = self.createParameterRow("Soll-Rücklauftemperatur HAST:", "50")
        self.parameter_rows_heat_consumer.append(self.return_temp_row)
        layout.addLayout(self.return_temp_row)

        # Parameterzeile für Temperaturdifferenz Netz/HAST
        dT_RL = self.createParameterRow("Temperaturdifferenz Netz/HAST:", "5")
        self.parameter_rows_heat_consumer.append(dT_RL)
        layout.addLayout(dT_RL)

        return layout

    def createParameterRow(self, label_text, default_text):
        row_layout = QHBoxLayout()
        label = QLabel(label_text)
        line_edit = QLineEdit(default_text)
        row_layout.addWidget(label)
        row_layout.addWidget(line_edit)
        return row_layout
    
    def createDiameterOptCheckbox(self):
        layout = QVBoxLayout()
        self.DiameterOptCheckbox = QCheckBox("Durchmesser optimieren.")
        layout.addWidget(self.DiameterOptCheckbox)

        # Setze die Checkbox bei der Initialisierung als ausgewählt
        self.DiameterOptCheckbox.setChecked(True)

        # Verbinde das stateChanged Signal der Checkbox mit der update-Methode
        self.DiameterOptCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)

        return layout

    def createinitialpipetypeInput(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Rohrtyp zur Initialisierung des Netzes:"))
        self.initialpipetypeInput = QComboBox(self)
        pipetypes = pp.std_types.available_std_types(pp.create_empty_network(fluid="water"), "pipe").index.tolist()
        self.initialpipetypeInput.addItems(pipetypes)
        layout.addWidget(self.initialpipetypeInput)
        
        # Setze einen Startwert
        default_pipe_type = "KMR 100/250-2v"  # Ersetzen Sie "Ihr Startwert" mit dem tatsächlichen Wert
        if default_pipe_type in pipetypes:
            self.initialpipetypeInput.setCurrentText(default_pipe_type)
        else:
            print(f"Warnung: Startwert '{default_pipe_type}' nicht in der Liste der Rohrtypen gefunden.")

        return layout
    
    def createDiameterOptInput(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Eingaben zur Durchmesseroptimierung der Rohrleitungen:"))

        row_layout = QHBoxLayout()
        self.v_max_pipelabel = QLabel("Maximale Strömungsgeschwindigkeit Leitungen:")
        self.v_max_pipeInput = QLineEdit("1.0")
        row_layout.addWidget(self.v_max_pipelabel)
        row_layout.addWidget(self.v_max_pipeInput)
        layout.addLayout(row_layout)

        self.v_max_heat_consumerLabel = QLabel("Maximale Strömungsgeschwindigkeit HAST:")
        self.v_max_heat_consumerInput = QLineEdit("1.5")
        row_layout.addWidget(self.v_max_heat_consumerLabel)
        row_layout.addWidget(self.v_max_heat_consumerInput)
        layout.addLayout(row_layout)

        self.material_filterInput = QComboBox(self)
        self.material_filterInput.addItems(["KMR", "FL", "HK"])
        layout.addWidget(self.material_filterInput)
        self.material_filterInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)

        self.insulation_filterInput = QComboBox(self)
        self.insulation_filterInput.addItems(["2v", "1v", "S"])
        layout.addWidget(self.insulation_filterInput)
        self.insulation_filterInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)
    
        return layout

    def set_layout_visibility(self, layout, visible):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.setVisible(visible)
            elif item.layout():
                self.set_layout_visibility(item.layout(), visible)

    def set_default_value(self, parameter_row, value):
        # Zugriff auf das QLineEdit Widget in der Parameterzeile und Aktualisieren des Textes
        for i in range(parameter_row.count()):
            widget = parameter_row.itemAt(i).widget()
            if isinstance(widget, QLineEdit):
                widget.setText(value)
                break  # Beendet die Schleife, sobald das QLineEdit gefunden und aktualisiert wurde

    def updateInputFieldsVisibility(self):
        is_geojson = self.importTypeComboBox.currentText() == "GeoJSON"

        # GeoJSON-spezifische Eingabefelder
        for input_layout in self.geojsonInputs:
            self.set_layout_visibility(input_layout, is_geojson)

        self.netconfiguration = self.netconfigurationControlInput.currentText()
        is_low_temp_net = self.netconfigurationControlInput.currentText() == "Niedertemperaturnetz"
        #is_changing_temp_net = self.netconfigurationControlInput.currentText() == "wechselwarmes Netz"
        is_cold_temp_net = self.netconfigurationControlInput.currentText() == "kaltes Netz"

        if is_low_temp_net:
            # Setze neue Standardwerte für das Niedertemperaturnetz
            self.set_default_value(self.supply_temp_row, "85")
            self.set_default_value(self.max_supply_temp_row, "85")
            self.set_default_value(self.min_supply_temp_row, "70")
            self.set_default_value(self.return_temp_row, "60")

        elif is_cold_temp_net:
            # Setze neue Standardwerte für das kalte Netz
            self.set_default_value(self.supply_temp_row, "10")
            self.set_default_value(self.max_supply_temp_row, "10")
            self.set_default_value(self.min_supply_temp_row, "5")
            self.set_default_value(self.return_temp_row, "3")

        """elif is_changing_temp_net:
            # Setze neue Standardwerte für das wechselwarme Netz
            self.set_default_value(self.supply_temp_row, "45")
            self.set_default_value(self.max_supply_temp_row, "45")
            self.set_default_value(self.min_supply_temp_row, "30")
            self.set_default_value(self.return_temp_row, "20")"""

        is_control_mode_static = self.temperatureControlInput.currentText() == "Statisch"
        is_control_mode_dynamic = self.temperatureControlInput.currentText() == "Gleitend"

        if is_control_mode_static:
            # Zeige die Widgets für Vorlauftemperatur (Index 0)
            for i in range(self.parameter_rows_net[0].count()):
                widget = self.parameter_rows_net[0].itemAt(i).widget()
                if widget:
                    widget.setVisible(True)
            
            # Blende die Widgets für Maximale Vorlauftemperatur, Minimale Vorlauftemperatur,
            # Obere Grenze der Lufttemperatur und Untere Grenze der Lufttemperatur (Index 1 bis 4) aus
            for parameter_row in self.parameter_rows_net[1:5]:
                for i in range(parameter_row.count()):
                    widget = parameter_row.itemAt(i).widget()
                    if widget:
                        widget.setVisible(False)

        elif is_control_mode_dynamic:
            # Blende die Widgets für Vorlauftemperatur (Index 0) aus
            for i in range(self.parameter_rows_net[0].count()):
                widget = self.parameter_rows_net[0].itemAt(i).widget()
                if widget:
                    widget.setVisible(False)

            # Zeige die Widgets für Maximale Vorlauftemperatur, Minimale Vorlauftemperatur,
            # Obere Grenze der Lufttemperatur und Untere Grenze der Lufttemperatur (Index 1 bis 4)
            for parameter_row in self.parameter_rows_net[1:5]:
                for i in range(parameter_row.count()):
                    widget = parameter_row.itemAt(i).widget()
                    if widget:
                        widget.setVisible(True)
        
        self.DiameterOpt_ckecked = self.DiameterOptCheckbox.isChecked()

        # Anzeige Optimierungsoptionen
        self.v_max_pipelabel.setVisible(self.DiameterOpt_ckecked)
        self.v_max_pipeInput.setVisible(self.DiameterOpt_ckecked)

        self.v_max_heat_consumerLabel.setVisible(self.DiameterOpt_ckecked)
        self.v_max_heat_consumerInput.setVisible(self.DiameterOpt_ckecked)

        self.material_filterInput.setVisible(self.DiameterOpt_ckecked)
        self.insulation_filterInput.setVisible(self.DiameterOpt_ckecked)

        self.insulation_filterInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)

        self.supply_temperature_heat_consumer_checked = self.supplyTempCheckbox.isChecked()
        self.set_layout_visibility(self.supply_temperature_heat_consumer_row, self.supply_temperature_heat_consumer_checked)

        self.return_temp_checked = self.returnTempCheckbox.isChecked()
        self.set_layout_visibility(self.return_temp_row, self.return_temp_checked)

        self.building_temp_checked =  self.buildingTempCheckbox.isChecked()

    def selectFilename(self, line_edit):
        fname, _ = QFileDialog.getOpenFileName(self, 'Datei auswählen', '', 'All Files (*);;CSV Files (*.csv);;GeoJSON Files (*.geojson)')
        if fname:
            line_edit.setText(fname)
            self.update_plot()

    ### Hier vielleicht noch Funktionalitäten auslagern
    def calculateTemperatureCurve(self):
        control_mode = self.temperatureControlInput.currentText()
        if control_mode == "Statisch":
            return float(self.parameter_rows_net[0].itemAt(1).widget().text())
        elif control_mode == "Gleitend":
            max_supply_temperature = float(self.parameter_rows_net[1].itemAt(1).widget().text())
            min_supply_temperature = float(self.parameter_rows_net[2].itemAt(1).widget().text())
            max_air_temperature = float(self.parameter_rows_net[3].itemAt(1).widget().text())
            min_air_temperature = float(self.parameter_rows_net[4].itemAt(1).widget().text())

            air_temperature_data = import_TRY(self.parent.parent.try_filename)

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

    def update_plot(self):
        try:
            # Pfade auslesen
            vorlauf_path = self.vorlaufInput.itemAt(1).widget().text()
            ruecklauf_path = self.ruecklaufInput.itemAt(1).widget().text()
            hast_path = self.hastInput.itemAt(1).widget().text()
            erzeugeranlagen_path = self.erzeugeranlagenInput.itemAt(1).widget().text()

            # Dateien einlesen
            vorlauf = gpd.read_file(vorlauf_path)
            ruecklauf = gpd.read_file(ruecklauf_path)
            hast = gpd.read_file(hast_path)
            erzeugeranlagen = gpd.read_file(erzeugeranlagen_path)

            # Plot vorbereiten
            self.figure1.clear()
            ax = self.figure1.add_subplot(111)
            vorlauf.plot(ax=ax, color='red')
            ruecklauf.plot(ax=ax, color='blue')
            hast.plot(ax=ax, color='green')
            erzeugeranlagen.plot(ax=ax, color='black')

            # Annotations vorbereiten
            annotations = []
            for idx, row in hast.iterrows():
                point = row['geometry'].representative_point()
                label = f"{row['Adresse']}\nWärmebedarf: {row['Wärmebedarf']}\nGebäudetyp: {row['Gebäudetyp']}\nVLT_max:{row['VLT_max']}\nRLT_max:{row['RLT_max']}"
                annotation = ax.annotate(label, xy=(point.x, point.y), xytext=(10, 10),
                                        textcoords="offset points", bbox=dict(boxstyle="round", fc="w"))
                annotation.set_visible(False)
                annotations.append((point, annotation))

            # Event-Handler definieren
            def on_move(event):
                if event.xdata is None or event.ydata is None:
                    return

                visibility_changed = False
                for point, annotation in annotations:
                    should_be_visible = (point.distance(Point(event.xdata, event.ydata)) < 5)

                    if should_be_visible != annotation.get_visible():
                        visibility_changed = True
                        annotation.set_visible(should_be_visible)

                if visibility_changed:
                    self.canvas1.draw()

            # Maus-Bewegung-Event verbinden
            self.figure1.canvas.mpl_connect('motion_notify_event', on_move)

            ax.set_title('Visualisierung der GeoJSON-Netz-Daten')
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')

        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ein Fehler ist aufgetreten")
            msg.setInformativeText(str(e))
            msg.setWindowTitle("Fehler")
            msg.exec_()

    def generateNetwork(self):
        import_type = self.importTypeComboBox.currentText()
        if import_type == "GeoJSON":
            # Extrahiere GeoJSON-spezifische Daten
            vorlauf_path = self.vorlaufInput.itemAt(1).widget().text()
            ruecklauf_path = self.ruecklaufInput.itemAt(1).widget().text()
            hast_path = self.hastInput.itemAt(1).widget().text()
            erzeugeranlagen_path = self.erzeugeranlagenInput.itemAt(1).widget().text()

            json_path = self.jsonLineEdit.text()

            v_max_heat_consumer  = float(self.v_max_heat_consumerInput.text())
            pipetype = self.initialpipetypeInput.currentText()

            v_max_pipe = float(self.v_max_pipeInput.text())
            material_filter = self.material_filterInput.currentText()
            insulation_filter = self.insulation_filterInput.currentText()

        supply_temperature_net = self.calculateTemperatureCurve()
        flow_pressure_pump = float(self.parameter_rows_net[5].itemAt(1).widget().text())
        lift_pressure_pump = float(self.parameter_rows_net[6].itemAt(1).widget().text())

        if self.supply_temperature_heat_consumer_checked == True:
            supply_temperature_heat_consumer = float(self.parameter_rows_heat_consumer[0].itemAt(1).widget().text())
        else:
            supply_temperature_heat_consumer = None  
              
        if self.return_temp_checked == True:
            rl_temp_heat_consumer = float(self.parameter_rows_heat_consumer[1].itemAt(1).widget().text())
        else:
            rl_temp_heat_consumer = None

        dT_RL = float(self.parameter_rows_heat_consumer[2].itemAt(1).widget().text())
        
        ### hier muss der path für die JSON mit den Lastgängen ergänzt werden ###
        # Führen Sie die Netzgenerierung für GeoJSON durch
        if self.generate_callback:
            self.generate_callback(vorlauf_path, ruecklauf_path, hast_path, erzeugeranlagen_path, json_path, rl_temp_heat_consumer, 
                                   supply_temperature_heat_consumer, supply_temperature_net, flow_pressure_pump, lift_pressure_pump, self.netconfiguration, 
                                   dT_RL, v_max_heat_consumer, self.building_temp_checked, pipetype, v_max_pipe, material_filter, insulation_filter, 
                                   self.DiameterOpt_ckecked, import_type)

        self.accept()

class ZeitreihenrechnungDialog(QDialog):
    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Zeitreihenrechnung")
        self.resize(400, 200)

        self.layout = QVBoxLayout(self)

        # Zeitschritte
        self.StartTimeStepLabel = QLabel("Zeitschritt Simulationsstart (min 0):", self)
        self.StartTimeStepInput = QLineEdit("0", self)
        self.EndTimeStepLabel = QLabel("Zeitschritt Simulationsende (max 8760):", self)
        self.EndTimeStepInput = QLineEdit("8760", self)

        self.layout.addWidget(self.StartTimeStepLabel)
        self.layout.addWidget(self.StartTimeStepInput)
        self.layout.addWidget(self.EndTimeStepLabel)
        self.layout.addWidget(self.EndTimeStepInput)

        # Dateiauswahl
        self.fileInputlayout = QHBoxLayout(self)

        self.resultsFileLabel = QLabel("Ausgabedatei Lastgang:", self)
        self.resultsFileInput = QLineEdit(f"{self.base_path}/Lastgang/Lastgang.csv", self)
        self.selectresultsFileButton = QPushButton('csv-Datei auswählen')
        self.selectresultsFileButton.clicked.connect(lambda: self.selectFilename(self.resultsFileInput))

        self.fileInputlayout.addWidget(self.resultsFileLabel)
        self.fileInputlayout.addWidget(self.resultsFileInput)
        self.fileInputlayout.addWidget(self.selectresultsFileButton)

        self.layout.addLayout(self.fileInputlayout)

        # Buttons
        buttonLayout = QHBoxLayout()
        okButton = QPushButton("OK", self)
        cancelButton = QPushButton("Abbrechen", self)
        
        okButton.clicked.connect(self.onAccept)
        cancelButton.clicked.connect(self.reject)
        
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)

        self.layout.addLayout(buttonLayout)

    def onAccept(self):
        if self.validateInputs():
            self.accept()

    def validateInputs(self):
        start = int(self.StartTimeStepInput.text())
        end = int(self.EndTimeStepInput.text())
        
        if start < 0 or start > 8760 or end < 0 or end > 8760:
            QMessageBox.warning(self, "Ungültige Eingabe", "Start- und Endzeitschritte müssen zwischen 0 und 8760 liegen.")
            return False
        if start > end:
            QMessageBox.warning(self, "Ungültige Eingabe", "Der Startschritt darf nicht größer als der Endschritt sein.")
            return False
        return True

    def selectFilename(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            lineEdit.setText(filename)

    def getValues(self):
        return {
            'results_filename': self.resultsFileInput.text(),
            'start': int(self.StartTimeStepInput.text()),
            'end': int(self.EndTimeStepInput.text())
        }