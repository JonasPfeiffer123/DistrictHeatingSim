"""GUI Dialogs Module
==================

Dialog windows for user input and configuration.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from PyQt6.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, QPushButton, QHBoxLayout, QFileDialog, QCheckBox, QDialogButtonBox, QHBoxLayout
from PyQt6.QtCore import Qt

from districtheatingsim.utilities.utilities import get_resource_path

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
    Dialog for selecting heat pump COP data files.

    .. note::
       Simple file selection dialog for heat pump performance data.
    """

    def __init__(self, parent=None):
        """
        Initialize heat pump data dialog.

        :param parent: Parent widget, defaults to None
        :type parent: QWidget, optional
        """
        super().__init__(parent)
        self.setWindowTitle("Wärmepumpendaten")
        self.initUI()

    def initUI(self):
        """
        Initialize the user interface components with COP file selection.

        .. note::
           Creates file input field with default COP data path and OK/Cancel buttons.
        """
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

        :param lineEdit: Target line edit widget
        :type lineEdit: QLineEdit
        """
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