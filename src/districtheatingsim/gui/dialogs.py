"""GUI Dialogs Module
==================

Dialog windows for user input and configuration.

:author: M.Eng. Jonas Pfeiffer
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from districtheatingsim.utilities.project_location import (
    DWD_TRY_URL,
    TRY_DISTANCE_WARNING_KM,
    distance_km,
    format_location,
    try_location,
)
from districtheatingsim.utilities.utilities import DEFAULT_COP_RESOURCE, DEFAULT_TRY_RESOURCE, get_resource_path


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
        self.project_location = None  # (lat, lon) of the project, set before showing the dialog
        self.initUI()

    def initUI(self):
        """
        Initialize the user interface components with file selection controls.

        .. note::
           Creates description label with DWD link, file input field with default TRY path, and OK/Cancel buttons.
        """
        self.setWindowTitle("Klimadaten (Testreferenzjahr) auswählen")
        self.resize(600, 200)

        self.main_layout = QVBoxLayout(self)

        # Description label with DWD link
        self.descriptionLabel = QLabel(
            "Bitte wählen Sie die Datei des Testreferenzjahres (TRY) für den Standort des Projekts.<br>"
            "Mitgeliefert ist nur ein TRY für die Oberlausitz (51,17° N, 14,42° O). Testreferenzjahre für "
            f"jeden Ort in Deutschland erhalten Sie kostenlos beim Deutschen Wetterdienst: "
            f"<a href='{DWD_TRY_URL}'>{DWD_TRY_URL}</a> (Registrierung nötig).",
            self,
        )
        self.descriptionLabel.setWordWrap(True)
        self.descriptionLabel.setOpenExternalLinks(True)
        self.descriptionLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.descriptionLabel)

        # File input controls
        self.input_layout = QHBoxLayout()

        self.temperatureDataFileLabel = QLabel("TRY-Datei:", self)
        self.temperatureDataFileInput = QLineEdit(self)
        self.temperatureDataFileInput.setText(get_resource_path(DEFAULT_TRY_RESOURCE))
        self.selectTRYFileButton = QPushButton("TRY-Datei auswählen")
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

    def set_project_location(self, location):
        """
        Show the distance of the TRY to the project (UT-H9).

        :param location: ``(lat, lon)`` of the project, or None if unknown.
        """
        self.project_location = location
        self._update_location_label(self.temperatureDataFileInput.text())

    def _update_location_label(self, path: str):
        """Update the location label from the given TRY file path."""
        point = try_location(path) if path else None
        if point is None:
            self.locationLabel.setText("")
            return
        text = f"Standort des TRY: {format_location(*point)}"
        style = ""
        if self.project_location is not None:
            distance = distance_km(point, self.project_location)
            text += f" – {distance:.0f} km vom Projektstandort ({format_location(*self.project_location)})"
            if distance > TRY_DISTANCE_WARNING_KM:
                text += "\nDieses TRY passt nicht zum Projekt."
                style = "color: #c62828; font-weight: bold;"
        self.locationLabel.setText(text)
        self.locationLabel.setStyleSheet(style)

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
        return {"TRY-filename": self.temperatureDataFileInput.text()}


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
        self.heatPumpDataFileInput.setText(get_resource_path(DEFAULT_COP_RESOURCE))
        self.selectCOPFileButton = QPushButton("CSV-Datei auswählen")
        self.selectCOPFileButton.clicked.connect(lambda: self.selectFilename(self.heatPumpDataFileInput))

        fileRow.addWidget(self.heatPumpDataFileLabel)
        fileRow.addWidget(self.heatPumpDataFileInput)
        fileRow.addWidget(self.selectCOPFileButton)
        mainLayout.addLayout(fileRow)

        # Kennfeld canvas: created on the first show. The dialog itself is built at application
        # start (its file path is needed), and matplotlib + the heatmap cost ~0.75 s there
        # (BACKLOG G8).
        self._fig = None
        self._ax = None
        self._canvas = None
        self._colorbar = None
        self._canvasHolder = QVBoxLayout()
        mainLayout.addLayout(self._canvasHolder)

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

        # Wire up live preview (drawn once the canvas exists, see showEvent)
        self.heatPumpDataFileInput.textChanged.connect(self._update_kennfeld)

    def showEvent(self, event):
        """Create the Kennfeld canvas on the first show and draw the current file."""
        self._ensure_canvas()
        super().showEvent(event)

    def _ensure_canvas(self):
        if self._fig is not None:
            return
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure

        self._fig = Figure(figsize=(5.5, 3.8), tight_layout=True)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvasHolder.addWidget(self._canvas)
        self._update_kennfeld(self.heatPumpDataFileInput.text())

    # ------------------------------------------------------------------

    def _update_kennfeld(self, path: str):
        """Re-draw the COP heatmap for *path*. Silently clears on any error."""
        if self._fig is None:  # not shown yet — drawn in _ensure_canvas
            return
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

            im = self._ax.imshow(
                masked,
                aspect="auto",
                origin="lower",
                cmap="RdYlGn",
                vmin=1.0,
                vmax=7.0,
            )

            # Annotate each cell
            for r in range(data.shape[0]):
                for c in range(data.shape[1]):
                    val = data[r, c]
                    if val > 0:
                        self._ax.text(c, r, f"{val:.1f}", ha="center", va="center", fontsize=7, color="black")

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
        return {"COP-filename": self.heatPumpDataFileInput.text()}
