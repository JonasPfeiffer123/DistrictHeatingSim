"""
Sensitivity Tab Module
======================

:author: M.Eng. Jonas Pfeiffer

Performing sensitivity analysis on heat generation costs based on varying parameters, with 3D visualization.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget
from scipy.interpolate import griddata


def price_range(base: float) -> tuple[str, str]:
    """Lower and upper end of a sensitivity range: 60 % and 140 % of the base price, in steps of 5."""
    lower = max(0.0, round(0.6 * base / 5) * 5)
    upper = max(lower + 5, round(1.4 * base / 5) * 5)
    return f"{lower:g}", f"{upper:g}"


class SensitivityTab(QWidget):
    """
    A QWidget subclass representing the SensitivityTab.

    Attributes:
        data_added (pyqtSignal): A signal that emits data as an object.
        data_manager (DataManager): An instance of the DataManager class for managing data.
        parent (QWidget): The parent widget.
        results (dict): A dictionary to store results.
    """

    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager, parent=None):
        """
        Initializes the SensitivityTab.

        :param data_manager: The data manager
        :type data_manager: DataManager
        :param parent: The parent widget
        :type parent: QWidget or None
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent
        self.results = {}

        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.variant_folder)

        self.initUI()

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default base path.

        :param new_base_path: The new base path
        :type new_base_path: str
        """
        self.base_path = new_base_path

    def initUI(self):
        """
        Initializes the UI components of the SensitivityTab.
        """
        self.mainLayout = QVBoxLayout(self)
        self.createInputFields()
        self.createPlotArea()
        self.setLayout(self.mainLayout)

    def createInputFields(self):
        """
        Creates the input fields for sensitivity analysis ranges.
        """
        inputLayout = QVBoxLayout()

        # Ranges around the base prices of the economic parameters (set_base_prices); the fixed
        # defaults (gas 30-60 €/MWh, electricity 60-120) did not even contain the base prices (UT-M16)
        self._base_prices = {}
        self.gasPriceRange = self.createRangeInputField("Gaspreis", "€/MWh", *price_range(70.0), "5")
        self.electricityPriceRange = self.createRangeInputField("Strompreis", "€/MWh", *price_range(150.0), "5")
        self.woodPriceRange = self.createRangeInputField("Holzpreis", "€/MWh", *price_range(50.0), "5")
        self._ranges = {
            "gas_price": self.gasPriceRange,
            "electricity_price": self.electricityPriceRange,
            "wood_price": self.woodPriceRange,
        }

        self.startButton = QPushButton("Sensitivitätsuntersuchung starten")
        self.startButton.clicked.connect(self.start_sensitivity_analysis)

        inputLayout.addLayout(self.gasPriceRange)
        inputLayout.addLayout(self.electricityPriceRange)
        inputLayout.addLayout(self.woodPriceRange)
        inputLayout.addWidget(self.startButton)

        self.mainLayout.addLayout(inputLayout)

    def createRangeInputField(self, label_text, unit_text, ll=10, ul=50, nP=5):
        """
        Creates a range input field for sensitivity analysis.

        :param label_text: The text for the label
        :type label_text: str
        :param unit_text: The text for the unit label
        :type unit_text: str
        :param ll: The lower limit
        :type ll: int or float
        :param ul: The upper limit
        :type ul: int or float
        :param nP: The number of points
        :type nP: int
        :return: The layout containing the input fields
        :rtype: QVBoxLayout
        """
        layout = QVBoxLayout()
        label = QLabel(label_text)
        unit = QLabel(unit_text)
        rangeLayout = QHBoxLayout()
        lowerLimit = QLineEdit()
        upperLimit = QLineEdit()
        numPoints = QLineEdit()
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

    def set_base_prices(self, economic_parameters: dict):
        """
        Centre the price ranges on the base prices of the economic parameters (60-140 %).

        Only when a base price changed - ranges the user edited for the same prices are kept.
        """
        names = {"gas_price": "Gaspreis", "electricity_price": "Strompreis", "wood_price": "Holzpreis"}
        for key, layout in self._ranges.items():
            try:
                base = float(economic_parameters[key])
            except (KeyError, TypeError, ValueError):
                continue
            label = layout.itemAt(0).widget()
            label.setText(f"{names[key]} (Basis {base:g} €/MWh)")
            if self._base_prices.get(key) == base:
                continue
            self._base_prices[key] = base
            lower, upper = price_range(base)
            layout.itemAt(1).itemAt(1).widget().setText(lower)
            layout.itemAt(1).itemAt(3).widget().setText(upper)

    def createPlotArea(self):
        """
        Creates the plot area for displaying graphs.
        """
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(500, 500)
        self.mainLayout.addWidget(self.canvas)

    def start_sensitivity_analysis(self):
        """
        Starts the sensitivity analysis based on the input ranges.
        """
        gas_range = self.parse_range(self.gasPriceRange)
        electricity_range = self.parse_range(self.electricityPriceRange)
        wood_range = self.parse_range(self.woodPriceRange)

        if gas_range and electricity_range and wood_range:
            self.parent.sensitivity(gas_range, electricity_range, wood_range)

    def parse_range(self, layout):
        """
        Parses the range input fields and returns the range values.

        :param layout: The layout containing the input fields
        :type layout: QVBoxLayout
        :return: The lower limit, upper limit, and number of points if valid, otherwise None
        :rtype: tuple or None
        """
        try:
            lower = float(layout.itemAt(1).itemAt(1).widget().text())
            upper = float(layout.itemAt(1).itemAt(3).widget().text())
            num_points = int(layout.itemAt(1).itemAt(5).widget().text())
            if num_points <= 0:
                raise ValueError("Die Anzahl der Punkte muss größer als 0 sein.")
            return lower, upper, num_points
        except ValueError:
            QMessageBox.warning(
                self, "Ungültiger Bereich", "Bitte geben Sie einen gültigen Bereich ein (Format: von, bis, Anzahl)."
            )
            return None

    def plotSensitivity(self, results):
        """
        Plots the sensitivity analysis results.

        :param results: The results of the sensitivity analysis
        :type results: list
        """
        self.figure.clear()
        ax = self.figure.add_subplot(111, projection="3d")

        gas_prices = [res["gas_price"] for res in results]
        electricity_prices = [res["electricity_price"] for res in results]
        wood_prices = [res["wood_price"] for res in results]
        wgk = [res["WGK_Gesamt"] + res["wgk_heat_pump_electricity"] for res in results]

        sc = ax.scatter(gas_prices, electricity_prices, wood_prices, c=wgk, cmap="viridis", marker="o")
        ax.set_xlabel("Gaspreis (€/MWh)")
        ax.set_ylabel("Strompreis (€/MWh)")
        ax.set_zlabel("Holzpreis (€/MWh)")
        ax.set_title("Gesamtwärmegestehungskosten (€/MWh)")

        cbar = plt.colorbar(sc, ax=ax, pad=0.1)
        cbar.set_label("Wärmegestehungskosten (€/MWh)")

        self.canvas.draw()

    def plotSensitivitySurface(self, results):
        """
        Plots the sensitivity analysis results as a surface plot.

        :param results: The results of the sensitivity analysis
        :type results: list
        """
        self.figure.clear()
        ax = self.figure.add_subplot(111, projection="3d")

        wood_prices = np.array([res["wood_price"] for res in results])
        unique_wood_prices = np.unique(wood_prices)

        colors = plt.cm.viridis(np.linspace(0, 1, len(unique_wood_prices)))

        for i, wood_price in enumerate(unique_wood_prices):
            subset_results = [res for res in results if res["wood_price"] == wood_price]
            gas_prices = np.array([res["gas_price"] for res in subset_results])
            electricity_prices = np.array([res["electricity_price"] for res in subset_results])
            wgk = np.array([res["WGK_Gesamt"] + res["wgk_heat_pump_electricity"] for res in subset_results])

            grid_x, grid_y = np.meshgrid(
                np.linspace(gas_prices.min(), gas_prices.max(), len(set(gas_prices))),
                np.linspace(electricity_prices.min(), electricity_prices.max(), len(set(electricity_prices))),
            )

            grid_wgk = griddata((gas_prices, electricity_prices), wgk, (grid_x, grid_y), method="linear")

            ax.plot_surface(
                grid_x,
                grid_y,
                grid_wgk,
                color=colors[i],
                edgecolor="none",
                alpha=0.7,
                label=f"Holzpreis: {wood_price} €/MWh",
            )

        ax.set_xlabel("Gaspreis (€/MWh)")
        ax.set_ylabel("Strompreis (€/MWh)")
        ax.set_zlabel("Wärmegestehungskosten (€/MWh)")
        ax.set_title("Gesamtwärmegestehungskosten (€/MWh)")

        # One legend below the plot: inside the 3D axes it covered the surfaces (UT-M16)
        custom_lines = [plt.Line2D([0], [0], color=colors[i], lw=4) for i in range(len(unique_wood_prices))]
        self.figure.legend(
            custom_lines,
            [f"Holzpreis {price:g} €/MWh" for price in unique_wood_prices],
            loc="lower center",
            ncol=min(5, len(unique_wood_prices)),
            frameon=False,
        )
        self.figure.subplots_adjust(left=0.02, right=0.98, top=0.93, bottom=0.12)

        self.canvas.draw()
