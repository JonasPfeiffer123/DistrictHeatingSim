"""
Geothermal technology dialog (hand-written: includes a 3D borehole-field plot).
Moved verbatim from ``_04_technology_dialogs.py``; not yet schema-driven.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from PyQt6.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QHBoxLayout, QFormLayout, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

import numpy as np
import matplotlib.pyplot as plt


class GeothermalDialog(QWidget):
    """
    A QWidget subclass for configuring geothermal parameters.

    Attributes:
        tech_data (dict): Dictionary containing initial values for the geothermal parameters.
        areaGInput (QLineEdit): Input field for the area of the borehole field.
        depthInput (QLineEdit): Input field for the depth of the boreholes.
        tempGInput (QLineEdit): Input field for the source temperature.
        distholeInput (QLineEdit): Input field for the distance between boreholes.
        costdethInput (QLineEdit): Input field for the specific drilling costs.
        spezPInput (QLineEdit): Input field for the specific extraction performance.
        VBHInput (QLineEdit): Input field for the full load hours of the borehole field.
        WPGcostInput (QLineEdit): Input field for the specific investment costs of the heat pump.
        figure (Figure): Matplotlib figure for plotting the borehole configuration.
        ax (Axes): Matplotlib axes for plotting.
        canvas (FigureCanvas): Canvas to display the Matplotlib figure.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the GeothermalDialog.

        :param tech_data: Dictionary containing initial values for the geothermal parameters
        :type tech_data: dict or None
        """
        super(GeothermalDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        form_layout = QFormLayout()

        self.areaGInput = QLineEdit(self)
        self.areaGInput.setText(str(self.tech_data.get('Fläche', "100")))
        form_layout.addRow(QLabel("Fläche Erdsondenfeld in m²"), self.areaGInput)

        self.depthInput = QLineEdit(self)
        self.depthInput.setText(str(self.tech_data.get('Bohrtiefe', "100")))
        form_layout.addRow(QLabel("Bohrtiefe Sonden in m"), self.depthInput)

        self.tempGInput = QLineEdit(self)
        self.tempGInput.setText(str(self.tech_data.get('Temperatur_Geothermie', "10")))
        form_layout.addRow(QLabel("Quelltemperatur in °C"), self.tempGInput)

        self.distholeInput = QLineEdit(self)
        self.distholeInput.setText(str(self.tech_data.get('Abstand_Sonden', "10")))
        form_layout.addRow(QLabel("Abstand Erdsonden in m"), self.distholeInput)

        self.costdethInput = QLineEdit(self)
        self.costdethInput.setText(str(self.tech_data.get('spez_Bohrkosten', "120")))
        form_layout.addRow(QLabel("spez. Bohrkosten pro Bohrmeter in €/m"), self.costdethInput)

        self.spezPInput = QLineEdit(self)
        self.spezPInput.setText(str(self.tech_data.get('spez_Entzugsleistung', "50")))
        form_layout.addRow(QLabel("spez. Entzugsleistung Untergrund in W/m"), self.spezPInput)

        self.VBHInput = QLineEdit(self)
        self.VBHInput.setText(str(self.tech_data.get('Vollbenutzungsstunden', "2400")))
        form_layout.addRow(QLabel("Vollbenutzungsstunden Sondenfeld in h"), self.VBHInput)

        self.WPGcostInput = QLineEdit(self)
        self.WPGcostInput.setText(str(self.tech_data.get('spezifische_Investitionskosten_WP', "1000")))
        form_layout.addRow(QLabel("spez. Investitionskosten Wärmepumpe in €/kW"), self.WPGcostInput)

        top_layout.addLayout(form_layout)

        # Visualization
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111, projection='3d')
        self.canvas = FigureCanvas(self.figure)
        top_layout.addWidget(self.canvas)

        main_layout.addLayout(top_layout)

        # Connect input changes to the visualization update
        self.areaGInput.textChanged.connect(self.updateVisualization)
        self.depthInput.textChanged.connect(self.updateVisualization)
        self.distholeInput.textChanged.connect(self.updateVisualization)

        self.setLayout(main_layout)
        self.updateVisualization()

    def updateVisualization(self):
        """
        Updates the 3D visualization of the borehole configuration.
        """
        try:
            area = float(self.areaGInput.text())
            depth = float(self.depthInput.text())
            distance = float(self.distholeInput.text())
        except ValueError:
            area = 100
            depth = 100
            distance = 10

        self.ax.clear()

        # Calculate the number of boreholes in a grid
        side_length = np.sqrt(area)
        num_holes_per_side = int(side_length / distance) + 1
        x_positions = np.linspace(0, side_length, num_holes_per_side)
        y_positions = np.linspace(0, side_length, num_holes_per_side)
        x_positions, y_positions = np.meshgrid(x_positions, y_positions)

        # Draw the boreholes
        for x, y in zip(x_positions.flatten(), y_positions.flatten()):
            self.ax.plot([x, x], [y, y], [0, -depth], color='blue')

        # Set plot limits
        self.ax.set_xlim([0, side_length])
        self.ax.set_ylim([0, side_length])
        self.ax.set_zlim([-depth, 0])

        # Label axes
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (Tiefe in m)')

        self.ax.set_title(f"Sondenkonfiguration\nFläche: {area} m², Tiefe: {depth} m, Abstand: {distance} m")
        self.canvas.draw()

    def getInputs(self):
        """
        Retrieves the input values from the user interface.

        :return: A dictionary containing the input values
        :rtype: dict
        """
        inputs = {
            'Fläche': float(self.areaGInput.text()),
            'Bohrtiefe': float(self.depthInput.text()),
            'Temperatur_Geothermie': float(self.tempGInput.text()),
            'Abstand_Sonden': float(self.distholeInput.text()),
            'spez_Bohrkosten': float(self.costdethInput.text()),
            'spez_Entzugsleistung': float(self.spezPInput.text()),
            'Vollbenutzungsstunden': float(self.VBHInput.text()),
            'spezifische_Investitionskosten_WP': float(self.WPGcostInput.text())
        }
        return inputs
