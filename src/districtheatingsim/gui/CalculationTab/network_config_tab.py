"""
Filename: network_config_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-11
Description: Contains the NetworkConfigTab class.
"""

import os
import sys

import numpy as np
import pandapipes as pp

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QComboBox, QWidget, QHBoxLayout, QCheckBox, QGroupBox

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

class NetworkConfigTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        netConfigGroup = QGroupBox("Netzkonfiguration")
        netConfigGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")
        netConfigLayout = QVBoxLayout()
        netConfigLayout.addLayout(self.createNetconfigurationControlInput())
        netConfigGroup.setLayout(netConfigLayout)
        layout.addWidget(netConfigGroup)

        tempConfigGroup = QGroupBox("Vorlauftemperatur- und Druckregelung")
        tempConfigGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")
        tempConfigLayout = QVBoxLayout()
        tempConfigLayout.addLayout(self.createTemperatureControlInput())
        tempConfigLayout.addLayout(self.createNetParameterInputs())
        tempConfigGroup.setLayout(tempConfigLayout)
        layout.addWidget(tempConfigGroup)

        heatConsumerConfigGroup = QGroupBox("Einstellungen für Wärmeabnehmer")
        heatConsumerConfigGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")
        heatConsumerConfigLayout = QVBoxLayout()
        heatConsumerConfigLayout.addLayout(self.createSupplyTemperatureCheckbox())
        heatConsumerConfigLayout.addLayout(self.createReturnTemperatureCheckbox())
        heatConsumerConfigLayout.addLayout(self.createHeatConsumerParameterInputs())
        heatConsumerConfigLayout.addLayout(self.createBuildingTemperatureCheckbox())
        heatConsumerConfigGroup.setLayout(heatConsumerConfigLayout)
        layout.addWidget(heatConsumerConfigGroup)

        pipetypeConfigGroup = QGroupBox("Rohrtyp zur Initialisierung des Netzes")
        pipetypeConfigGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")
        pipetypeConfigLayout = QVBoxLayout()
        pipetypeConfigLayout.addLayout(self.createinitialpipetypeInput())
        pipetypeConfigGroup.setLayout(pipetypeConfigLayout)
        layout.addWidget(pipetypeConfigGroup)

        # Update der Sichtbarkeit
        self.updateInputFieldsVisibility()

    def createNetconfigurationControlInput(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Netzkonfiguration:"))
        self.netconfigurationControlInput = QComboBox(self)
        self.netconfigurationControlInput.addItems(["Niedertemperaturnetz", "kaltes Netz"])
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
        self.supplyTempCheckbox.setToolTip("""Aktivieren Sie diese Option, um eine Mindestvorlauftemperatur für alle Gebäude festzulegen.\nDas können beispielsweise 60 °C sein um die Warmwasserbereitung zu gewährleisten.\nÜber die Temperaturdifferenz zwischen HAST und Netz ergibt sich dann eine Mindestvorlauftemperatur welche in der Simulation erreicht werden muss.\nWenn nicht definiert, wird keine Mindesttemperatur berücksichtigt.""")
        layout.addWidget(self.supplyTempCheckbox)
        self.supplyTempCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)
        return layout

    def createReturnTemperatureCheckbox(self):
        layout = QVBoxLayout()
        self.returnTempCheckbox = QCheckBox("Rücklauftemperatur für alle HA-Stationen festlegen.")
        self.returnTempCheckbox.setToolTip("""Aktivieren Sie diese Option, um die Rücklauftemperatur für alle HA-Stationen zentral festzulegen.\nStandardmäßig erfolgt die Berechung der Rücklauftemperaturen der HA-Station aus den Rücklauftemperaturen der Gebäude sowie der vorgegebenen Temperaturdifferenz zwischen Netz und HAST.""")
        layout.addWidget(self.returnTempCheckbox)
        self.returnTempCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)
        return layout

    def createBuildingTemperatureCheckbox(self):
        layout = QVBoxLayout()
        self.buildingTempCheckbox = QCheckBox("Gebäudeheizungstemperaturen im zeitlichen Verlauf berücksichtigen.")
        self.buildingTempCheckbox.setToolTip("""Aktivieren Sie diese Option, um die Vor- und Rücklauftemperaturen in den Gebäuden mittels Temperaturregelung entsprechend der definierten Temperaturen und der Steigung in Abhängigkeit der Außentemperatur zu berechnen.\nIst eine Mindestvorlauftemperatur vorgegeben wird diese berücksichtigt.\nDie vorgabe einer zentralen Rücklauftemperatur ergibt nur bei einem kalten Netz Sinn.""")
        layout.addWidget(self.buildingTempCheckbox)
        self.buildingTempCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)
        return layout

    def createNetParameterInputs(self):
        layout = QVBoxLayout()
        self.parameter_rows_net = []

        self.supply_temp_row = self.createParameterRow("Vorlauftemperatur Heizzentrale:", "85")
        self.parameter_rows_net.append(self.supply_temp_row)
        layout.addLayout(self.supply_temp_row)

        self.max_supply_temp_row = self.createParameterRow("Maximale Vorlauftemperatur Heizzentrale:", "85")
        self.parameter_rows_net.append(self.max_supply_temp_row)
        layout.addLayout(self.max_supply_temp_row)

        self.min_supply_temp_row = self.createParameterRow("Minimale Vorlauftemperatur Heizzentrale:", "70")
        self.parameter_rows_net.append(self.min_supply_temp_row)
        layout.addLayout(self.min_supply_temp_row)

        self.max_air_temp_row = self.createParameterRow("Obere Grenze der Lufttemperatur:", "15")
        self.parameter_rows_net.append(self.max_air_temp_row)
        layout.addLayout(self.max_air_temp_row)

        self.min_air_temp_row = self.createParameterRow("Untere Grenze der Lufttemperatur:", "-10")
        self.parameter_rows_net.append(self.min_air_temp_row)
        layout.addLayout(self.min_air_temp_row)

        layout.addWidget(QLabel("Druckregelung Heizzentrale:"))

        self.flow_pressure_row = self.createParameterRow("Vorlaufdruck:", "4")
        self.parameter_rows_net.append(self.flow_pressure_row)
        layout.addLayout(self.flow_pressure_row)

        lift_pressure_row = self.createParameterRow("Druckdifferenz Vorlauf/Rücklauf:", "1.5")
        self.parameter_rows_net.append(lift_pressure_row)
        layout.addLayout(lift_pressure_row)

        return layout

    def createHeatConsumerParameterInputs(self):
        layout = QVBoxLayout()
        self.parameter_rows_heat_consumer = []

        self.supply_temperature_heat_consumer_row = self.createParameterRow("Minimale Vorlauftemperatur Gebäude:", "60")
        self.parameter_rows_heat_consumer.append(self.supply_temperature_heat_consumer_row)
        layout.addLayout(self.supply_temperature_heat_consumer_row)

        self.return_temp_row = self.createParameterRow("Soll-Rücklauftemperatur HAST:", "50")
        self.parameter_rows_heat_consumer.append(self.return_temp_row)
        layout.addLayout(self.return_temp_row)

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

    def createinitialpipetypeInput(self):
        layout = QVBoxLayout()
        self.initialpipetypeInput = QComboBox(self)
        pipetypes = pp.std_types.available_std_types(pp.create_empty_network(fluid="water"), "pipe").index.tolist()
        self.initialpipetypeInput.addItems(pipetypes)
        layout.addWidget(self.initialpipetypeInput)
        
        default_pipe_type = "KMR 100/250-2v"
        if default_pipe_type in pipetypes:
            self.initialpipetypeInput.setCurrentText(default_pipe_type)
        else:
            print(f"Warnung: Startwert '{default_pipe_type}' nicht in der Liste der Rohrtypen gefunden.")

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

        self.supply_temperature_heat_consumer_checked = self.supplyTempCheckbox.isChecked()
        self.set_layout_visibility(self.supply_temperature_heat_consumer_row, self.supply_temperature_heat_consumer_checked)

        self.return_temp_checked = self.returnTempCheckbox.isChecked()
        self.set_layout_visibility(self.return_temp_row, self.return_temp_checked)

        self.building_temp_checked =  self.buildingTempCheckbox.isChecked()

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

            air_temperature_data, _, _, _, _ = import_TRY(self.parent.parent.data_manager.get_try_filename())

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