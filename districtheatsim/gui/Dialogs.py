import sys
import os

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, QPushButton, QHBoxLayout, QFileDialog

# defines the map path
def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

class TemperatureDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Temperaturdaten-Verwaltung")
        self.resize(400, 200)  # Größeres und anpassbares Fenster

        self.layout = QVBoxLayout(self)

        self.temperatureDataFileLabel = QLabel("TRY-Datei:", self)
        self.temperatureDataFileInput = QLineEdit(self)
        self.temperatureDataFileInput.setText(get_resource_path("heat_requirement\TRY_511676144222\TRY2015_511676144222_Jahr.dat"))
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
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            lineEdit.setText(filename)

    def getValues(self):
        return {
            'TRY-filename': self.temperatureDataFileInput.text()
        }
    
class HeatPumpDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wärmepumpendaten")
        self.initUI()

    def initUI(self):
        self.setWindowTitle("COP-Daten-Verwaltung")
        self.resize(400, 200)  # Größeres und anpassbares Fenster
        
        # Hauptlayout
        mainLayout = QVBoxLayout(self)

        # Datenfelder und Label
        dataLayout = QVBoxLayout()
        self.heatPumpDataFileLabel = QLabel("csv-Datei mit Wärmepumpenkennfeld:")
        self.heatPumpDataFileInput = QLineEdit()
        self.heatPumpDataFileInput.setText(get_resource_path("heat_generators\Kennlinien WP.csv"))
        self.selectCOPFileButton = QPushButton('csv-Datei auswählen')
        self.selectCOPFileButton.clicked.connect(lambda: self.selectFilename(self.heatPumpDataFileInput))
        
        # Styling
        self.selectCOPFileButton.setStyleSheet("background-color: #0057b7; color: white; padding: 5px;")
        self.heatPumpDataFileInput.setStyleSheet("padding: 4px;")
        
        dataLayout.addWidget(self.heatPumpDataFileLabel)
        dataLayout.addWidget(self.heatPumpDataFileInput)
        dataLayout.addWidget(self.selectCOPFileButton)

        mainLayout.addLayout(dataLayout)

        # Button Layout für OK und Abbrechen
        buttonLayout = QHBoxLayout()
        okButton = QPushButton("OK")
        cancelButton = QPushButton("Abbrechen")
        okButton.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px;")
        cancelButton.setStyleSheet("background-color: #f44336; color: white; padding: 5px;")

        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)

        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)

        mainLayout.addLayout(buttonLayout)
        self.setLayout(mainLayout)

    def selectFilename(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "CSV-Dateien (*.csv)")
        if filename:
            lineEdit.setText(filename)

    def getValues(self):
        # Zurückgeben der Werte zur weiteren Verarbeitung
        return {
            'COP-filename': self.heatPumpDataFileInput.text()
        }