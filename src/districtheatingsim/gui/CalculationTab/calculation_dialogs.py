"""
Filename: calculation_dialogs.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
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

from districtheatingsim.utilities.test_reference_year import import_TRY

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
    """
    Dialog for generating a network based on user inputs.
    
    Attributes:
        generate_callback (function): Callback function to generate the network.
        base_path (str): Base path for file dialogs.
        parent (QWidget): Parent widget.
    """

    def __init__(self, generate_callback, base_path, parent=None):
        super().__init__(parent)
        self.generate_callback = generate_callback
        self.base_path = base_path
        self.parent = parent
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface for the dialog.
        """
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
        self.jsonLineEdit = QLineEdit(os.path.join(self.base_path, self.parent.config_manager.get_relative_path('building_load_profile_path')))
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
        """
        Creates input fields for GeoJSON file selection.

        Returns:
            list: List of QVBoxLayout containing file input fields.
        """
        default_paths = {
            'Erzeugeranlagen': os.path.join(self.base_path, self.parent.config_manager.get_relative_path("net_heat_sources_path")),
            'HAST': os.path.join(self.base_path, self.parent.config_manager.get_relative_path("net_building_transfer_station_path")),
            'Vorlauf': os.path.join(self.base_path, self.parent.config_manager.get_relative_path("net_flow_pipes_path")),
            'Rücklauf': os.path.join(self.base_path, self.parent.config_manager.get_relative_path("net_return_pipes_path"))
        }

        file_inputs_layout = self.createFileInputsGeoJSON(default_paths)

        inputs = [
            file_inputs_layout
        ]
        return inputs

    def createFileInputsGeoJSON(self, default_paths):
        """
        Creates file input fields for GeoJSON files.

        Args:
            default_paths (dict): Default paths for the GeoJSON files.

        Returns:
            QVBoxLayout: Layout containing the file input fields.
        """
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
        """
        Creates a single file input field with a label, line edit, and browse button.

        Args:
            label_text (str): Text for the label.
            default_text (str): Default text for the line edit.

        Returns:
            QHBoxLayout: Layout containing the file input field.
        """
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
        """
        Opens a file dialog to select a JSON file.
        """
        fname, _ = QFileDialog.getOpenFileName(self, 'Select JSON File', os.path.join(self.base_path, self.parent.config_manager.get_relative_path('building_load_profile_path')), 'JSON Files (*.json);;All Files (*)')
        if fname:
            self.jsonLineEdit.setText(fname)
    
    def createNetconfigurationControlInput(self):
        """
        Creates input for network configuration control.

        Returns:
            QVBoxLayout: Layout containing the network configuration control input.
        """
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Netzkonfiguration:"))
        self.netconfigurationControlInput = QComboBox(self)
        self.netconfigurationControlInput.addItems(["Niedertemperaturnetz", "kaltes Netz"])#, "wechselwarmes Netz"])
        layout.addWidget(self.netconfigurationControlInput)
        self.netconfigurationControlInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)
        return layout
    
    def createTemperatureControlInput(self):
        """
        Creates input for temperature control.

        Returns:
            QVBoxLayout: Layout containing the temperature control input.
        """
        layout = QVBoxLayout()
        self.temperatureControlInput = QComboBox(self)
        self.temperatureControlInput.addItems(["Gleitend", "Statisch"])
        layout.addWidget(QLabel("Vorlauftemperatur-Regelung:"))
        layout.addWidget(self.temperatureControlInput)
        self.temperatureControlInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)
        return layout
    
    def createSupplyTemperatureCheckbox(self):
        """
        Creates checkbox for supply temperature control.

        Returns:
            QVBoxLayout: Layout containing the supply temperature control checkbox.
        """
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Temperaturregelung HAST:"))

        self.supplyTempCheckbox = QCheckBox("Mindestvorlauftemperatur für die Gebäude berücksichtigen.")
        self.supplyTempCheckbox.setToolTip("""Aktivieren Sie diese Option, um eine Mindestvorlauftemperatur für alle Gebäude festzulegen.\nDas können beispielsweise 60 °C sein um die Warmwasserbereitung zu gewährleisten.\nÜber die Temperaturdifferenz zwischen HAST und Netz ergibt sich dann eine Mindestvorlauftemperatur welche in der Simulation erreicht werden muss.\nWenn nicht definiert, wird keine Mindesttemperatur berücksichtigt.""")  # Tooltip hinzufügen
        layout.addWidget(self.supplyTempCheckbox)

        # Verbinde das stateChanged Signal der Checkbox mit der update-Methode
        self.supplyTempCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)
        
        return layout

    def createReturnTemperatureCheckbox(self):
        """
        Creates checkbox for return temperature control.

        Returns:
            QVBoxLayout: Layout containing the return temperature control checkbox.
        """
        layout = QVBoxLayout()

        self.returnTempCheckbox = QCheckBox("Rücklauftemperatur für alle HA-Stationen festlegen.")
        self.returnTempCheckbox.setToolTip("""Aktivieren Sie diese Option, um die Rücklauftemperatur für alle HA-Stationen zentral festzulegen.\nStandardmäßig erfolgt die Berechung der Rücklauftemperaturen der HA-Station aus den Rücklauftemperaturen der Gebäude sowie der vorgegebenen Temperaturdifferenz zwischen Netz und HAST.""")  # Tooltip hinzufügen
        layout.addWidget(self.returnTempCheckbox)

        # Verbinde das stateChanged Signal der Checkbox mit der update-Methode
        self.returnTempCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)
        
        return layout
    
    def createBuildingTemperatureCheckbox(self):
        """
        Creates checkbox for building heating temperature control.

        Returns:
            QVBoxLayout: Layout containing the building heating temperature control checkbox.
        """
        layout = QVBoxLayout()
        self.buildingTempCheckbox = QCheckBox("Gebäudeheizungstemperaturen im zeitlichen Verlauf berücksichtigen.")
        self.buildingTempCheckbox.setToolTip("""Aktivieren Sie diese Option, um die Vor- und Rücklauftemperaturen in den Gebäuden mittels Temperaturregelung entsprechend der definierten Temperaturen und der Steigung in Abhängigkeit der Außentemperatur zu berechnen.\nIst eine Mindestvorlauftemperatur vorgegeben wird diese berücksichtigt.\nDie vorgabe einer zentralen Rücklauftemperatur ergibt nur bei einem kalten Netz Sinn.""")  # Tooltip hinzufügen
        layout.addWidget(self.buildingTempCheckbox)

        # Verbinde das stateChanged Signal der Checkbox mit der update-Methode
        self.buildingTempCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)
        
        return layout

    def createNetParameterInputs(self):
        """
        Creates input fields for network parameters.

        Returns:
            QVBoxLayout: Layout containing the network parameter input fields.
        """
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
        """
        Creates input fields for heat consumer parameters.

        Returns:
            QVBoxLayout: Layout containing the heat consumer parameter input fields.
        """
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
        """
        Creates a single parameter row with a label and line edit.

        Args:
            label_text (str): Text for the label.
            default_text (str): Default text for the line edit.

        Returns:
            QHBoxLayout: Layout containing the parameter row.
        """
        row_layout = QHBoxLayout()
        label = QLabel(label_text)
        line_edit = QLineEdit(default_text)
        row_layout.addWidget(label)
        row_layout.addWidget(line_edit)
        return row_layout
    
    def createDiameterOptCheckbox(self):
        """
        Creates checkbox for diameter optimization.

        Returns:
            QVBoxLayout: Layout containing the diameter optimization checkbox.
        """
        layout = QVBoxLayout()
        self.DiameterOptCheckbox = QCheckBox("Durchmesser optimieren.")
        layout.addWidget(self.DiameterOptCheckbox)

        # Setze die Checkbox bei der Initialisierung als ausgewählt
        self.DiameterOptCheckbox.setChecked(True)

        # Verbinde das stateChanged Signal der Checkbox mit der update-Methode
        self.DiameterOptCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)

        return layout

    def createinitialpipetypeInput(self):
        """
        Creates input field for initial pipe type selection.

        Returns:
            QVBoxLayout: Layout containing the initial pipe type input field.
        """
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
        """
        Creates input fields for diameter optimization parameters.

        Returns:
            QVBoxLayout: Layout containing the diameter optimization input fields.
        """
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Eingaben zur Durchmesseroptimierung der Rohrleitungen:"))

        row_layout = QHBoxLayout()
        self.v_max_pipelabel = QLabel("Maximale Strömungsgeschwindigkeit Leitungen:")
        self.v_max_pipeInput = QLineEdit("1.0")
        row_layout.addWidget(self.v_max_pipelabel)
        row_layout.addWidget(self.v_max_pipeInput)
        layout.addLayout(row_layout)

        self.material_filterInput = QComboBox(self)
        self.material_filterInput.addItems(["KMR", "FL", "HK"])
        layout.addWidget(self.material_filterInput)
        self.material_filterInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)

        self.k_mm_Label = QLabel("Rauigkeit der Rohrleitungen:")
        self.k_mm_Input = QLineEdit("0.1")
        row_layout.addWidget(self.k_mm_Label)
        row_layout.addWidget(self.k_mm_Input)
        layout.addLayout(row_layout)
    
        return layout

    def set_layout_visibility(self, layout, visible):
        """
        Sets the visibility of all widgets in a layout.

        Args:
            layout (QLayout): The layout to update.
            visible (bool): Whether the widgets should be visible.
        """
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.setVisible(visible)
            elif item.layout():
                self.set_layout_visibility(item.layout(), visible)

    def set_default_value(self, parameter_row, value):
        """
        Sets the default value for a parameter row.

        Args:
            parameter_row (QHBoxLayout): The parameter row layout.
            value (str): The default value to set.
        """
        # Zugriff auf das QLineEdit Widget in der Parameterzeile und Aktualisieren des Textes
        for i in range(parameter_row.count()):
            widget = parameter_row.itemAt(i).widget()
            if isinstance(widget, QLineEdit):
                widget.setText(value)
                break  # Beendet die Schleife, sobald das QLineEdit gefunden und aktualisiert wurde

    def updateInputFieldsVisibility(self):
        """
        Updates the visibility of input fields based on the selected options.
        """
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

        self.material_filterInput.setVisible(self.DiameterOpt_ckecked)

        self.supply_temperature_heat_consumer_checked = self.supplyTempCheckbox.isChecked()
        self.set_layout_visibility(self.supply_temperature_heat_consumer_row, self.supply_temperature_heat_consumer_checked)

        self.return_temp_checked = self.returnTempCheckbox.isChecked()
        self.set_layout_visibility(self.return_temp_row, self.return_temp_checked)

        self.building_temp_checked =  self.buildingTempCheckbox.isChecked()

    def selectFilename(self, line_edit):
        """
        Opens a file dialog to select a file and updates the line edit with the selected file path.

        Args:
            line_edit (QLineEdit): The line edit to update with the selected file path.
        """
        fname, _ = QFileDialog.getOpenFileName(self, 'Datei auswählen', '', 'All Files (*);;CSV Files (*.csv);;GeoJSON Files (*.geojson)')
        if fname:
            line_edit.setText(fname)
            self.update_plot()

    ### Hier vielleicht noch Funktionalitäten auslagern
    def calculateTemperatureCurve(self):
        """
        Calculates the temperature curve based on the selected control mode.

        Returns:
            float or np.ndarray: The calculated temperature curve.
        """
        control_mode = self.temperatureControlInput.currentText()
        if control_mode == "Statisch":
            return float(self.parameter_rows_net[0].itemAt(1).widget().text())
        elif control_mode == "Gleitend":
            max_supply_temperature = float(self.parameter_rows_net[1].itemAt(1).widget().text())
            min_supply_temperature = float(self.parameter_rows_net[2].itemAt(1).widget().text())
            max_air_temperature = float(self.parameter_rows_net[3].itemAt(1).widget().text())
            min_air_temperature = float(self.parameter_rows_net[4].itemAt(1).widget().text())

            air_temperature_data, _, _, _, _ = import_TRY(self.parent.data_manager.get_try_filename())

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
        """
        Updates the plot based on the selected GeoJSON files.
        """
        try:
            # Pfade auslesen
            vorlauf_path = self.vorlaufInput.itemAt(1).widget().text()
            ruecklauf_path = self.ruecklaufInput.itemAt(1).widget().text()
            hast_path = self.hastInput.itemAt(1).widget().text()
            erzeugeranlagen_path = self.erzeugeranlagenInput.itemAt(1).widget().text()

            # Dateien prüfen, ob sie existieren
            if not (os.path.exists(vorlauf_path) and os.path.exists(ruecklauf_path) and 
                    os.path.exists(hast_path) and os.path.exists(erzeugeranlagen_path)):
                raise FileNotFoundError("Eine oder mehrere GeoJSON-Dateien wurden nicht gefunden.")
            
            # Dateien einlesen
            vorlauf = gpd.read_file(vorlauf_path)
            ruecklauf = gpd.read_file(ruecklauf_path)
            hast = gpd.read_file(hast_path)
            erzeugeranlagen = gpd.read_file(erzeugeranlagen_path)

            # Plot vorbereiten
            self.figure1.clear()
            ax = self.figure1.add_subplot(111)

            # GeoJSON-Daten plotten
            vorlauf.plot(ax=ax, color='red')
            ruecklauf.plot(ax=ax, color='blue')
            hast.plot(ax=ax, color='green')
            erzeugeranlagen.plot(ax=ax, color='black')

            # Annotations vorbereiten
            annotations = []
            for idx, row in hast.iterrows():
                point = row['geometry'].representative_point()
                label = (f"{row['Adresse']}\nWärmebedarf: {row['Wärmebedarf']}\n"
                        f"Gebäudetyp: {row['Gebäudetyp']}\nVLT_max: {row['VLT_max']}\nRLT_max: {row['RLT_max']}")
                annotation = ax.annotate(label, xy=(point.x, point.y), xytext=(10, 10),
                                        textcoords="offset points", bbox=dict(boxstyle="round", fc="w"))
                annotation.set_visible(False)
                annotations.append((point, annotation))

            # Event-Handler für Mausbewegung
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

        except FileNotFoundError as e:
            # Fehlermeldung anzeigen, wenn Dateien fehlen
            self.figure1.clear()
            ax = self.figure1.add_subplot(111)
            ax.text(0.5, 0.5, 'No data available', fontsize=20, ha='center')
            self.canvas1.draw()

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Dateien nicht gefunden")
            msg.setInformativeText(str(e))
            msg.setWindowTitle("Fehler")
            msg.exec_()

        except Exception as e:
            # Allgemeine Fehlermeldung bei anderen Fehlern
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ein Fehler ist aufgetreten")
            msg.setInformativeText(str(e))
            msg.setWindowTitle("Fehler")
            msg.exec_()

    def generateNetwork(self):
        """
        Generates the network based on the user inputs and calls the generate_callback function.
        """
        import_type = self.importTypeComboBox.currentText()
        if import_type == "GeoJSON":
            # Extrahiere GeoJSON-spezifische Daten
            vorlauf_path = self.vorlaufInput.itemAt(1).widget().text()
            ruecklauf_path = self.ruecklaufInput.itemAt(1).widget().text()
            hast_path = self.hastInput.itemAt(1).widget().text()
            erzeugeranlagen_path = self.erzeugeranlagenInput.itemAt(1).widget().text()

            json_path = self.jsonLineEdit.text()

            pipetype = self.initialpipetypeInput.currentText()

            v_max_pipe = float(self.v_max_pipeInput.text())
            material_filter = self.material_filterInput.currentText()
            k_mm = float(self.k_mm_Input.text())

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
            self.generate_callback(vorlauf_path, ruecklauf_path, hast_path, erzeugeranlagen_path, json_path, supply_temperature_heat_consumer, 
                                   rl_temp_heat_consumer, supply_temperature_net, flow_pressure_pump, lift_pressure_pump, self.netconfiguration, 
                                   dT_RL, self.building_temp_checked, pipetype, v_max_pipe, material_filter, self.DiameterOpt_ckecked, 
                                   k_mm, import_type)

        self.accept()

class ZeitreihenrechnungDialog(QDialog):
    """
    Dialog for time series calculation based on user inputs.
    
    Attributes:
        base_path (str): Base path for file dialogs.
        parent (QWidget): Parent widget.
    """

    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.parent = parent
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface for the dialog.
        """
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
        self.resultsFileInput = QLineEdit(os.path.join(self.base_path, self.parent.config_manager.get_relative_path('load_profile_path')), self)
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
        """
        Validates the inputs and accepts the dialog if valid.
        """
        if self.validateInputs():
            self.accept()

    def validateInputs(self):
        """
        Validates the start and end time steps.

        Returns:
            bool: True if inputs are valid, False otherwise.
        """
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
        """
        Opens a file dialog to select a file and updates the line edit with the selected file path.

        Args:
            lineEdit (QLineEdit): The line edit to update with the selected file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            lineEdit.setText(filename)

    def getValues(self):
        """
        Gets the values from the dialog.

        Returns:
            dict: Dictionary containing the results filename, start time step, and end time step.
        """
        return {
            'results_filename': self.resultsFileInput.text(),
            'start': int(self.StartTimeStepInput.text()),
            'end': int(self.EndTimeStepInput.text())
        }
