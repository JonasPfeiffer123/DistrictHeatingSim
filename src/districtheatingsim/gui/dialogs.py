"""GUI Dialogs Module
==================

Dialog windows for user input and configuration.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os
import re

from PyQt6.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, QPushButton, QHBoxLayout, QFileDialog
from PyQt6.QtCore import Qt

from districtheatingsim.utilities.utilities import get_resource_path


def _extract_try_location(path: str) -> str:
    """
    Extract the geographic location from a TRY file path.

    Tries two methods in order:
    1. Filename pattern ``TRY????_LLLLLLWWWWWW_*.dat`` (lat = LLLLLL/10000, lon = WWWWWW/10000)
    2. File header ``Rechtswert`` / ``Hochwert`` lines → convert EPSG:3034 (LCC) → WGS84

    :param path: Path to the TRY .dat file
    :type path: str
    :return: Human-readable location string, e.g. ``"51.1676 °N, 14.4222 °E"``
    :rtype: str
    """
    # 1. Filename-based extraction
    m = re.search(r'_(\d{6})(\d{6})_', os.path.basename(path))
    if m:
        lat = int(m.group(1)) / 10000
        lon = int(m.group(2)) / 10000
        return f"{lat:.4f} °N, {lon:.4f} °E"

    # 2. Header-based extraction (Lambert Conformal Conic → WGS84)
    try:
        rw = hw = None
        with open(path, "r", encoding="latin-1", errors="replace") as f:
            for line in f:
                if line.startswith("Rechtswert"):
                    rw = float(line.split(":")[1].split()[0])
                elif line.startswith("Hochwert"):
                    hw = float(line.split(":")[1].split()[0])
                if rw is not None and hw is not None:
                    break
        if rw is not None and hw is not None:
            from pyproj import Transformer
            t = Transformer.from_crs("EPSG:3034", "EPSG:4326", always_xy=True)
            lon, lat = t.transform(rw, hw)
            return f"{lat:.4f} °N, {lon:.4f} °E"
    except Exception:
        pass

    return ""

class TemperatureDataDialog(QDialog):
    """
    Dialog for selecting TRY (Test Reference Year) weather data files.

    .. note::
       Simple file selection dialog for weather data input with default path.
    """

    def __init__(self, parent=None):
        """
        Initialize temperature data dialog.

        :param parent: Parent widget, defaults to None
        :type parent: QWidget, optional
        """
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """
        Initialize the user interface components with file selection controls.

        .. note::
           Creates description label with DWD link, file input field with default TRY path, and OK/Cancel buttons.
        """
        self.setWindowTitle("Testreferenzjahr-Datei auswählen")
        self.resize(600, 200)

        self.main_layout = QVBoxLayout(self)

        # Description label with DWD link
        self.descriptionLabel = QLabel(
            "Bitte wählen Sie die Datei des Testreferenzjahres (TRY) aus, die Sie verwenden möchten.<br>"
            "Testreferenzjahre können unter <a href='https://www.dwd.de/DE/leistungen/testreferenzjahre/testreferenzjahre.html'>"
            "https://www.dwd.de/DE/leistungen/testreferenzjahre/testreferenzjahre.html</a> bezogen werden.<br>"
            "Es ist jedoch eine Registrierung beim DWD notwendig", self)
        self.descriptionLabel.setWordWrap(True)
        self.descriptionLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.descriptionLabel)

        # File input controls
        self.input_layout = QHBoxLayout()

        self.temperatureDataFileLabel = QLabel("TRY-Datei:", self)
        self.temperatureDataFileInput = QLineEdit(self)
        self.temperatureDataFileInput.setText(
            get_resource_path(os.path.join("data", "TRY", "TRY_511676144222", "TRY2015_511676144222_Jahr.dat"))
        )
        self.selectTRYFileButton = QPushButton('TRY-Datei auswählen')
        self.selectTRYFileButton.clicked.connect(lambda: self.selectFilename(self.temperatureDataFileInput))

        self.input_layout.addWidget(self.temperatureDataFileLabel)
        self.input_layout.addWidget(self.temperatureDataFileInput)
        self.input_layout.addWidget(self.selectTRYFileButton)

        self.main_layout.addLayout(self.input_layout)

        # Location label (updated whenever the file path changes)
        self.locationLabel = QLabel("", self)
        self.locationLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.locationLabel)
        self.temperatureDataFileInput.textChanged.connect(self._update_location_label)
        self._update_location_label(self.temperatureDataFileInput.text())

        # OK/Cancel buttons
        self.buttonLayout = QHBoxLayout()
        okButton = QPushButton("OK", self)
        cancelButton = QPushButton("Abbrechen", self)
        
        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        
        self.buttonLayout.addWidget(okButton)
        self.buttonLayout.addWidget(cancelButton)

        self.main_layout.addLayout(self.buttonLayout)

    def _update_location_label(self, path: str):
        """Update the location label from the given TRY file path."""
        loc = _extract_try_location(path) if path else ""
        if loc:
            self.locationLabel.setText(f"Standort: {loc}")
        else:
            self.locationLabel.setText("")

    def selectFilename(self, lineEdit):
        """
        Open file dialog and set selected path to line edit.

        :param lineEdit: Target line edit widget
        :type lineEdit: QLineEdit
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            lineEdit.setText(filename)

    def getValues(self):
        """
        Get dialog values.

        :return: Dictionary with TRY filename
        :rtype: dict
        """
        return {
            'TRY-filename': self.temperatureDataFileInput.text()
        }

