"""
Filename: sensitivity_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Contains the SensitivityTab.
"""

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QLineEdit, QMessageBox
from PyQt5.QtCore import pyqtSignal
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

class SensitivityTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent
        self.results = {}

        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)
        
        self.initUI()

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)
        self.createInputFields()
        self.createPlotArea()
        self.setLayout(self.mainLayout)

    def createInputFields(self):
        inputLayout = QVBoxLayout()

        # Create input fields for sensitivity analysis ranges
        self.gasPriceRange = self.createRangeInputField("Gaspreisbereich (€): ", "€/MWh", "30", "60", "5")
        self.electricityPriceRange = self.createRangeInputField("Strompreisbereich (€): ", "€/MWh", "60", "120", "5")
        self.woodPriceRange = self.createRangeInputField("Holzpreisbereich (€): ", "€/MWh", "40", "80", "5")

        # Add a button to start the sensitivity analysis
        self.startButton = QPushButton("Sensitivitätsuntersuchung starten")
        self.startButton.clicked.connect(self.start_sensitivity_analysis)
        
        inputLayout.addLayout(self.gasPriceRange)
        inputLayout.addLayout(self.electricityPriceRange)
        inputLayout.addLayout(self.woodPriceRange)
        inputLayout.addWidget(self.startButton)

        self.mainLayout.addLayout(inputLayout)

    def createRangeInputField(self, label_text, unit_text, ll=10, ul=50, nP=5):
        layout = QVBoxLayout()
        label = QLabel(label_text)
        unit = QLabel(unit_text)
        rangeLayout = QHBoxLayout()
        lowerLimit = QLineEdit()
        upperLimit = QLineEdit()
        numPoints = QLineEdit()
        # Standardwerte setzen
        lowerLimit.setText(str(ll))
        upperLimit.setText(str(ul))
        numPoints.setText(str(nP))
        rangeLayout.addWidget(QLabel("von"))
        rangeLayout.addWidget(lowerLimit)
        rangeLayout.addWidget(QLabel("bis"))
        rangeLayout.addWidget(upperLimit)
        rangeLayout.addWidget(QLabel("Anzahl"))
        rangeLayout.addWidget(numPoints)
        rangeLayout.addWidget(unit)
        layout.addWidget(label)
        layout.addLayout(rangeLayout)
        return layout

    def createPlotArea(self):
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(500, 500)
        self.mainLayout.addWidget(self.canvas)

    def start_sensitivity_analysis(self):
        gas_range = self.parse_range(self.gasPriceRange)
        electricity_range = self.parse_range(self.electricityPriceRange)
        wood_range = self.parse_range(self.woodPriceRange)

        if gas_range and electricity_range and wood_range:
            self.parent.sensitivity(gas_range, electricity_range, wood_range)

    def parse_range(self, layout):
        try:
            lower = float(layout.itemAt(1).itemAt(1).widget().text())
            upper = float(layout.itemAt(1).itemAt(3).widget().text())
            num_points = int(layout.itemAt(1).itemAt(5).widget().text())
            if num_points <= 0:
                raise ValueError("Die Anzahl der Punkte muss größer als 0 sein.")
            return lower, upper, num_points
        except ValueError:
            QMessageBox.warning(self, "Ungültiger Bereich", "Bitte geben Sie einen gültigen Bereich ein (Format: von, bis, Anzahl).")
            return None

    def plotSensitivity(self, results):
        self.figure.clear()
        ax = self.figure.add_subplot(111, projection='3d')

        gas_prices = [res['gas_price'] for res in results]
        electricity_prices = [res['electricity_price'] for res in results]
        wood_prices = [res['wood_price'] for res in results]
        wgk = [res['WGK_Gesamt'] + res['wgk_heat_pump_electricity'] for res in results]

        sc = ax.scatter(gas_prices, electricity_prices, wood_prices, c=wgk, cmap='viridis', marker='o')
        ax.set_xlabel('Gaspreis (€/MWh)')
        ax.set_ylabel('Strompreis (€/MWh)')
        ax.set_zlabel('Holzpreis (€/MWh)')
        ax.set_title('Gesamtwärmegestehungskosten (€/MWh)')

        # Add color bar
        cbar = plt.colorbar(sc, ax=ax, pad=0.1)
        cbar.set_label('Wärmegestehungskosten (€/MWh)')
        
        self.canvas.draw()

    def plotSensitivitySurface(self, results):
        self.figure.clear()
        ax = self.figure.add_subplot(111, projection='3d')

        wood_prices = np.array([res['wood_price'] for res in results])
        unique_wood_prices = np.unique(wood_prices)

        colors = plt.cm.viridis(np.linspace(0, 1, len(unique_wood_prices)))

        for i, wood_price in enumerate(unique_wood_prices):
            subset_results = [res for res in results if res['wood_price'] == wood_price]
            gas_prices = np.array([res['gas_price'] for res in subset_results])
            electricity_prices = np.array([res['electricity_price'] for res in subset_results])
            wgk = np.array([res['WGK_Gesamt'] + res['wgk_heat_pump_electricity'] for res in subset_results])

            # Create a grid for surface plot
            grid_x, grid_y = np.meshgrid(
                np.linspace(gas_prices.min(), gas_prices.max(), len(set(gas_prices))),
                np.linspace(electricity_prices.min(), electricity_prices.max(), len(set(electricity_prices)))
            )

            # Interpolating the wgk data to fit into the grid
            grid_wgk = griddata((gas_prices, electricity_prices), wgk, (grid_x, grid_y), method='linear')

            # Plot the surface
            surf = ax.plot_surface(grid_x, grid_y, grid_wgk, color=colors[i], edgecolor='none', alpha=0.7, label=f'Holzpreis: {wood_price} €/MWh')

        ax.set_xlabel('Gaspreis (€/MWh)')
        ax.set_ylabel('Strompreis (€/MWh)')
        ax.set_zlabel('Wärmegestehungskosten (€/MWh)')
        ax.set_title('Gesamtwärmegestehungskosten (€/MWh)')

        # Add legend for the wood prices
        custom_lines = [plt.Line2D([0], [0], color=colors[i], lw=4) for i in range(len(unique_wood_prices))]
        ax.legend(custom_lines, [f'Holzpreis: {price} €/MWh' for price in unique_wood_prices])

        self.canvas.draw()