"""
River-water heat-pump and AqvaHeat dialogs (hand-written: CSV temperature import).
Moved verbatim from ``_04_technology_dialogs.py``; not yet schema-driven.

The waste-heat-pump dialog, which was simple, now lives schema-driven in
``_simple.py``.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QLineEdit, QLabel, QDialog, QFormLayout, QPushButton, QFileDialog, QMessageBox,
)

import numpy as np


class RiverHeatPumpDialog(QDialog):
    """
    A QDialog subclass for configuring river heat pump parameters.

    Attributes:
        tech_data (dict): Dictionary containing initial values for the river heat pump parameters.
        PFWInput (QLineEdit): Input field for the thermal capacity of the heat pump.
        TFWInput (QLineEdit): Input field for the river temperature.
        DTFWInput (QLineEdit): Input field for the permissible deviation of the heat pump's supply temperature from the network supply temperature.
        RHcostInput (QLineEdit): Input field for the specific investment costs of river heat utilization.
        WPRHcostInput (QLineEdit): Input field for the specific investment costs of the heat pump.
        csvButton (QPushButton): Button to open and load a CSV file containing river temperatures.
        canvas (FigureCanvas): Canvas to display the Matplotlib figure.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the RiverHeatPumpDialog.

        :param tech_data: Dictionary containing initial values for the river heat pump parameters
        :type tech_data: dict or None
        """
        super(RiverHeatPumpDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        main_layout = QVBoxLayout()
        rhp_layout = QFormLayout()

        self.PFWInput = QLineEdit(self)
        self.PFWInput.setText(str(self.tech_data.get('Wärmeleistung_FW_WP', "200")))
        rhp_layout.addRow(QLabel("th. Leistung Wärmepumpe in kW"), self.PFWInput)

        self.TFWInput = QLineEdit(self)
        if isinstance(self.tech_data.get('Temperatur_FW_WP'), (float, int)) or self.tech_data == {}:
            self.TFWInput.setText(str(self.tech_data.get('Temperatur_FW_WP', "10")))
        rhp_layout.addRow(QLabel("Flusstemperatur in °C"), self.TFWInput)

        self.csvButton = QPushButton("CSV für Flusstemperatur wählen", self)
        self.csvButton.clicked.connect(self.openCSV)
        rhp_layout.addRow(self.csvButton)

        self.DTFWInput = QLineEdit(self)
        self.DTFWInput.setText(str(self.tech_data.get('dT', "0")))
        rhp_layout.addRow(QLabel("Zulässige Abweichung Vorlauftemperatur Wärmepumpe von Netzvorlauftemperatur"), self.DTFWInput)

        self.RHcostInput = QLineEdit(self)
        self.RHcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_Flusswasser', "1000")))
        rhp_layout.addRow(QLabel("spez. Investitionskosten Flusswärmenutzung"), self.RHcostInput)

        self.WPRHcostInput = QLineEdit(self)
        self.WPRHcostInput.setText(str(self.tech_data.get('spezifische_Investitionskosten_WP', "1000")))
        rhp_layout.addRow(QLabel("spez. Investitionskosten Wärmepumpe"), self.WPRHcostInput)

        main_layout.addLayout(rhp_layout)
        self.setLayout(main_layout)

    def openCSV(self):
        """
        Opens a file dialog to select a CSV file and loads its content.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")  # this needs a path
        if filename:
            self.loadCSV(filename)

    def loadCSV(self, filename):
        """
        Loads temperature data from a CSV file.

        :param filename: The path to the CSV file
        :type filename: str
        """
        data = np.loadtxt(filename, delimiter=';', skiprows=1, usecols=1).astype(float)
        self.csvData = data
        QMessageBox.information(self, "CSV geladen", f"CSV-Datei {filename} erfolgreich geladen.")

    def getInputs(self):
        """
        Retrieves the input values from the user interface.

        :return: A dictionary containing the input values
        :rtype: dict
        """
        inputs = {
            'Wärmeleistung_FW_WP': float(self.PFWInput.text()),
            'dT': float(self.DTFWInput.text()),
            'spez_Investitionskosten_Flusswasser': float(self.RHcostInput.text()),
            'spezifische_Investitionskosten_WP': float(self.WPRHcostInput.text())
        }
        try:
            if hasattr(self, 'csvData'):
                inputs['Temperatur_FW_WP'] = self.csvData
            elif isinstance(self.tech_data.get('Temperatur_FW_WP'), (float, int)):
                inputs['Temperatur_FW_WP'] = float(self.TFWInput.text())
            elif isinstance(self.tech_data.get('Temperatur_FW_WP'), np.ndarray):
                inputs['Temperatur_FW_WP'] = self.tech_data.get('Temperatur_FW_WP')
            else:
                inputs['Temperatur_FW_WP'] = float(self.TFWInput.text())
        except ValueError:
            pass
        return inputs


class AqvaHeatDialog(QDialog):
    """
    A QDialog subclass for configuring AqvaHeat parameters.

    Attributes:
        tech_data (dict): Dictionary containing initial values for the river heat pump parameters.
        PFWInput (QLineEdit): Input field for the thermal capacity of the heat pump.
        TFWInput (QLineEdit): Input field for the river temperature.
        DTFWInput (QLineEdit): Input field for the permissible deviation of the heat pump's supply temperature from the network supply temperature.
        RHcostInput (QLineEdit): Input field for the specific investment costs of river heat utilization.
        WPRHcostInput (QLineEdit): Input field for the specific investment costs of the heat pump.
        csvButton (QPushButton): Button to open and load a CSV file containing river temperatures.
        canvas (FigureCanvas): Canvas to display the Matplotlib figure.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the RiverHeatPumpDialog.

        :param tech_data: Dictionary containing initial values for the river heat pump parameters
        :type tech_data: dict or None
        """
        super(AqvaHeatDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        main_layout = QVBoxLayout()
        rhp_layout = QFormLayout()

        main_layout.addLayout(rhp_layout)
        self.setLayout(main_layout)

    def openCSV(self):
        """
        Opens a file dialog to select a CSV file and loads its content.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")  # this needs a path
        if filename:
            self.loadCSV(filename)

    def loadCSV(self, filename):
        """
        Loads temperature data from a CSV file.

        :param filename: The path to the CSV file
        :type filename: str
        """
        data = np.loadtxt(filename, delimiter=';', skiprows=1, usecols=1).astype(float)
        self.csvData = data
        QMessageBox.information(self, "CSV geladen", f"CSV-Datei {filename} erfolgreich geladen.")

    def getInputs(self):
        """
        Retrieves the input values from the user interface.

        :return: A dictionary containing the input values
        :rtype: dict
        """
        inputs = {
        }
        return inputs
