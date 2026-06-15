"""
River-water heat-pump and AqvaHeat dialogs.

RiverHeatPump is schema-driven for its four plain numeric fields
(:data:`_schemas.RIVER`); it adds a custom river-temperature field plus a CSV
import button and overrides ``getInputs`` to emit ``Temperatur_FW_WP`` (scalar /
array / CSV). AqvaHeat currently has no inputs (empty schema).

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import numpy as np
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from districtheatingsim.gui.EnergySystemTab.technology_dialogs import _schemas as S
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._base import SchemaDialog


class RiverHeatPumpDialog(SchemaDialog):
    """Configure river heat-pump parameters with optional CSV river-temperature data."""

    main_schema = S.RIVER

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        form = QFormLayout()

        # First schema field (thermal capacity).
        self._populate(form, [self.main_schema[0]])

        # Custom river-temperature field + CSV button (between capacity and the rest).
        self.TFWInput = QLineEdit()
        if isinstance(self.tech_data.get("Temperatur_FW_WP"), (float, int)) or self.tech_data == {}:
            self.TFWInput.setText(str(self.tech_data.get("Temperatur_FW_WP", "10")))
        form.addRow(QLabel("Flusstemperatur in °C"), self.TFWInput)

        self.csvButton = QPushButton("CSV für Flusstemperatur wählen")
        self.csvButton.clicked.connect(self.openCSV)
        form.addRow(self.csvButton)

        # Remaining schema fields (dT, investment costs).
        self._populate(form, self.main_schema[1:])

        outer.addLayout(form)

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
        data = np.loadtxt(filename, delimiter=";", skiprows=1, usecols=1).astype(float)
        self.csvData = data
        QMessageBox.information(self, "CSV geladen", f"CSV-Datei {filename} erfolgreich geladen.")

    def getInputs(self):
        """
        Retrieves the input values, resolving the river temperature from the CSV
        import, an existing array, or the scalar field.
        """
        inputs = super().getInputs()
        try:
            if hasattr(self, "csvData"):
                inputs["Temperatur_FW_WP"] = self.csvData
            elif isinstance(self.tech_data.get("Temperatur_FW_WP"), (float, int)):
                inputs["Temperatur_FW_WP"] = float(self.TFWInput.text())
            elif isinstance(self.tech_data.get("Temperatur_FW_WP"), np.ndarray):
                inputs["Temperatur_FW_WP"] = self.tech_data.get("Temperatur_FW_WP")
            else:
                inputs["Temperatur_FW_WP"] = float(self.TFWInput.text())
        except ValueError:
            pass
        return inputs


class AqvaHeatDialog(SchemaDialog):
    """Configure AqvaHeat parameters (no inputs yet)."""

    main_schema = []
