"""
Geothermal technology dialog: schema-driven fields plus a 3D borehole-field plot.

The numeric fields come from :data:`_schemas.GEOTHERMAL` via :class:`SchemaDialog`;
this module only adds the matplotlib canvas and the live visualization, which
reads the relevant values from ``self._widgets``.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout

from districtheatingsim.gui.EnergySystemTab.technology_dialogs import _schemas as S
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._base import SchemaDialog


class GeothermalDialog(SchemaDialog):
    """Configure geothermal parameters with a live 3D borehole-field preview."""

    main_schema = S.GEOTHERMAL

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(self._build_fields())

        # Visualization
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111, projection="3d")
        self.canvas = FigureCanvas(self.figure)
        top.addWidget(self.canvas)

        outer.addLayout(top)

        # Connect input changes to the visualization update
        self._widgets["Fläche"].textChanged.connect(self.updateVisualization)
        self._widgets["Bohrtiefe"].textChanged.connect(self.updateVisualization)
        self._widgets["Abstand_Sonden"].textChanged.connect(self.updateVisualization)

        self.updateVisualization()

    def updateVisualization(self):
        """
        Updates the 3D visualization of the borehole configuration.
        """
        try:
            area = float(self._widgets["Fläche"].text())
            depth = float(self._widgets["Bohrtiefe"].text())
            distance = float(self._widgets["Abstand_Sonden"].text())
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
        for x, y in zip(x_positions.flatten(), y_positions.flatten(), strict=False):
            self.ax.plot([x, x], [y, y], [0, -depth], color="blue")

        # Set plot limits
        self.ax.set_xlim([0, side_length])
        self.ax.set_ylim([0, side_length])
        self.ax.set_zlim([-depth, 0])

        # Label axes
        self.ax.set_xlabel("X (m)")
        self.ax.set_ylabel("Y (m)")
        self.ax.set_zlabel("Z (Tiefe in m)")

        self.ax.set_title(f"Sondenkonfiguration\nFläche: {area} m², Tiefe: {depth} m, Abstand: {distance} m")
        self.canvas.draw()
