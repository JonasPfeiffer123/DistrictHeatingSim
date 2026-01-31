"""Time Series Dialog Module
=========================

Dialog for configuring time series calculation parameters.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os
from PyQt6.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog,  \
    QPushButton, QHBoxLayout, QFileDialog, QMessageBox, QRadioButton, \
    QButtonGroup, QGroupBox

class TimeSeriesCalculationDialog(QDialog):
    """
    Dialog for time series calculation configuration.
    """

    def __init__(self, base_path, parent=None):
        """
        Initialize time series calculation dialog.

        :param base_path: Base path for file dialogs.
        :type base_path: str
        :param parent: Parent widget.
        :type parent: QWidget
        """
        super().__init__(parent)
        self.base_path = base_path
        self.parent = parent
        self.initUI()

    def initUI(self):
        """
        Initialize user interface components.
        """
        self.setWindowTitle("Zeitreihenrechnung")
        self.resize(500, 300)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Berechnungsmethode auswählen
        calculationMethodGroup = QGroupBox("Berechnungsmethode", self)
        calculationMethodLayout = QVBoxLayout()
        
        self.detailedCalcRadio = QRadioButton("Ausführliche Berechnung mit pandapipes (detailliert, langsamer)", self)
        self.simplifiedCalcRadio = QRadioButton("Vereinfachte Berechnung (schnell, basierend auf Auslegung)", self)
        self.detailedCalcRadio.setChecked(True)
        
        self.calculationMethodGroup = QButtonGroup(self)
        self.calculationMethodGroup.addButton(self.detailedCalcRadio, 0)
        self.calculationMethodGroup.addButton(self.simplifiedCalcRadio, 1)
        
        calculationMethodLayout.addWidget(self.detailedCalcRadio)
        calculationMethodLayout.addWidget(self.simplifiedCalcRadio)
        calculationMethodGroup.setLayout(calculationMethodLayout)
        
        self.layout.addWidget(calculationMethodGroup)

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
        """
        Validate inputs and accept dialog if valid.
        """
        if self.validateInputs():
            self.accept()

    def validateInputs(self):
        """
        Validate start and end time steps.

        :return: True if inputs are valid.
        :rtype: bool
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

        :param lineEdit: Line edit widget to update.
        :type lineEdit: QLineEdit
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            lineEdit.setText(filename)

    def getValues(self):
        """
        Get dialog values.

        :return: Dictionary containing results filename, start and end time steps, and calculation method.
        :rtype: dict
        """
        return {
            'results_filename': self.resultsFileInput.text(),
            'start': int(self.StartTimeStepInput.text()),
            'end': int(self.EndTimeStepInput.text()),
            'simplified': self.simplifiedCalcRadio.isChecked()
        }