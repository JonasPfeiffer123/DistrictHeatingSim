"""
Filename: mix_design_dialogs.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
Description: Contains the Dialogs for the MixDesignTab.
"""

import sys
import os

import numpy as np
import geopandas as gpd

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, \
    QComboBox, QTableWidget, QPushButton, QTableWidgetItem, \
    QHBoxLayout, QMessageBox, QMenu, QInputDialog, QFormLayout, QDialogButtonBox
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

# defines the map path
def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # When the application is frozen, the base path is the temp folder where PyInstaller extracts everything
        base_path = sys._MEIPASS
    else:
        # When the application is not frozen, the base path is the folder where the main script is located
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, relative_path)

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
            'Gaspreis in €/MWh': float(self.gaspreisInput.text()),
            'Strompreis in €/MWh': float(self.strompreisInput.text()),
            'Holzpreis in €/MWh': float(self.holzpreisInput.text()),
            'BEW-Förderung': self.BEWComboBox.currentText(),
            'Kapitalzins in %': float(self.kapitalzinsInput.text()),
            'Preissteigerungsrate in %': float(self.preissteigerungsrateInput.text()),
            'Betrachtungszeitraum in a': int(self.betrachtungszeitraumInput.text()),
            'Stundensatz in €/h': float(self.stundensatzInput.text())
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
        self.filename = f"{self.base_path}\Wärmenetz\dimensioniertes Wärmenetz.geojson"
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

