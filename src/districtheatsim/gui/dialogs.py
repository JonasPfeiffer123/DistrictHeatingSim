"""
Filename: Dialogs.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Contains the Dialogs of the main GUI
"""

import sys
import os

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, QPushButton, QHBoxLayout, QFileDialog

def get_resource_path(relative_path):
    """
    Get the absolute path to the resource, works for dev and for PyInstaller.

    Args:
        relative_path (str): The relative path to the resource.

    Returns:
        str: The absolute path to the resource.
    """
    if getattr(sys, 'frozen', False):
        # When the application is frozen, the base path is the temp folder where PyInstaller extracts everything
        base_path = sys._MEIPASS
    else:
        # When the application is not frozen, the base path is the folder where the main file is located
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

class TemperatureDataDialog(QDialog):
    """
    Dialog for managing temperature data.

    Attributes:
        temperatureDataFileLabel (QLabel): Label for the TRY file input.
        temperatureDataFileInput (QLineEdit): Input field for the TRY file path.
        selectTRYFileButton (QPushButton): Button to open file dialog for selecting TRY file.
    """

    def __init__(self, parent=None):
        """
        Initializes the TemperatureDataDialog.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """Initializes the user interface."""
        self.setWindowTitle("Temperaturdaten-Verwaltung")
        self.resize(400, 200)  # Larger and resizable window

        self.layout = QVBoxLayout(self)

        self.temperatureDataFileLabel = QLabel("TRY-Datei:", self)
        self.temperatureDataFileInput = QLineEdit(self)
        self.temperatureDataFileInput.setText(get_resource_path("data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat"))
        self.selectTRYFileButton = QPushButton('TRY-Datei auswählen')
        self.selectTRYFileButton.clicked.connect(lambda: self.selectFilename(self.temperatureDataFileInput))

        self.layout.addWidget(self.temperatureDataFileLabel)
        self.layout.addWidget(self.temperatureDataFileInput)
        self.layout.addWidget(self.selectTRYFileButton)

        self.setLayout(self.layout)

        buttonLayout = QHBoxLayout()
        okButton = QPushButton("OK", self)
        cancelButton = QPushButton("Abbrechen", self)
        
        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)

        self.layout.addLayout(buttonLayout)

    def selectFilename(self, lineEdit):
        """
        Opens a file dialog to select a file and sets the selected file path to the given QLineEdit.

        Args:
            lineEdit (QLineEdit): The QLineEdit to set the file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            lineEdit.setText(filename)

    def getValues(self):
        """
        Returns the values from the dialog for further processing.

        Returns:
            dict: A dictionary with the TRY filename.
        """
        return {
            'TRY-filename': self.temperatureDataFileInput.text()
        }

class HeatPumpDataDialog(QDialog):
    """
    Dialog for managing heat pump data.

    Attributes:
        heatPumpDataFileLabel (QLabel): Label for the heat pump data file input.
        heatPumpDataFileInput (QLineEdit): Input field for the heat pump data file path.
        selectCOPFileButton (QPushButton): Button to open file dialog for selecting COP data file.
    """

    def __init__(self, parent=None):
        """
        Initializes the HeatPumpDataDialog.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Wärmepumpendaten")
        self.initUI()

    def initUI(self):
        """Initializes the user interface."""
        self.setWindowTitle("COP-Daten-Verwaltung")
        self.resize(400, 200)  # Larger and resizable window
        
        # Main layout
        mainLayout = QVBoxLayout(self)

        # Data fields and label
        dataLayout = QVBoxLayout()
        self.heatPumpDataFileLabel = QLabel("csv-Datei mit Wärmepumpenkennfeld:")
        self.heatPumpDataFileInput = QLineEdit()
        self.heatPumpDataFileInput.setText(get_resource_path("data/COP/Kennlinien WP.csv"))
        self.selectCOPFileButton = QPushButton('csv-Datei auswählen')
        self.selectCOPFileButton.clicked.connect(lambda: self.selectFilename(self.heatPumpDataFileInput))
        
        dataLayout.addWidget(self.heatPumpDataFileLabel)
        dataLayout.addWidget(self.heatPumpDataFileInput)
        dataLayout.addWidget(self.selectCOPFileButton)

        mainLayout.addLayout(dataLayout)

        # Button layout for OK and Cancel
        buttonLayout = QHBoxLayout()
        okButton = QPushButton("OK")
        cancelButton = QPushButton("Abbrechen")

        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)

        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)

        mainLayout.addLayout(buttonLayout)
        self.setLayout(mainLayout)

    def selectFilename(self, lineEdit):
        """
        Opens a file dialog to select a file and sets the selected file path to the given QLineEdit.

        Args:
            lineEdit (QLineEdit): The QLineEdit to set the file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "CSV-Dateien (*.csv)")
        if filename:
            lineEdit.setText(filename)

    def getValues(self):
        """
        Returns the values from the dialog for further processing.

        Returns:
            dict: A dictionary with the COP filename.
        """
        return {
            'COP-filename': self.heatPumpDataFileInput.text()
        }