class HeatPumpDataDialog(QDialog):
    """
    Dialog for selecting heat pump COP data files with inline Kennfeld visualisation.

    The dialog embeds a matplotlib heatmap that updates whenever a new CSV is
    selected, so the user can immediately judge whether the data looks plausible.

    CSV format expected: first row = supply temperatures (header), first column =
    source/ambient temperatures, matrix values = COP.  Zero entries are treated as
    not feasible and rendered distinctly (white/grey).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("COP-Daten-Verwaltung")
        self.resize(620, 560)

        mainLayout = QVBoxLayout(self)

        # File input row
        fileRow = QHBoxLayout()
        self.heatPumpDataFileLabel = QLabel("CSV-Datei mit Wärmepumpenkennfeld:")
        self.heatPumpDataFileInput = QLineEdit()
        self.heatPumpDataFileInput.setText(get_resource_path("data/COP/Kennlinien WP.csv"))
        self.selectCOPFileButton = QPushButton("CSV-Datei auswählen")
        self.selectCOPFileButton.clicked.connect(lambda: self.selectFilename(self.heatPumpDataFileInput))

        fileRow.addWidget(self.heatPumpDataFileLabel)
        fileRow.addWidget(self.heatPumpDataFileInput)
        fileRow.addWidget(self.selectCOPFileButton)
        mainLayout.addLayout(fileRow)

        # Kennfeld canvas
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

        self._fig = Figure(figsize=(5.5, 3.8), tight_layout=True)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._colorbar = None
        mainLayout.addWidget(self._canvas)

        # OK/Cancel buttons
        buttonLayout = QHBoxLayout()
        okButton = QPushButton("OK")
        cancelButton = QPushButton("Abbrechen")
        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)
        mainLayout.addLayout(buttonLayout)

        self.setLayout(mainLayout)

        # Wire up live preview
        self.heatPumpDataFileInput.textChanged.connect(self._update_kennfeld)
        self._update_kennfeld(self.heatPumpDataFileInput.text())

    # ------------------------------------------------------------------

    def _update_kennfeld(self, path: str):
        """Re-draw the COP heatmap for *path*. Silently clears on any error."""
        import numpy as np

        self._ax.clear()
        try:
            import pandas as pd
            df = pd.read_csv(path, sep=";", header=0, index_col=0)
            df = df.apply(pd.to_numeric, errors="coerce").fillna(0)

            data = df.values.astype(float)
            supply_temps = [str(c) for c in df.columns]
            source_temps = [str(i) for i in df.index]

            # Mask zero / infeasible cells
            masked = np.ma.masked_where(data == 0, data)

            cmap = self._fig.get_facecolor()  # inherit bg
            im = self._ax.imshow(
                masked, aspect="auto", origin="lower",
                cmap="RdYlGn", vmin=1.0, vmax=7.0,
            )

            # Annotate each cell
            for r in range(data.shape[0]):
                for c in range(data.shape[1]):
                    val = data[r, c]
                    if val > 0:
                        self._ax.text(c, r, f"{val:.1f}", ha="center", va="center",
                                      fontsize=7, color="black")

            self._ax.set_xticks(range(len(supply_temps)))
            self._ax.set_xticklabels(supply_temps, fontsize=8)
            self._ax.set_yticks(range(len(source_temps)))
            self._ax.set_yticklabels(source_temps, fontsize=8)
            self._ax.set_xlabel("Vorlauftemperatur [°C]", fontsize=9)
            self._ax.set_ylabel("Quelltemperatur [°C]", fontsize=9)
            self._ax.set_title("COP-Kennfeld (weiß = nicht realisierbar)", fontsize=9)

            if self._colorbar is None:
                self._colorbar = self._fig.colorbar(im, ax=self._ax, label="COP")
            else:
                self._colorbar.update_normal(im)
            self._ax.set_visible(True)

        except Exception:
            self._ax.set_visible(False)
            if self._colorbar is not None:
                self._colorbar.remove()
                self._colorbar = None

        self._canvas.draw_idle()

    # ------------------------------------------------------------------

    def selectFilename(self, lineEdit):
        """Open file dialog and set selected path to line edit."""
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "CSV-Dateien (*.csv)")
        if filename:
            lineEdit.setText(filename)

    def getValues(self):
        """
        Get dialog values.

        :return: Dictionary with COP filename
        :rtype: dict
        """
        return {
            'COP-filename': self.heatPumpDataFileInput.text()
        }