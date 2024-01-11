import sys
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QScrollArea, QSizePolicy, QFormLayout,
                             QApplication, QPushButton, QLineEdit, QMessageBox)
import heat_requirement_BDEW

class HeatGenTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Heizungsauslegung")
        self.setGeometry(0, 0, 1920, 1080)

        layout = QVBoxLayout(self)
        mainWidget = QWidget()
        self.mainLayout = QVBoxLayout(mainWidget)

        self.setupLabels(self.mainLayout)

        self.setupPlotLayout()
        layout.addWidget(mainWidget)

        # Stylesheet für visuelle Verbesserungen
        self.setStyleSheet("QWidget { font-size: 12pt; } QPushButton { background-color: lightblue; }")

    def setupLabels(self, layout):
        formLayout = QFormLayout()

        heating_temp_label = QLabel("Vorlauftemperatur der Heizung (unterschiedlich je nach Heizungssystem) in °C:", self)
        heating_temp_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        formLayout.addWidget(heating_temp_label)

        self.HeiztemperaturInput = QLineEdit("65", self)
        self.HeiztemperaturInput.setToolTip("Geben Sie eine Vorlauftemperatur ein.")
        formLayout.addWidget(self.HeiztemperaturInput)

        # Dropdown-Menü für Wärmequelle
        wärmequelle_label = QLabel("Wärmequelle:")
        wärmequelle_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        formLayout.addWidget(wärmequelle_label)

        self.wärmequelleInput = QComboBox(self)
        self.wärmequelleInput.addItems(["Luft", "Erdreich"])
        self.wärmequelleInput.currentIndexChanged.connect(self.onWaermequelleChange) # Verbindung zum Event
        formLayout.addWidget(self.wärmequelleInput)

        # Zusätzliches Eingabefeld für Erdreichtemperatur
        self.ErdreichTemperaturInput = QLineEdit("10", self)
        self.ErdreichTemperaturInput.setToolTip("Geben Sie die Erdreichtemperatur ein.")
        self.ErdreichTemperaturInput.setHidden(True) # Standardmäßig versteckt
        formLayout.addWidget(self.ErdreichTemperaturInput)

        self.calculateNetButton = QPushButton('COP-Jahresverlauf berechnen', self)
        self.calculateNetButton.clicked.connect(self.calculate_cop)
        formLayout.addWidget(self.calculateNetButton)

        Heiztemperatur_label = QLabel("Jahreswärmebedarf in kWh", self)
        Heiztemperatur_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        formLayout.addWidget(Heiztemperatur_label)

        self.JahreswärmebedarfInput = QLineEdit("15000", self)
        self.JahreswärmebedarfInput.setToolTip("Geben Sie den Jahreswärmebedarf in kWh ein.")
        formLayout.addWidget(self.JahreswärmebedarfInput)

        gebäudetyp_label = QLabel("Gebäudetyp:")
        gebäudetyp_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        formLayout.addWidget(gebäudetyp_label)

        self.buildingTypeInput = QComboBox(self)
        self.buildingTypeInput.addItems(["Einfamilienhaus", "Mehrfamilienhaus", "Gewerbe/Handel/Dienstleistungen"])
        formLayout.addWidget(self.buildingTypeInput)

        self.calculateNetButton = QPushButton('Strombedarf berechnen', self)
        self.calculateNetButton.clicked.connect(self.calculate)
        formLayout.addWidget(self.calculateNetButton)

        self.strombedarf_label = QLabel("Jährlicher Stromverbrauch der Wärmepumpe: ")
        self.strombedarf_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        formLayout.addWidget(self.strombedarf_label)

        self.JAZ_label = QLabel("Jahresarbeitszahl Wärmepumpe (Jahreswärmebedarf Gebäude / Stromverbrauch Wärmepumpe): ")
        self.JAZ_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        formLayout.addWidget(self.JAZ_label)

        layout.addLayout(formLayout)

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
    
    def onWaermequelleChange(self, index):
        # Anzeigen des Erdreichtemperatur-Eingabefelds, wenn "Erdreich" ausgewählt ist
        if self.wärmequelleInput.currentText() == "Erdreich":
            self.ErdreichTemperaturInput.setHidden(False)
        else:
            self.ErdreichTemperaturInput.setHidden(True)

    def calculate_cop(self):
        HT = float(self.HeiztemperaturInput.text())
        JEB_Wärme_ges_kWh = 1
        building_type = "HMF"
        time_steps, _, hourly_temperatures  = heat_requirement_BDEW.calculate(JEB_Wärme_ges_kWh, building_type, subtyp="03")
        
        if self.wärmequelleInput.currentText() == "Erdreich":
            # Anpassen der Berechnungen für Erdreich
            hourly_temperatures = np.full(8760, float(self.ErdreichTemperaturInput.text()))

        COP_id = (HT + 273.15) / (HT - hourly_temperatures)
        COP = COP_id * 0.6

        self.plot1(time_steps, hourly_temperatures, COP)
    
    def plot1(self, time_steps, hourly_temperatures, COP):
        # Vorherige Darstellung löschen
        self.figure.clear()

        # Anpassen der Ränder
        self.figure.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.1)

        # Erste Y-Achse für den Wärmebedarf
        ax1 = self.figure.add_subplot(111)
        ax1.plot(time_steps, COP, 'purple', label="COP", linewidth=1)  # Verringerte Strichstärke
        ax1.set_xlabel("Zeit")
        ax1.set_ylabel("COP", color='purple')
        ax1.tick_params('y', colors='purple')
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
        ax1.set_ylim([0, max(COP) * 1.1])  # Ein wenig Spielraum nach oben

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

        HT = float(self.HeiztemperaturInput.text())

        if self.wärmequelleInput.currentText() == "Erdreich":
            # Anpassen der Berechnungen für Erdreich
            hourly_temperatures = np.full(8760, float(self.ErdreichTemperaturInput.text()))

        COP_id = (HT + 273.15) / (HT - hourly_temperatures)
        COP = COP_id * 0.6

        strom_ges_kW = waerme_ges_kW / COP

        strombedarf_gesamt_kWh = np.sum(strom_ges_kW)
        JAZ = JEB_Wärme_ges_kWh/strombedarf_gesamt_kWh

        self.strombedarf_label.setText(f"Jährlicher Stromverbrauch der Wärmepumpe: {strombedarf_gesamt_kWh:.2f} kWh")
        self.JAZ_label.setText(f"Jahresarbeitszahl Wärmepumpe (Jahreswärmebedarf Gebäude / Stromverbrauch Wärmepumpe): {JAZ:.2f}")

        self.plot2(time_steps, waerme_ges_kW, strom_ges_kW)
    
    def plot2(self, time_steps, waerme_ges_kW, strom_ges_kW):
        # Vorherige Darstellung löschen
        self.figure.clear()

        # Anpassen der Ränder
        self.figure.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.1)

        # Erste Y-Achse für den Wärmebedarf
        ax1 = self.figure.add_subplot(111)
        ax1.plot(time_steps, waerme_ges_kW, 'b-', label="Gesamtlast Gebäude", linewidth=1)  # Verringerte Strichstärke
        ax1.plot(time_steps, strom_ges_kW, 'r-', label="Strombedarf Wärmepumpe", linewidth=1)  # Verringerte Strichstärke
        ax1.set_xlabel("Zeit")
        ax1.set_ylabel("Wärmebedarf, Stromverbrauch in kW")
        ax1.legend(loc='upper center')
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

        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HeatGenTab()
    ex.show()
    sys.exit(app.exec_())