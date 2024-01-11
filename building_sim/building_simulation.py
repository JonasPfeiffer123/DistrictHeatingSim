import sys
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QScrollArea,
                             QApplication, QPushButton, QLineEdit, QMessageBox)
import heat_requirement_BDEW

class BuildingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Gebäudesimulator")
        self.setGeometry(0, 0, 1920, 1080)

        layout = QVBoxLayout(self)
        mainWidget = QWidget()
        self.mainLayout = QVBoxLayout(mainWidget)

        self.setupInputs()
        self.calculateNetButton = QPushButton('Lastgang berechnen', self)
        self.calculateNetButton.clicked.connect(self.calculate)
        self.mainLayout.addWidget(self.calculateNetButton)

        self.setupPlotLayout()
        layout.addWidget(mainWidget)

        # Stylesheet für visuelle Verbesserungen
        self.setStyleSheet("QWidget { font-size: 12pt; } QPushButton { background-color: lightblue; }")

    def setupInputs(self):
        self.mainLayout.addWidget(QLabel("Jahreswärmebedarf in kWh", self))
        self.JahreswärmebedarfInput = QLineEdit("15000", self)
        self.JahreswärmebedarfInput.setToolTip("Geben Sie den Jahreswärmebedarf in kWh ein.")
        self.mainLayout.addWidget(self.JahreswärmebedarfInput)

        self.buildingTypeInput = QComboBox(self)
        self.mainLayout.addWidget(QLabel("Gebäudetyp:"))
        self.buildingTypeInput.addItems(["Einfamilienhaus", "Mehrfamilienhaus", "Gewerbe/Handel/Dienstleistungen"])
        self.mainLayout.addWidget(self.buildingTypeInput)

    def setupPlotLayout(self):
        self.scrollArea = QScrollArea(self)
        self.scrollWidget = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollWidget)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(500, 500)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.scrollLayout.addWidget(self.canvas)
        self.scrollLayout.addWidget(self.toolbar)
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setWidgetResizable(True)
        self.mainLayout.addWidget(self.scrollArea)
    
    def calculate(self):
        try:
            JEB_Wärme_ges_kWh = int(self.JahreswärmebedarfInput.text())
            #JEB_Strom_kWh = int(self.JahresstrombedarfInput.text())
        except ValueError:
            QMessageBox.warning(self, "Eingabefehler", "Bitte geben Sie gültige Zahlen ein.")
            return
        
        building_type_name = self.buildingTypeInput.currentText()

        time_steps = None

        if building_type_name == "Einfamilienhaus":
            building_type = "HEF"
        if building_type_name == "Mehrfamilienhaus":
            building_type = "HMF"
        if building_type_name == "Gewerbe/Handel/Dienstleistungen":
            building_type = "GHD"

        time_steps, waerme_ges_kW, hourly_temperatures  = heat_requirement_BDEW.calculate(JEB_Wärme_ges_kWh, building_type, subtyp="03")

        waerme_ges_kW = np.array(waerme_ges_kW)

        self.plot(time_steps, waerme_ges_kW, hourly_temperatures)
    
    def plot(self, time_steps, waerme_ges_kW, hourly_temperatures):
        # Vorherige Darstellung löschen
        self.figure.clear()

        # Anpassen der Ränder
        self.figure.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.1)

        # Erste Y-Achse für den Wärmebedarf
        ax1 = self.figure.add_subplot(111)
        ax1.plot(time_steps, waerme_ges_kW, 'b-', label="Gesamtlast Gebäude", linewidth=1)  # Verringerte Strichstärke
        ax1.set_xlabel("Zeit")
        ax1.set_ylabel("Wärmebedarf in kW", color='b')
        ax1.tick_params('y', colors='b')
        ax1.legend(loc='upper left')
        ax1.grid()

        # Schriftgröße für Achsenbeschriftungen und Titel anpassen
        ax1.xaxis.label.set_fontsize(14)
        ax1.yaxis.label.set_fontsize(14)
        for label in ax1.get_xticklabels() + ax1.get_yticklabels():
            label.set_fontsize(12)

        # Setze die Grenzen der X-Achse so, dass sie mit den Zeitdaten beginnen und enden
        ax1.set_xlim([time_steps[0], time_steps[-1]])  # Erster und letzter Zeitpunkt als Grenzen
        # Setze die Grenzen der Y-Achse so, dass 0 an der Achse liegt
        ax1.set_ylim([0, max(waerme_ges_kW) * 1.1])  # Ein wenig Spielraum nach oben

        # Zweite Y-Achse für die Temperatur
        ax2 = ax1.twinx()
        ax2.plot(time_steps, hourly_temperatures, 'g-', label="Lufttemperatur", linewidth=1)  # Verringerte Strichstärke
        ax2.set_ylabel("Temperatur in °C", color='g')
        ax2.tick_params('y', colors='g')
        ax2.legend(loc='upper right')

        # Schriftgröße für die zweite Y-Achse
        ax2.yaxis.label.set_fontsize(14)
        for label in ax2.get_yticklabels():
            label.set_fontsize(12)

        # Setze die Grenzen der Y-Achse für die Temperaturen so, dass 0 an der Achse liegt
        min_temp = min(hourly_temperatures)
        max_temp = max(hourly_temperatures)
        temp_range = max_temp - min_temp
        ax2.set_ylim([min_temp - 0.1 * temp_range, max_temp + 0.1 * temp_range])  # Ein wenig Spielraum nach oben und unten

        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = BuildingTab()
    ex.show()
    sys.exit(app.exec_())