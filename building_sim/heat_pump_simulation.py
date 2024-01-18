import sys
from PyQt5.QtWidgets import (QApplication, QLabel, QLineEdit, QPushButton, QVBoxLayout, 
                             QWidget, QGroupBox, QFormLayout)
from PyQt5.QtGui import QIntValidator, QFont

class HeatPumpTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Wärmepumpen-Simulator")
        self.setGeometry(100, 100, 800, 600)

        mainLayout = QVBoxLayout(self)
        inputGroupBox = QGroupBox("Eingabewerte")
        formLayout = QFormLayout()

        self.QuelltemperaturInput = QLineEdit("5")
        self.QuelltemperaturInput.setValidator(QIntValidator(-20, 40))
        self.QuelltemperaturInput.setToolTip("Geben Sie eine Quelltemperatur zwischen -20 und 40 ein.")
        formLayout.addRow("Temperatur der Quelle in °C:", self.QuelltemperaturInput)

        self.HeiztemperaturInput = QLineEdit("65")
        self.HeiztemperaturInput.setValidator(QIntValidator(0, 100))
        self.HeiztemperaturInput.setToolTip("Geben Sie eine Vorlauftemperatur zwischen 0 und 100 ein.")
        formLayout.addRow("Vorlauftemperatur der Heizung in °C:", self.HeiztemperaturInput)

        self.calculateNetButton = QPushButton('COP berechnen')
        self.calculateNetButton.clicked.connect(self.calculate)
        formLayout.addRow(self.calculateNetButton)

        self.resultOutput = QLineEdit()
        self.resultOutput.setReadOnly(True)
        self.resultOutput.setFont(QFont("Arial", 12, QFont.Bold))
        self.resultOutput.setStyleSheet("color: green;")
        formLayout.addRow("Effizienz der Wärmepumpe (COP):", self.resultOutput)

        inputGroupBox.setLayout(formLayout)
        mainLayout.addWidget(inputGroupBox)

    def calculate(self):
        QT = float(self.QuelltemperaturInput.text())
        HT = float(self.HeiztemperaturInput.text())
        self.calculateNetButton.setEnabled(False)
        
        try:
            COP_id = (HT + 273.15) / (HT - QT)
            COP = COP_id * 0.6
            self.resultOutput.setText(f"{COP:.2f}")
        except ZeroDivisionError:
            self.resultOutput.setText("Fehler: Division durch Null")
        finally:
            self.calculateNetButton.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HeatPumpTab()
    ex.show()
    sys.exit(app.exec_())
