"""
Solar-thermal technology dialog (hand-written: includes a 3D collector-orientation
plot). Moved verbatim from ``_04_technology_dialogs.py``; not yet schema-driven.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QLineEdit, QLabel, QComboBox, QGroupBox, QHBoxLayout, QFormLayout, QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import art3d


class SolarThermalDialog(QWidget):
    """
    A dialog for inputting data specific to solar thermal technology.

    Attributes:
        tech_data (dict): The data for the solar thermal technology.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the SolarThermalDialog with the given data.

        :param tech_data: The data for the solar thermal technology
        :type tech_data: dict or None
        """
        super(SolarThermalDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface for the dialog.
        """
        main_layout = QHBoxLayout()  # Main layout as QHBoxLayout
        input_layout = QVBoxLayout()  # Layout for inputs

        # Technical Data GroupBox
        tech_groupbox = QGroupBox("Technische Daten")
        tech_layout = QFormLayout()

        self.areaSInput = QLineEdit(self)
        self.areaSInput.setText(str(self.tech_data.get('bruttofläche_STA', "200")))
        tech_layout.addRow(QLabel("Kollektorbruttofläche in m²"), self.areaSInput)

        self.vsInput = QLineEdit(self)
        self.vsInput.setText(str(self.tech_data.get('vs', "20")))
        tech_layout.addRow(QLabel("Solarspeichervolumen in m³"), self.vsInput)

        self.typeInput = QComboBox(self)
        self.techOptions = ["Vakuumröhrenkollektor", "Flachkollektor"]
        self.typeInput.addItems(self.techOptions)
        if 'Typ' in self.tech_data:
            current_type_index = self.techOptions.index(self.tech_data['Typ'])
            self.typeInput.setCurrentIndex(current_type_index)
        tech_layout.addRow(QLabel("Kollektortyp"), self.typeInput)

        self.TsmaxInput = QLineEdit(self)
        self.TsmaxInput.setText(str(self.tech_data.get('Tsmax', "90")))
        tech_layout.addRow(QLabel("Maximale Speichertemperatur in °C"), self.TsmaxInput)

        self.LongitudeInput = QLineEdit(self)
        self.LongitudeInput.setText(str(self.tech_data.get('Longitude', "-14.4222")))
        tech_layout.addRow(QLabel("Longitude des Erzeugerstandortes"), self.LongitudeInput)

        self.STD_LongitudeInput = QLineEdit(self)
        self.STD_LongitudeInput.setText(str(self.tech_data.get('STD_Longitude', "15")))
        tech_layout.addRow(QLabel("STD_Longitude des Erzeugerstandortes"), self.STD_LongitudeInput)

        self.LatitudeInput = QLineEdit(self)
        self.LatitudeInput.setText(str(self.tech_data.get('Latitude', "51.1676")))
        tech_layout.addRow(QLabel("Latitude des Erzeugerstandortes"), self.LatitudeInput)

        self.East_West_collector_azimuth_angleInput = QLineEdit(self)
        self.East_West_collector_azimuth_angleInput.setText(str(self.tech_data.get('East_West_collector_azimuth_angle', "0")))
        tech_layout.addRow(QLabel("Azimuth-Ausrichtung des Kollektors in °"), self.East_West_collector_azimuth_angleInput)

        self.Collector_tilt_angleInput = QLineEdit(self)
        self.Collector_tilt_angleInput.setText(str(self.tech_data.get('Collector_tilt_angle', "36")))
        tech_layout.addRow(QLabel("Neigungswinkel des Kollektors in ° (0-90)"), self.Collector_tilt_angleInput)

        self.Tm_rlInput = QLineEdit(self)
        self.Tm_rlInput.setText(str(self.tech_data.get('Tm_rl', "60")))
        tech_layout.addRow(QLabel("Startwert Rücklauftemperatur in Speicher in °C"), self.Tm_rlInput)

        self.QsaInput = QLineEdit(self)
        self.QsaInput.setText(str(self.tech_data.get('Qsa', "0")))
        tech_layout.addRow(QLabel("Startwert Speicherfüllstand"), self.QsaInput)

        self.Vorwärmung_KInput = QLineEdit(self)
        self.Vorwärmung_KInput.setText(str(self.tech_data.get('Vorwärmung_K', "8")))
        tech_layout.addRow(QLabel("Mögliche Abweichung von Solltemperatur bei Vorwärmung"), self.Vorwärmung_KInput)

        self.DT_WT_Solar_KInput = QLineEdit(self)
        self.DT_WT_Solar_KInput.setText(str(self.tech_data.get('DT_WT_Solar_K', "5")))
        tech_layout.addRow(QLabel("Grädigkeit Wärmeübertrager Kollektor/Speicher"), self.DT_WT_Solar_KInput)

        self.DT_WT_Netz_KInput = QLineEdit(self)
        self.DT_WT_Netz_KInput.setText(str(self.tech_data.get('DT_WT_Netz_K', "5")))
        tech_layout.addRow(QLabel("Grädigkeit Wärmeübertrager Speicher/Netz"), self.DT_WT_Netz_KInput)

        tech_groupbox.setLayout(tech_layout)
        input_layout.addWidget(tech_groupbox)

        # Cost GroupBox
        cost_groupbox = QGroupBox("Kosten")
        cost_layout = QFormLayout()

        self.vscostInput = QLineEdit(self)
        self.vscostInput.setText(str(self.tech_data.get('kosten_speicher_spez', "750")))
        cost_layout.addRow(QLabel("spez. Kosten Solarspeicher in €/m³"), self.vscostInput)

        self.areaScostfkInput = QLineEdit(self)
        self.areaScostfkInput.setText(str(self.tech_data.get('kosten_fk_spez', "430")))
        cost_layout.addRow(QLabel("spez. Kosten Flachkollektor in €/m²"), self.areaScostfkInput)

        self.areaScostvrkInput = QLineEdit(self)
        self.areaScostvrkInput.setText(str(self.tech_data.get('kosten_vrk_spez', "590")))
        cost_layout.addRow(QLabel("spez. Kosten Vakuumröhrenkollektor in €/m²"), self.areaScostvrkInput)

        cost_groupbox.setLayout(cost_layout)
        input_layout.addWidget(cost_groupbox)

        # Optimization Parameters GroupBox
        opt_groupbox = QGroupBox("Optimierungsparameter")
        opt_layout = QFormLayout()

        self.minVolumeInput = QLineEdit(self)
        self.minVolumeInput.setText(str(self.tech_data.get('opt_volume_min', "1")))
        opt_layout.addRow(QLabel("Untere Grenze Speichervolumen Optimierung"), self.minVolumeInput)

        self.maxVolumeInput = QLineEdit(self)
        self.maxVolumeInput.setText(str(self.tech_data.get('opt_volume_max', "200")))
        opt_layout.addRow(QLabel("Obere Grenze Speichervolumen Optimierung"), self.maxVolumeInput)

        self.minAreaInput = QLineEdit(self)
        self.minAreaInput.setText(str(self.tech_data.get('opt_area_min', "1")))
        opt_layout.addRow(QLabel("Untere Grenze Kollektorfläche Optimierung"), self.minAreaInput)

        self.maxAreaInput = QLineEdit(self)
        self.maxAreaInput.setText(str(self.tech_data.get('opt_area_max', "2000")))
        opt_layout.addRow(QLabel("Obere Grenze Kollektorfläche Optimierung"), self.maxAreaInput)

        opt_groupbox.setLayout(opt_layout)
        input_layout.addWidget(opt_groupbox)

        main_layout.addLayout(input_layout)  # Add input layout to main layout

        # Visualization
        vis_layout = QVBoxLayout()
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111, projection='3d')
        self.canvas = FigureCanvas(self.figure)
        vis_layout.addWidget(self.canvas)

        main_layout.addLayout(vis_layout)  # Add visualization layout to main layout

        self.setLayout(main_layout)
        self.updateVisualization()

        # Connect input changes to the visualization update
        self.East_West_collector_azimuth_angleInput.textChanged.connect(self.updateVisualization)
        self.Collector_tilt_angleInput.textChanged.connect(self.updateVisualization)

    def updateVisualization(self):
        """
        Updates the visualization of the collector orientation.
        """
        try:
            azimuth = float(self.East_West_collector_azimuth_angleInput.text())
            tilt = float(self.Collector_tilt_angleInput.text())
        except ValueError:
            azimuth = 0
            tilt = 0

        self.ax.clear()

        # Draw the ground plane
        xx, yy = np.meshgrid(range(-180, 181, 45), range(-180, 181, 45))
        zz = np.zeros_like(xx)
        self.ax.plot_surface(xx, yy, zz, color='green', alpha=0.5)

        # Define the corners of the collector plane
        length = 50  # Length of the collector for better visibility
        width = 30   # Width of the collector for better visibility

        # Calculate coordinates of the collector plane
        x1 = length * np.cos(np.radians(azimuth)) * np.cos(np.radians(tilt))
        y1 = length * np.sin(np.radians(azimuth)) * np.cos(np.radians(tilt))
        z1 = length * np.sin(np.radians(tilt))

        collector_corners = np.array([
            [0, 0, 0],
            [x1, y1, z1],
            [x1 - width * np.sin(np.radians(azimuth)), y1 + width * np.cos(np.radians(azimuth)), z1],
            [-width * np.sin(np.radians(azimuth)), width * np.cos(np.radians(azimuth)), 0]
        ])

        # Create the collector plane
        collector_plane = art3d.Poly3DCollection([collector_corners], facecolors='blue', linewidths=1, edgecolors='r', alpha=0.75)
        self.ax.add_collection3d(collector_plane)

        # Draw a vector representing the normal to the collector plane
        normal_x = np.cos(np.radians(tilt)) * np.cos(np.radians(azimuth))
        normal_y = np.cos(np.radians(tilt)) * np.sin(np.radians(azimuth))
        normal_z = np.sin(np.radians(tilt))
        self.ax.quiver(0, 0, 0, normal_x, normal_y, normal_z, length=10, color='red')

        # Set plot limits
        self.ax.set_xlim([-180, 180])
        self.ax.set_ylim([-180, 180])
        self.ax.set_zlim([0, 100])

        # Label axes with angles
        self.ax.set_xticks(np.arange(-180, 181, 45))
        self.ax.set_yticks(np.arange(-180, 181, 45))
        self.ax.set_zticks(np.arange(0, 101, 10))

        self.ax.set_xlabel('X (Azimut in °)')
        self.ax.set_ylabel('Y (Azimut in °)')
        self.ax.set_zlabel('Z (Höhe in m)')

        # Add compass directions
        self.ax.text(180, 0, 0, 'Nord', color='black', fontsize=12)
        self.ax.text(-180, 0, 0, 'Süd', color='black', fontsize=12)
        self.ax.text(0, 180, 0, 'Ost', color='black', fontsize=12)
        self.ax.text(0, -180, 0, 'West', color='black', fontsize=12)

        self.ax.set_title(f"Kollektorausrichtung\nAzimut: {azimuth}°, Neigung: {tilt}°")
        self.canvas.draw()

    def getInputs(self):
        """
        Retrieves the input data from the dialog.

        :return: The input data
        :rtype: dict
        """
        inputs = {
            'bruttofläche_STA': float(self.areaSInput.text()),
            'vs': float(self.vsInput.text()),
            'Typ': self.typeInput.itemText(self.typeInput.currentIndex()),
            'Tsmax': float(self.TsmaxInput.text()),
            'Longitude': float(self.LongitudeInput.text()),
            'STD_Longitude': int(self.STD_LongitudeInput.text()),
            'Latitude': float(self.LatitudeInput.text()),
            'East_West_collector_azimuth_angle': float(self.East_West_collector_azimuth_angleInput.text()),
            'Collector_tilt_angle': float(self.Collector_tilt_angleInput.text()),
            'Tm_rl': float(self.Tm_rlInput.text()),
            'Qsa': float(self.QsaInput.text()),
            'Vorwärmung_K': float(self.Vorwärmung_KInput.text()),
            'DT_WT_Solar_K': float(self.DT_WT_Solar_KInput.text()),
            'DT_WT_Netz_K': float(self.DT_WT_Netz_KInput.text()),
            'kosten_speicher_spez': float(self.vscostInput.text()),
            'kosten_fk_spez': float(self.areaScostfkInput.text()),
            'kosten_vrk_spez': float(self.areaScostvrkInput.text()),
            'opt_volume_min': float(self.minVolumeInput.text()),
            'opt_volume_max': float(self.maxVolumeInput.text()),
            'opt_area_min': float(self.minAreaInput.text()),
            'opt_area_max': float(self.maxAreaInput.text())
        }
        return inputs
