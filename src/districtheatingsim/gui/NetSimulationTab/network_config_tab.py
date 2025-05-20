"""
Filename: network_config_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-17
Description: Contains the NetworkConfigTab class.
"""

import pandapipes as pp

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QComboBox, QWidget, QHBoxLayout, QCheckBox, QGroupBox

class NetworkConfigTab(QWidget):
    def __init__(self, dialog_config, parent=None):
        super().__init__(parent)
        self.dialog_config = dialog_config
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
        self.netconfigurationControlInput.addItems(self.dialog_config["netconfiguration"])
        layout.addWidget(self.netconfigurationControlInput)
        self.netconfigurationControlInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)
        return layout

    def createTemperatureControlInput(self):
        layout = QVBoxLayout()
        self.supplyTemperatureControlInput = QComboBox(self)
        self.supplyTemperatureControlInput.addItems(self.dialog_config["supply_temperature_control"])
        layout.addWidget(QLabel("Vorlauftemperatur-Regelung:"))
        layout.addWidget(self.supplyTemperatureControlInput)
        self.supplyTemperatureControlInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)
        return layout

    def createSupplyTemperatureCheckbox(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Temperaturregelung HAST:"))

        self.minSupplyTempCheckbox = QCheckBox("Mindestvorlauftemperatur für die Gebäude berücksichtigen.")
        self.minSupplyTempCheckbox.setToolTip("""Aktivieren Sie diese Option, um eine Mindestvorlauftemperatur für alle Gebäude festzulegen.\nDas können beispielsweise 60 °C sein um die Warmwasserbereitung zu gewährleisten.\nÜber die Temperaturdifferenz zwischen HAST und Netz ergibt sich dann eine Mindestvorlauftemperatur welche in der Simulation erreicht werden muss.\nWenn nicht definiert, wird keine Mindesttemperatur berücksichtigt.""")
        layout.addWidget(self.minSupplyTempCheckbox)
        self.minSupplyTempCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)
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

        # Hole die aktuelle Netzkonfiguration aus dem Dialog (oder nimm die erste als Fallback)
        netconfig = self.netconfigurationControlInput.currentText() if hasattr(self, 'netconfigurationControlInput') else self.dialog_config["netconfiguration"][0]
        std = self.dialog_config["standardwerte"][netconfig]

        self.max_supply_temp_row = self.createParameterRow("Maximale Vorlauftemperatur Heizzentrale:", str(std["max_supply_temp"]))
        self.parameter_rows_net.append(self.max_supply_temp_row)
        layout.addLayout(self.max_supply_temp_row)

        self.min_supply_temp_row = self.createParameterRow("Minimale Vorlauftemperatur Heizzentrale:", str(std["min_supply_temp"]))
        self.parameter_rows_net.append(self.min_supply_temp_row)
        layout.addLayout(self.min_supply_temp_row)

        self.max_air_temp_row = self.createParameterRow("Obere Grenze der Lufttemperatur:", str(std["max_air_temp"]))
        self.parameter_rows_net.append(self.max_air_temp_row)
        layout.addLayout(self.max_air_temp_row)

        self.min_air_temp_row = self.createParameterRow("Untere Grenze der Lufttemperatur:", str(std["min_air_temp"]))
        self.parameter_rows_net.append(self.min_air_temp_row)
        layout.addLayout(self.min_air_temp_row)

        layout.addWidget(QLabel("Druckregelung Heizzentrale:"))

        self.flow_pressure_row = self.createParameterRow("Vorlaufdruck:", str(std["flow_pressure"]))
        self.parameter_rows_net.append(self.flow_pressure_row)
        layout.addLayout(self.flow_pressure_row)

        self.lift_pressure_row = self.createParameterRow("Druckdifferenz Vorlauf/Rücklauf:", str(std["lift_pressure"]))
        self.parameter_rows_net.append(self.lift_pressure_row)
        layout.addLayout(self.lift_pressure_row)

        return layout

    def createHeatConsumerParameterInputs(self):
        layout = QVBoxLayout()
        self.parameter_rows_heat_consumer = []

        # Hole die aktuelle Netzkonfiguration aus dem Dialog (oder nimm die erste als Fallback)
        netconfig = self.netconfigurationControlInput.currentText() if hasattr(self, 'netconfigurationControlInput') else self.dialog_config["netconfiguration"][0]
        std = self.dialog_config["standardwerte"][netconfig]

        self.min_supply_temperature_building_row = self.createParameterRow("Minimale Vorlauftemperatur Gebäude:", str(std["min_supply_temp_building"]))
        self.parameter_rows_heat_consumer.append(self.min_supply_temperature_building_row)
        layout.addLayout(self.min_supply_temperature_building_row)

        self.return_temp_row = self.createParameterRow("Soll-Rücklauftemperatur HAST:", str(std["return_temp"]))
        self.parameter_rows_heat_consumer.append(self.return_temp_row)
        layout.addLayout(self.return_temp_row)

        self.dT_RL_row = self.createParameterRow("Temperaturdifferenz Netz/HAST:", str(std["dT_RL"]))
        self.parameter_rows_heat_consumer.append(self.dT_RL_row)
        layout.addLayout(self.dT_RL_row)

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

        # Hole die aktuelle Netzkonfiguration aus dem Dialog (oder nimm die erste als Fallback)
        netconfig = self.netconfigurationControlInput.currentText() if hasattr(self, 'netconfigurationControlInput') else self.dialog_config["netconfiguration"][0]
        std = self.dialog_config["standardwerte"][netconfig]
        
        default_pipe_type = std["default_pipe_type"]
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
        std = self.dialog_config["standardwerte"][self.netconfiguration]
        self.set_default_value(self.max_supply_temp_row, str(std["max_supply_temp"]))
        self.set_default_value(self.min_supply_temp_row, str(std["min_supply_temp"]))
        self.set_default_value(self.return_temp_row, str(std["return_temp"]))

        is_control_mode_static = self.supplyTemperatureControlInput.currentText() == "Statisch"
        is_control_mode_dynamic = self.supplyTemperatureControlInput.currentText() == "Gleitend"

        if is_control_mode_static:
            # Zeige die Widgets für Vorlauftemperatur (Index 0)
            for i in range(self.parameter_rows_net[0].count()):
                widget = self.parameter_rows_net[0].itemAt(i).widget()
                if widget:
                    widget.setVisible(True)
            
            # Blende die Widgets für Maximale Vorlauftemperatur, Minimale Vorlauftemperatur,
            # Obere Grenze der Lufttemperatur und Untere Grenze der Lufttemperatur (Index 1 bis 4) aus
            for parameter_row in self.parameter_rows_net[1:4]:
                for i in range(parameter_row.count()):
                    widget = parameter_row.itemAt(i).widget()
                    if widget:
                        widget.setVisible(False)

        elif is_control_mode_dynamic:
            # Blende die Widgets für Vorlauftemperatur (Index 0) aus
            for i in range(self.parameter_rows_net[0].count()):
                widget = self.parameter_rows_net[0].itemAt(i).widget()
                if widget:
                    widget.setVisible(True)

            # Zeige die Widgets für Maximale Vorlauftemperatur, Minimale Vorlauftemperatur,
            # Obere Grenze der Lufttemperatur und Untere Grenze der Lufttemperatur (Index 1 bis 4)
            for parameter_row in self.parameter_rows_net[1:4]:
                for i in range(parameter_row.count()):
                    widget = parameter_row.itemAt(i).widget()
                    if widget:
                        widget.setVisible(True)

        self.min_supply_temperature_building_checked = self.minSupplyTempCheckbox.isChecked()
        self.set_layout_visibility(self.min_supply_temperature_building_row, self.min_supply_temperature_building_checked)

        self.return_temp_checked = self.returnTempCheckbox.isChecked()
        self.set_layout_visibility(self.return_temp_row, self.return_temp_checked)

        self.building_temp_checked =  self.buildingTempCheckbox.isChecked()

    ### Hier vielleicht noch Funktionalitäten auslagern
    def getSupplyTemperatureHeatGenerator(self):
        """
        Calculates the temperature curve based on the selected control mode.

        Returns:
            float or np.ndarray: The calculated temperature curve.
        """
        self.supply_temperature_control = self.supplyTemperatureControlInput.currentText()
        if self.supply_temperature_control == "Statisch":
            self.max_supply_temperature = float(self.parameter_rows_net[0].itemAt(1).widget().text())
            self.min_supply_temperature = None
            self.max_air_temperature = None
            self.min_air_temperature = None

        elif self.supply_temperature_control == "Gleitend":
            self.max_supply_temperature = float(self.parameter_rows_net[0].itemAt(1).widget().text())
            self.min_supply_temperature = float(self.parameter_rows_net[1].itemAt(1).widget().text())
            self.max_air_temperature = float(self.parameter_rows_net[2].itemAt(1).widget().text())
            self.min_air_temperature = float(self.parameter_rows_net[3].itemAt(1).widget().text())
