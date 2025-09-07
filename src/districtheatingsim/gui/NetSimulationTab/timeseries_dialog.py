"""
Time Series Dialog Module
=========================

Dialog for configuring time series calculation parameters.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-11
"""

import os
from PyQt6.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog,  \
    QPushButton, QHBoxLayout, QFileDialog, QMessageBox

class TimeSeriesCalculationDialog(QDialog):
    """
    Dialog for time series calculation configuration.
    """

    def __init__(self, base_path, parent=None):
        """
        Initialize time series calculation dialog.

        Parameters
        ----------
        base_path : str
            Base path for file dialogs.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.base_path = base_path
        self.parent = parent
        self.initUI()

    def initUI(self):
        """Initialize user interface components."""
        self.setWindowTitle("Zeitreihenrechnung")
        self.resize(400, 200)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Zeitschritte
        self.StartTimeStepLabel = QLabel("Zeitschritt Simulationsstart (min 0):", self)
        self.StartTimeStepInput = QLineEdit("0", self)
        self.EndTimeStepLabel = QLabel("Zeitschritt Simulationsende (max 8760):", self)
        self.EndTimeStepInput = QLineEdit("8760", self)

        self.layout.addWidget(self.StartTimeStepLabel)
        self.layout.addWidget(self.StartTimeStepInput)
        self.layout.addWidget(self.EndTimeStepLabel)
        self.layout.addWidget(self.EndTimeStepInput)

        # Dateiauswahl
        self.fileInputlayout = QHBoxLayout()

        self.resultsFileLabel = QLabel("Ausgabedatei Lastgang:", self)
        self.resultsFileInput = QLineEdit(os.path.join(self.base_path, self.parent.config_manager.get_relative_path('load_profile_path')), self)
        self.selectresultsFileButton = QPushButton('csv-Datei auswählen')
        self.selectresultsFileButton.clicked.connect(lambda: self.selectFilename(self.resultsFileInput))

        self.fileInputlayout.addWidget(self.resultsFileLabel)
        self.fileInputlayout.addWidget(self.resultsFileInput)
        self.fileInputlayout.addWidget(self.selectresultsFileButton)

        self.layout.addLayout(self.fileInputlayout)

        # Buttons
        buttonLayout = QHBoxLayout()
        okButton = QPushButton("OK", self)
        cancelButton = QPushButton("Abbrechen", self)
        
        okButton.clicked.connect(self.onAccept)
        cancelButton.clicked.connect(self.reject)
        
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)

        self.layout.addLayout(buttonLayout)

    def onAccept(self):
        """Validate inputs and accept dialog if valid."""
        if self.validateInputs():
            self.accept()

    def validateInputs(self):
        """
        Validate start and end time steps.

        Returns
        -------
        bool
            True if inputs are valid.
        """
        start = int(self.StartTimeStepInput.text())
        end = int(self.EndTimeStepInput.text())
        
        if start < 0 or start > 8760 or end < 0 or end > 8760:
            QMessageBox.warning(self, "Ungültige Eingabe", "Start- und Endzeitschritte müssen zwischen 0 und 8760 liegen.")
            return False
        if start > end:
            QMessageBox.warning(self, "Ungültige Eingabe", "Der Startschritt darf nicht größer als der Endschritt sein.")
            return False
        return True

    def selectFilename(self, lineEdit):
        """
        Open file dialog and update line edit with selected file.

        Parameters
        ----------
        lineEdit : QLineEdit
            Line edit widget to update.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            lineEdit.setText(filename)

    def getValues(self):
        """
        Get dialog values.

        Returns
        -------
        dict
            Dictionary containing results filename, start and end time steps.
        """
        return {
            'results_filename': self.resultsFileInput.text(),
            'start': int(self.StartTimeStepInput.text()),
            'end': int(self.EndTimeStepInput.text())
        }