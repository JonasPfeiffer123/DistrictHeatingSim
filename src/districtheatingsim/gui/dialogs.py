"""
GUI Dialogs Module
==================

This module contains dialog windows for user input and configuration.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-10
"""

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, QPushButton, QHBoxLayout, QFileDialog, QCheckBox, QDialogButtonBox, QHBoxLayout
from PyQt5.QtCore import Qt

from districtheatingsim.utilities.utilities import get_resource_path

class TemperatureDataDialog(QDialog):
    """
    Dialog for selecting TRY (Test Reference Year) weather data files.
    
    Simple file selection dialog for weather data input with default path.
    """

    def __init__(self, parent=None):
        """
        Initialize temperature data dialog.
        
        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """Initialize the user interface components."""
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
        self.descriptionLabel.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.descriptionLabel)

        # File input controls
        self.input_layout = QHBoxLayout()

        self.temperatureDataFileLabel = QLabel("TRY-Datei:", self)
        self.temperatureDataFileInput = QLineEdit(self)
        self.temperatureDataFileInput.setText(get_resource_path("data\\TRY\\TRY_511676144222\\TRY2015_511676144222_Jahr.dat"))
        self.selectTRYFileButton = QPushButton('TRY-Datei auswählen')
        self.selectTRYFileButton.clicked.connect(lambda: self.selectFilename(self.temperatureDataFileInput))

        self.input_layout.addWidget(self.temperatureDataFileLabel)
        self.input_layout.addWidget(self.temperatureDataFileInput)
        self.input_layout.addWidget(self.selectTRYFileButton)

        self.main_layout.addLayout(self.input_layout)
        
        # OK/Cancel buttons
        self.buttonLayout = QHBoxLayout()
        okButton = QPushButton("OK", self)
        cancelButton = QPushButton("Abbrechen", self)
        
        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        
        self.buttonLayout.addWidget(okButton)
        self.buttonLayout.addWidget(cancelButton)

        self.main_layout.addLayout(self.buttonLayout)

    def selectFilename(self, lineEdit):
        """
        Open file dialog and set selected path to line edit.
        
        Parameters
        ----------
        lineEdit : QLineEdit
            Target line edit widget.
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
            Dictionary with TRY filename.
        """
        return {
            'TRY-filename': self.temperatureDataFileInput.text()
        }

class HeatPumpDataDialog(QDialog):
    """
    Dialog for selecting heat pump COP data files.
    
    Simple file selection dialog for heat pump performance data.
    """

    def __init__(self, parent=None):
        """
        Initialize heat pump data dialog.
        
        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Wärmepumpendaten")
        self.initUI()

    def initUI(self):
        """Initialize the user interface components."""
        self.setWindowTitle("COP-Daten-Verwaltung")
        self.resize(400, 200)
        
        mainLayout = QVBoxLayout(self)

        # File input controls
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

    def selectFilename(self, lineEdit):
        """
        Open file dialog and set selected path to line edit.
        
        Parameters
        ----------
        lineEdit : QLineEdit
            Target line edit widget.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "CSV-Dateien (*.csv)")
        if filename:
            lineEdit.setText(filename)

    def getValues(self):
        """
        Get dialog values.
        
        Returns
        -------
        dict
            Dictionary with COP filename.
        """
        return {
            'COP-filename': self.heatPumpDataFileInput.text()
        }

class PDFSelectionDialog(QDialog):
    """
    Dialog for selecting PDF report sections.
    
    Checkbox dialog for choosing which sections to include in PDF reports.
    """
    
    def __init__(self, parent=None):
        """
        Initialize PDF selection dialog.
        
        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("PDF Abschnittsauswahl")
        self.resize(300, 200)

        layout = QVBoxLayout()

        # Section checkboxes
        self.net_structure_cb = QCheckBox("Netzstruktur")
        self.net_structure_cb.setChecked(True)
        self.economic_conditions_cb = QCheckBox("Wirtschaftliche Randbedingungen")
        self.economic_conditions_cb.setChecked(True)
        self.technologies_cb = QCheckBox("Erzeugertechnologien")
        self.technologies_cb.setChecked(True)
        self.technolgies_scene_cb = QCheckBox("Schaltbild Erzeugertechnologien")
        self.technolgies_scene_cb.setChecked(True)
        self.costs_net_infrastructure_cb = QCheckBox("Kosten Netzinfrastruktur")
        self.costs_net_infrastructure_cb.setChecked(True)
        self.costs_heat_generators_cb = QCheckBox("Kosten Wärmeerzeuger")
        self.costs_heat_generators_cb.setChecked(True)
        self.costs_total_cb = QCheckBox("Gesamtkosten")
        self.costs_total_cb.setChecked(True)
        self.results_cb = QCheckBox("Berechnungsergebnisse")
        self.results_cb.setChecked(True)
        self.combined_results_cb = QCheckBox("Wirtschaftlichkeit")
        self.combined_results_cb.setChecked(True)

        # Add checkboxes to layout
        layout.addWidget(self.net_structure_cb)
        layout.addWidget(self.economic_conditions_cb)
        layout.addWidget(self.technologies_cb)
        layout.addWidget(self.technolgies_scene_cb)
        layout.addWidget(self.costs_net_infrastructure_cb)
        layout.addWidget(self.costs_heat_generators_cb)
        layout.addWidget(self.costs_total_cb)
        layout.addWidget(self.results_cb)
        layout.addWidget(self.combined_results_cb)

        # OK/Cancel buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

        self.setLayout(layout)

    def get_selected_sections(self):
        """
        Get selected PDF sections.
        
        Returns
        -------
        dict
            Dictionary with checkbox states for each section.
        """
        return {
            'net_structure': self.net_structure_cb.isChecked(),
            'economic_conditions': self.economic_conditions_cb.isChecked(),
            'technologies': self.technologies_cb.isChecked(),
            'technologies_scene': self.technolgies_scene_cb.isChecked(),
            'costs_net_infrastructure': self.costs_net_infrastructure_cb.isChecked(),
            'costs_heat_generators': self.costs_heat_generators_cb.isChecked(),
            'costs_total': self.costs_total_cb.isChecked(),
            'results': self.results_cb.isChecked(),
            'combined_results': self.combined_results_cb.isChecked()
        }