class NetInfrastructureDialog(QDialog):
    """
    A QDialog subclass for managing network infrastructure.

    Attributes:
        base_path (str): The base path for loading and saving data.
        infraObjects (list): A list of infrastructure objects.
        table (QTableWidget): The table widget for displaying infrastructure data.
        layout (QVBoxLayout): The main layout of the dialog.
        addButton (QPushButton): Button to add a new row.
        removeButton (QPushButton): Button to remove the selected row.
        berechneWärmenetzKostenButton (QPushButton): Button to calculate the cost of the heating network.
        berechneHausanschlussKostenButton (QPushButton): Button to calculate the cost of house connection stations.
    """
    
    def __init__(self, parent=None):
        """
        Initializes the NetInfrastructureDialog.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.base_path = None
        self.initUI()
        self.initDefaultValues()
        self.table.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.verticalHeader().customContextMenuRequested.connect(self.openHeaderContextMenu)

    def initUI(self):
        """
        Initializes the user interface components.
        """
        self.setWindowTitle("Netzinfrastruktur-Verwaltung")
        self.resize(800, 600)

        self.layout = QVBoxLayout(self)

        self.table = QTableWidget(self)
        self.infraObjects = ['Wärmenetz', 'Hausanschlussstationen', 'Druckhaltung', 'Hydraulik', 'Elektroinstallation', 'Planungskosten']
        self.table.setRowCount(len(self.infraObjects))
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['Kosten', 'T_N', 'F_inst', 'F_w_insp', 'Bedienaufwand'])
        self.table.setVerticalHeaderLabels(self.infraObjects)
        self.layout.addWidget(self.table)

        self.table.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.verticalHeader().customContextMenuRequested.connect(self.openHeaderContextMenu)

        self.addButton = QPushButton("Zeile hinzufügen", self)
        self.removeButton = QPushButton("Zeile entfernen", self)
        self.addButton.clicked.connect(self.addRow)
        self.removeButton.clicked.connect(self.removeRow)

        self.berechneWärmenetzKostenButton = QPushButton("Kosten Wärmenetz aus geoJSON berechnen", self)
        self.berechneWärmenetzKostenButton.clicked.connect(self.berechneWaermenetzKosten)
        self.layout.addWidget(self.berechneWärmenetzKostenButton)

        self.berechneHausanschlussKostenButton = QPushButton("Kosten Hausanschlusstationen aus geoJSON berechnen", self)
        self.berechneHausanschlussKostenButton.clicked.connect(self.berechneHausanschlussKosten)
        self.layout.addWidget(self.berechneHausanschlussKostenButton)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.addButton)
        buttonLayout.addWidget(self.removeButton)

        okButton = QPushButton("OK", self)
        cancelButton = QPushButton("Abbrechen", self)
        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)

        self.layout.addLayout(buttonLayout)

    def openHeaderContextMenu(self, position):
        """
        Opens the context menu for the vertical header.

        Args:
            position (QPoint): The position where the context menu should be opened.
        """
        menu = QMenu()
        renameAction = menu.addAction("Umbenennen")
        action = menu.exec_(self.table.verticalHeader().mapToGlobal(position))

        if action == renameAction:
            row = self.table.verticalHeader().logicalIndexAt(position)
            if row != -1:
                self.renameHeader(row)

    def renameHeader(self, row):
        """
        Renames the header item at the specified row.

        Args:
            row (int): The row index of the header item to rename.
        """
        newName, okPressed = QInputDialog.getText(self, "Name ändern", "Neuer Name:", QLineEdit.Normal, "")
        if okPressed and newName:
            self.table.verticalHeaderItem(row).setText(newName)
            self.infraObjects[row] = newName

    def addRow(self):
        """
        Adds a new row to the table.
        """
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        new_row_name = "Neues Objekt {}".format(row_count + 1)
        self.table.setVerticalHeaderItem(row_count, QTableWidgetItem(new_row_name))
        self.infraObjects.append(new_row_name)

    def removeRow(self):
        """
        Removes the selected row from the table.
        """
        current_row = self.table.currentRow()
        if current_row != -1:
            del self.infraObjects[current_row]
            self.table.removeRow(current_row)

    def initDefaultValues(self):
        """
        Initializes the table with default values.
        """
        defaultValues = {
            'Wärmenetz': {'kosten': "2000000", 't_n': "40", 'f_inst': "1", 'f_w_insp': "0", 'bedienaufwand': "5"},
            'Hausanschlussstationen': {'kosten': "100000", 't_n': "20", 'f_inst': "1", 'f_w_insp': "1", 'bedienaufwand': "2"},
            'Druckhaltung': {'kosten': "20000", 't_n': "20", 'f_inst': "1", 'f_w_insp': "1", 'bedienaufwand': "2"},
            'Hydraulik': {'kosten': "40000", 't_n': "40", 'f_inst': "1", 'f_w_insp': "0", 'bedienaufwand': "0"},
            'Elektroinstallation': {'kosten': "15000", 't_n': "15", 'f_inst': "1", 'f_w_insp': "1", 'bedienaufwand': "5"},
            'Planungskosten': {'kosten': "500000", 't_n': "20", 'f_inst': "0", 'f_w_insp': "0", 'bedienaufwand': "0"}
        }

        for i, obj in enumerate(self.infraObjects):
            for j, field in enumerate(['kosten', 't_n', 'f_inst', 'f_w_insp', 'bedienaufwand']):
                self.table.setItem(i, j, QTableWidgetItem(str(defaultValues[obj][field])))

    def updateTableValue(self, row, column, value):
        """
        Updates the value in the specified table cell.

        Args:
            row (int): The row index.
            column (int): The column index.
            value (Any): The value to set.
        """
        if 0 <= row < self.table.rowCount() and 0 <= column < self.table.columnCount():
            self.table.setItem(row, column, QTableWidgetItem(str(value)))
        else:
            print("Fehler: Ungültiger Zeilen- oder Spaltenindex.")

    def berechneWaermenetzKosten(self):
        """
        Opens the dialog to calculate the cost of the heating network and updates the table.
        """
        dialog = KostenBerechnungDialog(self, label="spez. Kosten Wärmenetz pro m_Trasse (inkl. Tiefbau) in €/m", value="1000", type="flow line")
        dialog.setWindowTitle("Kosten Wärmenetz berechnen")
        if dialog.exec_():
            cost_net = dialog.total_cost
            self.updateTableValue(row=0, column=0, value=cost_net)

    def berechneHausanschlussKosten(self):
        """
        Opens the dialog to calculate the cost of house connection stations and updates the table.
        """
        dialog = KostenBerechnungDialog(self, label="spez. Kosten Hausanschlussstationen pro kW max. Wärmebedarf in €/kW", value="250", type="HAST")
        dialog.setWindowTitle("Kosten Hausanschlussstationen berechnen")
        if dialog.exec_():
            cost_net = dialog.total_cost
            self.updateTableValue(row=1, column=0, value=cost_net)

    def getCurrentInfraObjects(self):
        """
        Gets the current list of infrastructure objects.

        Returns:
            list: The list of infrastructure objects.
        """
        return self.infraObjects

    def getValues(self):
        """
        Gets the values from the table.

        Returns:
            dict: A dictionary of values with keys in the format {object_field}.
        """
        values = {}
        for i, obj in enumerate(self.infraObjects):
            for j, field in enumerate(['kosten', 't_n', 'f_inst', 'f_w_insp', 'bedienaufwand']):
                key = f"{obj}_{field}"
                item = self.table.item(i, j)
                if item is not None:
                    values[key] = float(item.text())
                else:
                    values[key] = 0.0
        return values
    
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