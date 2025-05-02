"""
Filename: _02_energy_system_dialogs.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-02
Description: Contains the Dialogs for the Energy System Tab.
"""

import os

import numpy as np
import geopandas as gpd

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, QComboBox, \
    QPushButton, QHBoxLayout, QMessageBox, QFormLayout, QDialogButtonBox

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

class EconomicParametersDialog(QDialog):
    """
    A QDialog subclass for inputting economic parameters.

    Attributes:
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
        self.initUI()
        self.initDefaultValues()
        self.validateInput()
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

    def initDefaultValues(self):
        """
        Initializes the input fields with default values.
        """
        self.gaspreisInput.setText("70")
        self.strompreisInput.setText("150")
        self.holzpreisInput.setText("50")
        self.kapitalzinsInput.setText("5")
        self.preissteigerungsrateInput.setText("3")
        self.betrachtungszeitraumInput.setText("20")
        self.stundensatzInput.setText("45")
        self.BEWComboBox.setCurrentIndex(0)  # Sets the selection to "Nein"

    def connectSignals(self):
        """
        Connects the signals of the input fields to the validation method.
        """
        self.gaspreisInput.textChanged.connect(self.validateInput)
        self.strompreisInput.textChanged.connect(self.validateInput)
        self.holzpreisInput.textChanged.connect(self.validateInput)
        self.preissteigerungsrateInput.textChanged.connect(self.validateInput)

    def validateInput(self):
        """
        Validates the input fields and updates the plot if valid.
        """
        gas_price = self.gaspreisInput.text()
        strom_price = self.strompreisInput.text()
        holz_price = self.holzpreisInput.text()
        kapitalzins = self.kapitalzinsInput.text()
        preissteigerungsrate = self.preissteigerungsrateInput.text()
        betrachtungszeitraum = self.betrachtungszeitraumInput.text()
        stundensatz = self.stundensatzInput.text()

        if not (gas_price and strom_price and holz_price and kapitalzins and preissteigerungsrate and betrachtungszeitraum):
            self.showErrorMessage("Alle Felder müssen ausgefüllt sein.")
            return

        try:
            float(gas_price)
            float(strom_price)
            float(holz_price)
            float(kapitalzins)
            float(preissteigerungsrate)
            int(betrachtungszeitraum)
            float(stundensatz)
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
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setText(message)
        msgBox.setWindowTitle("Fehler")
        msgBox.exec_()

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

    def getValues(self):
        """
        Gets the values from the input fields.

        Returns:
            dict: A dictionary containing the input values.
        """
        return {
            "gas_price": float(self.gaspreisInput.text()), # gas price in €/MWh
            "electricity_price": float(self.strompreisInput.text()), # electricity price in €/MWh
            "wood_price": float(self.holzpreisInput.text()), # wood price in €/MWh
            "capital_interest_rate": 1 + (float(self.kapitalzinsInput.text()) / 100), # capital interest rate
            "inflation_rate": 1 + (float(self.preissteigerungsrateInput.text()) / 100), # inflation rate
            "time_period": int(self.betrachtungszeitraumInput.text()), # evaluation period in years
            "hourly_rate": float(self.stundensatzInput.text()), # hourly wage rate for maintenance in €/h
            "subsidy_eligibility": self.BEWComboBox.currentText() # subsidy eligibility (Yes/No)
        }

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

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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