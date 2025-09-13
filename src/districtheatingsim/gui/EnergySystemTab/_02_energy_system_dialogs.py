"""
Energy System Dialogs Module
=============================

This module contains the dialogs for the Energy System Tab, including economic parameters input, cost calculation based on geoJSON files, and weight settings for optimization.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-02
"""

import os

import numpy as np
import geopandas as gpd

from PyQt6.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, QComboBox, \
    QPushButton, QHBoxLayout, QMessageBox, QFormLayout, QDialogButtonBox

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

class EconomicParametersDialog(QDialog):
    """
    A QDialog subclass for inputting economic parameters.

    Attributes:
        default_values (dict): Dictionary containing the default values for the input fields.
        gaspreisInput (QLineEdit): Input field for gas price.
        strompreisInput (QLineEdit): Input field for electricity price.
        holzpreisInput (QLineEdit): Input field for wood price.
        kapitalzinsInput (QLineEdit): Input field for capital interest rate.
        preissteigerungsrateInput (QLineEdit): Input field for price increase rate.
        betrachtungszeitraumInput (QLineEdit): Input field for evaluation period.
        stundensatzInput (QLineEdit): Input field for hourly wage rate for maintenance.
        BEWComboBox (QComboBox): ComboBox for considering BEW funding.
        fig (Figure): Matplotlib figure for plotting.
        ax (Axes): Matplotlib axes for plotting.
        canvas (FigureCanvas): Canvas to display the Matplotlib figure.
    
    """

    def __init__(self, parent=None):
        """
        Initializes the EconomicParametersDialog.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.default_values = {
            "gas_price": 70.0,
            "electricity_price": 150.0,
            "wood_price": 50.0,
            "capital_interest_rate": 1.05,
            "inflation_rate": 1.03,
            "time_period": 20,
            "hourly_rate": 45.0,
            "subsidy_eligibility": "Nein"
        }
        self.initUI()
        self.loadValues(self.default_values)
        self.plotPriceDevelopment()
        self.connectSignals()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        self.setWindowTitle("Eingabe wirtschaftliche Parameter")

        self.mainLayout = QHBoxLayout(self)

        # Left Column
        self.leftLayout = QVBoxLayout()

        self.gaspreisLabel = QLabel("Gaspreis (€/MWh):", self)
        self.gaspreisInput = QLineEdit(self)
        self.leftLayout.addWidget(self.gaspreisLabel)
        self.leftLayout.addWidget(self.gaspreisInput)

        self.strompreisLabel = QLabel("Strompreis (€/MWh):", self)
        self.strompreisInput = QLineEdit(self)
        self.leftLayout.addWidget(self.strompreisLabel)
        self.leftLayout.addWidget(self.strompreisInput)

        self.holzpreisLabel = QLabel("Holzpreis (€/MWh):", self)
        self.holzpreisInput = QLineEdit(self)
        self.leftLayout.addWidget(self.holzpreisLabel)
        self.leftLayout.addWidget(self.holzpreisInput)

        self.kapitalzinsLabel = QLabel("Kapitalzins (%):", self)
        self.kapitalzinsInput = QLineEdit(self)
        self.leftLayout.addWidget(self.kapitalzinsLabel)
        self.leftLayout.addWidget(self.kapitalzinsInput)

        self.preissteigerungsrateLabel = QLabel("Preissteigerungsrate (%):", self)
        self.preissteigerungsrateInput = QLineEdit(self)
        self.leftLayout.addWidget(self.preissteigerungsrateLabel)
        self.leftLayout.addWidget(self.preissteigerungsrateInput)

        self.betrachtungszeitraumLabel = QLabel("Betrachtungszeitraum (Jahre):", self)
        self.betrachtungszeitraumInput = QLineEdit(self)
        self.leftLayout.addWidget(self.betrachtungszeitraumLabel)
        self.leftLayout.addWidget(self.betrachtungszeitraumInput)

        self.stundensatzLabel = QLabel("Stundensatz Wartung und Instandhaltung (€/h):", self)
        self.stundensatzInput = QLineEdit(self)
        self.leftLayout.addWidget(self.stundensatzLabel)
        self.leftLayout.addWidget(self.stundensatzInput)

        self.BEWLabel = QLabel("Berücksichtigung BEW-Förderung?:", self)
        self.BEWComboBox = QComboBox(self)
        self.BEWComboBox.addItems(["Nein", "Ja"])
        self.leftLayout.addWidget(self.BEWLabel)
        self.leftLayout.addWidget(self.BEWComboBox)

        buttonLayout = QHBoxLayout()
        okButton = QPushButton("OK", self)
        cancelButton = QPushButton("Abbrechen", self)

        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)

        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)

        self.leftLayout.addLayout(buttonLayout)
        self.mainLayout.addLayout(self.leftLayout)

        # Right Column (Matplotlib Plot)
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        self.mainLayout.addWidget(self.canvas)

    def loadValues(self, values):
        """
        Loads the given values into the input fields.

        Args:
            values (dict): Dictionary containing the values to load.
        """
        self.gaspreisInput.setText(str(values["gas_price"]))
        self.strompreisInput.setText(str(values["electricity_price"]))
        self.holzpreisInput.setText(str(values["wood_price"]))
        self.kapitalzinsInput.setText(str((values["capital_interest_rate"] - 1) * 100))
        self.preissteigerungsrateInput.setText(str((values["inflation_rate"] - 1 ) * 100))
        self.betrachtungszeitraumInput.setText(str(values["time_period"]))
        self.stundensatzInput.setText(str(values["hourly_rate"]))
        self.BEWComboBox.setCurrentText(values["subsidy_eligibility"])

    def getValues(self):
        """
        Gets the values from the input fields.

        Returns:
            dict: A dictionary containing the input values.
        """
        return {
            "gas_price": float(self.gaspreisInput.text()),
            "electricity_price": float(self.strompreisInput.text()),
            "wood_price": float(self.holzpreisInput.text()),
            "capital_interest_rate": (float(self.kapitalzinsInput.text()) / 100) + 1,
            "inflation_rate": (float(self.preissteigerungsrateInput.text()) / 100) + 1,
            "time_period": int(self.betrachtungszeitraumInput.text()),
            "hourly_rate": float(self.stundensatzInput.text()),
            "subsidy_eligibility": self.BEWComboBox.currentText()
        }

    def updateValues(self, new_values):
        """
        Updates the default values and reloads them into the input fields.

        Args:
            new_values (dict): Dictionary containing the new values.
        """
        self.default_values.update(new_values)
        self.loadValues(self.default_values)
        
        self.plotPriceDevelopment()

    def connectSignals(self):
        """
        Connects the signals of the input fields to the validation method.
        """
        self.gaspreisInput.textChanged.connect(self.validateInput)
        self.strompreisInput.textChanged.connect(self.validateInput)
        self.holzpreisInput.textChanged.connect(self.validateInput)
        self.preissteigerungsrateInput.textChanged.connect(self.validateInput)
        self.kapitalzinsInput.textChanged.connect(self.validateInput)
        self.betrachtungszeitraumInput.textChanged.connect(self.validateInput)
        self.stundensatzInput.textChanged.connect(self.validateInput)
        self.BEWComboBox.currentTextChanged.connect(self.validateInput)

    def validateInput(self):
        """
        Validates the input fields and updates the plot if valid.
        """
        try:
            float(self.gaspreisInput.text())
            float(self.strompreisInput.text())
            float(self.holzpreisInput.text())
            float(self.kapitalzinsInput.text())
            float(self.preissteigerungsrateInput.text())
            int(self.betrachtungszeitraumInput.text())
            float(self.stundensatzInput.text())
        except ValueError:
            self.showErrorMessage("Ungültige Eingabe. Bitte geben Sie numerische Werte ein.")
            return

        self.plotPriceDevelopment()

    def showErrorMessage(self, message):
        """
        Shows an error message dialog.

        Args:
            message (str): The message to display.
        """
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Icon.Warning)
        msgBox.setText(message)
        msgBox.setWindowTitle("Fehler")
        msgBox.exec()

    def plotPriceDevelopment(self):
        """
        Plots the price development of energy carriers over time.
        """
        self.ax.clear()

        years = range(1, int(self.betrachtungszeitraumInput.text()) + 1)
        gas_prices = [float(self.gaspreisInput.text()) * (1 + float(self.preissteigerungsrateInput.text()) / 100) ** year for year in years]
        strom_prices = [float(self.strompreisInput.text()) * (1 + float(self.preissteigerungsrateInput.text()) / 100) ** year for year in years]
        holz_prices = [float(self.holzpreisInput.text()) * (1 + float(self.preissteigerungsrateInput.text()) / 100) ** year for year in years]

        self.ax.plot(years, gas_prices, label='Gaspreis')
        self.ax.plot(years, strom_prices, label='Strompreis')
        self.ax.plot(years, holz_prices, label='Holzpreis')

        self.ax.set_xticks(years[::1])
        self.ax.set_xticklabels(years[::1])
        self.ax.set_xlabel('Jahr')
        self.ax.set_ylabel('Preis (€/MWh)')
        self.ax.set_title('Preisentwicklung der Energieträger')
        self.ax.legend()

        self.fig.tight_layout()
        self.canvas.draw()

class KostenBerechnungDialog(QDialog):
    """
    A QDialog subclass for calculating costs based on a geoJSON file.

    Attributes:
        base_path (str): The base path for loading the geoJSON file.
        filename (str): The filename of the geoJSON file.
        label (str): The label for the specific cost input field.
        value (str): The default value for the specific cost input field.
        type (str): The type of cost calculation.
        total_cost (float): The total calculated cost.
    """

    def __init__(self, parent=None, label=None, value=None, type=None):
        """
        Initializes the KostenBerechnungDialog.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
            label (str, optional): The label for the specific cost input field. Defaults to None.
            value (str, optional): The default value for the specific cost input field. Defaults to None.
            type (str, optional): The type of cost calculation. Defaults to None.
        """
        super().__init__(parent)
        self.base_path = parent.base_path
        self.config_manager = parent.config_manager
        self.filename = os.path.join(self.base_path, self.config_manager.get_relative_path("dimensioned_net_path"))
        self.label = label
        self.value = value
        self.type = type
        self.total_cost = None
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        self.layout = QVBoxLayout(self)

        self.specCostLabel = QLabel(self.label)
        self.specCostInput = QLineEdit(self.value, self)
        self.layout.addWidget(self.specCostLabel)
        self.layout.addWidget(self.specCostInput)

        self.filenameLabel = QLabel("Datei Wärmenetz")
        self.filenameInput = QLineEdit(self.filename, self)
        self.layout.addWidget(self.filenameLabel)
        self.layout.addWidget(self.filenameInput)

        okButton = QPushButton("OK", self)
        cancelButton = QPushButton("Abbrechen", self)
        okButton.clicked.connect(self.onAccept)
        cancelButton.clicked.connect(self.reject)
        self.layout.addWidget(okButton)
        self.layout.addWidget(cancelButton)

    def onAccept(self):
        """
        Reads the geoJSON file and calculates the total cost based on the input values.
        """
        gdf_net = gpd.read_file(self.filename)

        gdf_net_filtered = gdf_net[gdf_net["name"].str.startswith(self.type)]

        if self.type.startswith("flow line"):
            self.length_values = gdf_net_filtered["length_m"].values.astype(float)
            self.cost_lines = self.length_values * float(self.specCostInput.text())
            self.total_cost = round(np.sum(self.cost_lines), 0)

        elif self.type == "HAST":
            self.qext_values = gdf_net_filtered["qext_W"].values.astype(float) / 1000
            self.cost_lines = self.qext_values * float(self.specCostInput.text())
            self.total_cost = round(np.sum(self.cost_lines), 0)

        self.accept()
    
class WeightDialog(QDialog):
    """
    A QDialog subclass for setting weights for optimization.

    Attributes:
        wgk_input (QLineEdit): Input field for the weight of heat generation costs.
        co2_input (QLineEdit): Input field for the weight of specific CO2 emissions.
        pe_input (QLineEdit): Input field for the weight of the primary energy factor.
        button_box (QDialogButtonBox): Dialog button box for OK and Cancel buttons.
    """
    
    def __init__(self):
        """
        Initializes the WeightDialog.
        """
        super().__init__()
        
        self.setWindowTitle("Gewichte für Optimierung festlegen")
        
        self.wgk_input = QLineEdit("1.0", self)
        self.wgk_input.setToolTip("Geben Sie das Gewicht für die Wärmegestehungskosten ein (z.B. 1.0 für höchste Priorität oder 0.0 für keine Berücksichtigung).")

        self.co2_input = QLineEdit("0.0", self)
        self.co2_input.setToolTip("Geben Sie das Gewicht für die spezifischen CO2-Emissionen ein (z.B. 1.0 für höchste Priorität oder 0.0 für keine Berücksichtigung).")

        self.pe_input = QLineEdit("0.0", self)
        self.pe_input.setToolTip("Geben Sie das Gewicht für den Primärenergiefaktor ein (z.B. 1.0 für höchste Priorität oder 0.0 für keine Berücksichtigung).")

        form_layout = QFormLayout()
        form_layout.addRow("Wärmegestehungskosten", self.wgk_input)
        form_layout.addRow("Spezifische Emissionen", self.co2_input)
        form_layout.addRow("Primärenergiefaktor", self.pe_input)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.button_box)
        
        self.setLayout(layout)
    
    def get_weights(self):
        """
        Gets the weights from the input fields.

        Returns:
            dict: A dictionary with weights for heat generation costs, CO2 emissions, and primary energy factor.
        """
        try:
            wgk_weight = float(self.wgk_input.text())
        except ValueError:
            wgk_weight = 0.0

        try:
            co2_weight = float(self.co2_input.text())
        except ValueError:
            co2_weight = 0.0
        
        try:
            pe_weight = float(self.pe_input.text())
        except ValueError:
            pe_weight = 0.0

        return {
            'WGK_Gesamt': wgk_weight,
            'specific_emissions_Gesamt': co2_weight,
            'primärenergiefaktor_Gesamt': pe_weight
        }