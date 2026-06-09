"""
Solar-thermal technology dialog: schema-driven fields (three group boxes, incl. a
collector-type dropdown) plus a 3D collector-orientation plot.

Fields come from :data:`_schemas.SOLAR_SECTIONS` via :class:`SchemaDialog`; this
module adds the matplotlib canvas and the live visualization, which reads the
azimuth / tilt values from ``self._widgets``.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import art3d

from districtheatingsim.gui.EnergySystemTab.technology_dialogs._base import SchemaDialog
from districtheatingsim.gui.EnergySystemTab.technology_dialogs import _schemas as S


class SolarThermalDialog(SchemaDialog):
    """Configure solar-thermal parameters with a live collector-orientation preview."""

    sections = S.SOLAR_SECTIONS

    def _build(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.addWidget(self._build_fields())  # three grouped sections

        # Visualization
        vis_layout = QVBoxLayout()
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111, projection='3d')
        self.canvas = FigureCanvas(self.figure)
        vis_layout.addWidget(self.canvas)
        main_layout.addLayout(vis_layout)

        self.updateVisualization()

        # Connect input changes to the visualization update
        self._widgets['East_West_collector_azimuth_angle'].textChanged.connect(self.updateVisualization)
        self._widgets['Collector_tilt_angle'].textChanged.connect(self.updateVisualization)

    def updateVisualization(self):
        """
        Updates the visualization of the collector orientation.
        """
        try:
            azimuth = float(self._widgets['East_West_collector_azimuth_angle'].text())
            tilt = float(self._widgets['Collector_tilt_angle'].text())
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
