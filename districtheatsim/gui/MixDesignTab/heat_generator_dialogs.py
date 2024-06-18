import sys
import os

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, QComboBox, QCheckBox, \
    QDialogButtonBox, QHBoxLayout, QFormLayout, QPushButton, QFileDialog, QMessageBox, QWidget
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D, art3d

# defines the map path
def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, relative_path)

class TechInputDialog(QDialog):
    def __init__(self, tech_type, tech_data=None):
        super().__init__()

        self.tech_type = tech_type
        self.tech_data = tech_data if tech_data is not None else {}
        self.dialog = None

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        if self.tech_type == "Solarthermie":
            self.dialog = SolarThermalDialog(self.tech_data)
        elif self.tech_type == "Biomassekessel":
            self.dialog = BiomassBoilerDialog(self.tech_data)
        elif self.tech_type == "Gaskessel":
            self.dialog = GasBoilerDialog(self.tech_data)
        elif self.tech_type == "BHKW":
            self.dialog = CHPDialog(self.tech_data)
        elif self.tech_type == "Holzgas-BHKW":
            self.dialog = HolzgasCHPDialog(self.tech_data)
        elif self.tech_type == "Geothermie":
            self.dialog = GeothermalDialog(self.tech_data)
        elif self.tech_type == "Abwärme":
            self.dialog = WasteHeatPumpDialog(self.tech_data)
        elif self.tech_type == "Flusswasser":
            self.dialog = RiverHeatPumpDialog(self.tech_data)
        else:
            raise ValueError(f"Unbekannter Technologietyp: {self.tech_type}")

        if self.dialog:
            layout.addWidget(self.dialog)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setWindowTitle(f"Eingabe für {self.tech_type}")
        #self.resize(400, 300)

    def accept(self):
        if self.dialog:
            self.tech_data = self.dialog.getInputs()
        super().accept()

    def getInputs(self):
        return self.tech_data

class SolarThermalDialog(QWidget):
    def __init__(self, tech_data=None):
        super(SolarThermalDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        form_layout = QFormLayout()

        self.areaSInput = QLineEdit(self)
        self.areaSInput.setText(str(self.tech_data.get('bruttofläche_STA', "200")))
        form_layout.addRow(QLabel("Kollektorbruttofläche in m²"), self.areaSInput)

        self.vsInput = QLineEdit(self)
        self.vsInput.setText(str(self.tech_data.get('vs', "20")))
        form_layout.addRow(QLabel("Solarspeichervolumen in m³"), self.vsInput)

        self.typeInput = QComboBox(self)
        self.techOptions = ["Vakuumröhrenkollektor", "Flachkollektor"]
        self.typeInput.addItems(self.techOptions)
        if 'Typ' in self.tech_data:
            current_type_index = self.techOptions.index(self.tech_data['Typ'])
            self.typeInput.setCurrentIndex(current_type_index)
        form_layout.addRow(QLabel("Kollektortyp"), self.typeInput)

        self.TsmaxInput = QLineEdit(self)
        self.TsmaxInput.setText(str(self.tech_data.get('Tsmax', "90")))
        form_layout.addRow(QLabel("Maximale Speichertemperatur in °C"), self.TsmaxInput)

        self.LongitudeInput = QLineEdit(self)
        self.LongitudeInput.setText(str(self.tech_data.get('Longitude', "-14.4222")))
        form_layout.addRow(QLabel("Longitude des Erzeugerstandortes"), self.LongitudeInput)

        self.STD_LongitudeInput = QLineEdit(self)
        self.STD_LongitudeInput.setText(str(self.tech_data.get('STD_Longitude', "15")))
        form_layout.addRow(QLabel("STD_Longitude des Erzeugerstandortes"), self.STD_LongitudeInput)

        self.LatitudeInput = QLineEdit(self)
        self.LatitudeInput.setText(str(self.tech_data.get('Latitude', "51.1676")))
        form_layout.addRow(QLabel("Latitude des Erzeugerstandortes"), self.LatitudeInput)

        self.East_West_collector_azimuth_angleInput = QLineEdit(self)
        self.East_West_collector_azimuth_angleInput.setText(str(self.tech_data.get('East_West_collector_azimuth_angle', "0")))
        form_layout.addRow(QLabel("Azimuth-Ausrichtung des Kollektors in °"), self.East_West_collector_azimuth_angleInput)

        self.Collector_tilt_angleInput = QLineEdit(self)
        self.Collector_tilt_angleInput.setText(str(self.tech_data.get('Collector_tilt_angle', "36")))
        form_layout.addRow(QLabel("Neigungswinkel des Kollektors in ° (0-90)"), self.Collector_tilt_angleInput)

        self.Tm_rlInput = QLineEdit(self)
        self.Tm_rlInput.setText(str(self.tech_data.get('Tm_rl', "60")))
        form_layout.addRow(QLabel("Startwert Rücklauftemperatur in Speicher in °C"), self.Tm_rlInput)

        self.QsaInput = QLineEdit(self)
        self.QsaInput.setText(str(self.tech_data.get('Qsa', "0")))
        form_layout.addRow(QLabel("Startwert Speicherfüllstand"), self.QsaInput)

        self.Vorwärmung_KInput = QLineEdit(self)
        self.Vorwärmung_KInput.setText(str(self.tech_data.get('Vorwärmung_K', "8")))
        form_layout.addRow(QLabel("Mögliche Abweichung von Solltemperatur bei Vorwärmung"), self.Vorwärmung_KInput)

        self.DT_WT_Solar_KInput = QLineEdit(self)
        self.DT_WT_Solar_KInput.setText(str(self.tech_data.get('DT_WT_Solar_K', "5")))
        form_layout.addRow(QLabel("Grädigkeit Wärmeübertrager Kollektor/Speicher"), self.DT_WT_Solar_KInput)

        self.DT_WT_Netz_KInput = QLineEdit(self)
        self.DT_WT_Netz_KInput.setText(str(self.tech_data.get('DT_WT_Netz_K', "5")))
        form_layout.addRow(QLabel("Grädigkeit Wärmeübertrager Speicher/Netz"), self.DT_WT_Netz_KInput)

        self.vscostInput = QLineEdit(self)
        self.vscostInput.setText(str(self.tech_data.get('kosten_speicher_spez', "750")))
        form_layout.addRow(QLabel("spez. Kosten Solarspeicher in €/m³"), self.vscostInput)

        self.areaScostfkInput = QLineEdit(self)
        self.areaScostfkInput.setText(str(self.tech_data.get('kosten_fk_spez', "430")))
        form_layout.addRow(QLabel("spez. Kosten Flachkollektor in €/m²"), self.areaScostfkInput)

        self.areaScostvrkInput = QLineEdit(self)
        self.areaScostvrkInput.setText(str(self.tech_data.get('kosten_vrk_spez', "590")))
        form_layout.addRow(QLabel("spez. Kosten Vakuumröhrenkollektor in €/m²"), self.areaScostvrkInput)

        # Optimizaton inputs
        self.minVolumeInput = QLineEdit(self)
        self.minVolumeInput.setText(str(self.tech_data.get('opt_volume_min', "1")))
        form_layout.addRow(QLabel("Untere Grenze Speichervolumen Optimierung"), self.minVolumeInput)

        self.maxVolumeInput = QLineEdit(self)
        self.maxVolumeInput.setText(str(self.tech_data.get('opt_volume_max', "200")))
        form_layout.addRow(QLabel("Obere Grenze Speichervolumen Optimierung³"), self.maxVolumeInput)

        self.minAreaInput = QLineEdit(self)
        self.minAreaInput.setText(str(self.tech_data.get('opt_area_min', "1")))
        form_layout.addRow(QLabel("Untere Grenze Kollektorfläche Optimierung²"), self.minAreaInput)

        self.maxAreaInput = QLineEdit(self)
        self.maxAreaInput.setText(str(self.tech_data.get('opt_area_max', "2000")))
        form_layout.addRow(QLabel("Obere Grenze Kollektorfläche Optimierung²"), self.maxAreaInput)

        top_layout.addLayout(form_layout)

        # Visualization
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111, projection='3d')
        self.canvas = FigureCanvas(self.figure)
        top_layout.addWidget(self.canvas)

        main_layout.addLayout(top_layout)

        # Connect input changes to the visualization update
        self.East_West_collector_azimuth_angleInput.textChanged.connect(self.updateVisualization)
        self.Collector_tilt_angleInput.textChanged.connect(self.updateVisualization)

        self.setLayout(main_layout)
        self.updateVisualization()

    def updateVisualization(self):
        try:
            azimuth = float(self.East_West_collector_azimuth_angleInput.text())
            tilt = float(self.Collector_tilt_angleInput.text())
        except ValueError:
            azimuth = 0
            tilt = 0

        self.ax.clear()

        # Draw the ground plane
        xx, yy = np.meshgrid(range(-180, 181, 45), range(-180, 181, 45))
        zz = np.zeros_like(xx)
        self.ax.plot_surface(xx, yy, zz, color='green', alpha=0.5)

        # Define the corners of the collector plane
        length = 50  # Length of the collector for better visibility
        width = 30   # Width of the collector for better visibility

        # Calculate coordinates of the collector plane
        x1 = length * np.cos(np.radians(azimuth)) * np.cos(np.radians(tilt))
        y1 = length * np.sin(np.radians(azimuth)) * np.cos(np.radians(tilt))
        z1 = length * np.sin(np.radians(tilt))

        collector_corners = np.array([
            [0, 0, 0],
            [x1, y1, z1],
            [x1 - width * np.sin(np.radians(azimuth)), y1 + width * np.cos(np.radians(azimuth)), z1],
            [-width * np.sin(np.radians(azimuth)), width * np.cos(np.radians(azimuth)), 0]
        ])

        # Create the collector plane
        collector_plane = art3d.Poly3DCollection([collector_corners], facecolors='blue', linewidths=1, edgecolors='r', alpha=0.75)
        self.ax.add_collection3d(collector_plane)

        # Draw a vector representing the normal to the collector plane
        normal_x = np.cos(np.radians(tilt)) * np.cos(np.radians(azimuth))
        normal_y = np.cos(np.radians(tilt)) * np.sin(np.radians(azimuth))
        normal_z = np.sin(np.radians(tilt))
        self.ax.quiver(0, 0, 0, normal_x, normal_y, normal_z, length=10, color='red')

        # Set plot limits
        self.ax.set_xlim([-180, 180])
        self.ax.set_ylim([-180, 180])
        self.ax.set_zlim([0, 100])

        # Label axes with angles
        self.ax.set_xticks(np.arange(-180, 181, 45))
        self.ax.set_yticks(np.arange(-180, 181, 45))
        self.ax.set_zticks(np.arange(0, 101, 10))

        self.ax.set_xlabel('X (Azimut in °)')
        self.ax.set_ylabel('Y (Azimut in °)')
        self.ax.set_zlabel('Z (Höhe in m)')

        # Add compass directions
        self.ax.text(180, 0, 0, 'Nord', color='black', fontsize=12)
        self.ax.text(-180, 0, 0, 'Süd', color='black', fontsize=12)
        self.ax.text(0, 180, 0, 'Ost', color='black', fontsize=12)
        self.ax.text(0, -180, 0, 'West', color='black', fontsize=12)

        self.ax.set_title(f"Kollektorausrichtung\nAzimut: {azimuth}°, Neigung: {tilt}°")
        self.canvas.draw()

    def getInputs(self):
        inputs = {
            'bruttofläche_STA': float(self.areaSInput.text()),
            'vs': float(self.vsInput.text()),
            'Typ': self.typeInput.itemText(self.typeInput.currentIndex()),
            'Tsmax': float(self.TsmaxInput.text()),
            'Longitude': float(self.LongitudeInput.text()),
            'STD_Longitude': int(self.STD_LongitudeInput.text()),
            'Latitude': float(self.LatitudeInput.text()),
            'East_West_collector_azimuth_angle': float(self.East_West_collector_azimuth_angleInput.text()),
            'Collector_tilt_angle': float(self.Collector_tilt_angleInput.text()),
            'Tm_rl': float(self.Tm_rlInput.text()),
            'Qsa': float(self.QsaInput.text()),
            'Vorwärmung_K': float(self.Vorwärmung_KInput.text()),
            'DT_WT_Solar_K': float(self.DT_WT_Solar_KInput.text()),
            'DT_WT_Netz_K': float(self.DT_WT_Netz_KInput.text()),
            'kosten_speicher_spez': float(self.vscostInput.text()),
            'kosten_fk_spez': float(self.areaScostfkInput.text()),
            'kosten_vrk_spez': float(self.areaScostvrkInput.text()),
            'opt_volume_min': float(self.minVolumeInput.text()),
            'opt_volume_max': float(self.maxVolumeInput.text()),
            'opt_area_min': float(self.minAreaInput.text()),
            'opt_area_max': float(self.maxAreaInput.text())
        }
        return inputs
  
class BiomassBoilerDialog(QDialog):
    def __init__(self, tech_data=None):
        super(BiomassBoilerDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Eingabe für Biomassekessel")
        layout = QVBoxLayout()

        self.PBMKInput = QLineEdit(self)
        self.PBMKInput.setText(str(self.tech_data.get('P_BMK', "50")))
        layout.addWidget(QLabel("th. Leistung in kW"))
        layout.addWidget(self.PBMKInput)

        self.HLsizeInput = QLineEdit(self)
        self.HLsizeInput.setText(str(self.tech_data.get('Größe_Holzlager', "40")))
        layout.addWidget(QLabel("Größe Holzlager in t"))
        layout.addWidget(self.HLsizeInput)

        self.BMKcostInput = QLineEdit(self)
        self.BMKcostInput.setText(str(self.tech_data.get('spez_Investitionskosten', "200")))
        layout.addWidget(QLabel("spez. Investitionskosten Kessel in €/kW"))
        layout.addWidget(self.BMKcostInput)

        self.HLcostInput = QLineEdit(self)
        self.HLcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_Holzlager', "400")))
        layout.addWidget(QLabel("spez. Investitionskosten Holzlager in €/t"))
        layout.addWidget(self.HLcostInput)

        # Eingabe Nutzungsgrad Biomassekessel
        self.BMKeffInput = QLineEdit(self)
        self.BMKeffInput.setText(str(self.tech_data.get('Nutzungsgrad_BMK', "0.8")))
        layout.addWidget(QLabel("Nutzungsgrad Biomassekessel"))
        layout.addWidget(self.BMKeffInput)

        # Eingabe für minimale Teillast
        self.minLoadInput = QLineEdit(self)
        self.minLoadInput.setText(str(self.tech_data.get('min_Teillast', "0.3")))
        layout.addWidget(QLabel("minimale Teillast"))
        layout.addWidget(self.minLoadInput)

        # Optimierung BHKW
        self.minPoptInput = QLineEdit(self)
        self.minPoptInput.setText(str(self.tech_data.get('opt_BMK_min', "0")))
        layout.addWidget(QLabel("Untere Grenze th. Leistung Optimierung"))
        layout.addWidget(self.minPoptInput)

        self.maxPoptInput = QLineEdit(self)
        self.maxPoptInput.setText(str(self.tech_data.get('opt_BMK_max', "1000")))
        layout.addWidget(QLabel("Obere Grenze th. Leistung Optimierung"))
        layout.addWidget(self.maxPoptInput)

        # Checkbox für Speicher aktiv
        self.speicherAktivCheckbox = QCheckBox("Speicher aktiv", self)
        self.speicherAktivCheckbox.setChecked(self.tech_data.get('speicher_aktiv', False))
        self.speicherAktivCheckbox.stateChanged.connect(self.toggleSpeicherInputs)
        layout.addWidget(self.speicherAktivCheckbox)

        # Speicher Eingaben
        self.speicherInputs = QWidget()
        speicherLayout = QVBoxLayout()

        # Eingabe für Speicher Volumen
        self.speicherVolInput = QLineEdit(self.speicherInputs)
        self.speicherVolInput.setText(str(self.tech_data.get('Speicher_Volumen', "20")))
        speicherLayout.addWidget(QLabel("Speicher Volumen"))
        speicherLayout.addWidget(self.speicherVolInput)

        # Eingabe für Vorlauftemperatur
        self.vorlaufTempInput = QLineEdit(self.speicherInputs)
        self.vorlaufTempInput.setText(str(self.tech_data.get('T_vorlauf', "90")))
        speicherLayout.addWidget(QLabel("Vorlauftemperatur"))
        speicherLayout.addWidget(self.vorlaufTempInput)

        # Eingabe für Rücklauftemperatur
        self.ruecklaufTempInput = QLineEdit(self.speicherInputs)
        self.ruecklaufTempInput.setText(str(self.tech_data.get('T_ruecklauf', "60")))
        speicherLayout.addWidget(QLabel("Rücklauftemperatur"))
        speicherLayout.addWidget(self.ruecklaufTempInput)

        # Eingabe für initiale Füllung
        self.initialFillInput = QLineEdit(self.speicherInputs)
        self.initialFillInput.setText(str(self.tech_data.get('initial_fill', "0.0")))
        speicherLayout.addWidget(QLabel("initiale Füllung"))
        speicherLayout.addWidget(self.initialFillInput)

        # Eingabe für minimale Füllung
        self.minFillInput = QLineEdit(self.speicherInputs)
        self.minFillInput.setText(str(self.tech_data.get('min_fill', "0.2")))
        speicherLayout.addWidget(QLabel("minimale Füllung"))
        speicherLayout.addWidget(self.minFillInput)

        # Eingabe für maximale Füllung
        self.maxFillInput = QLineEdit(self.speicherInputs)
        self.maxFillInput.setText(str(self.tech_data.get('max_fill', "0.8")))
        speicherLayout.addWidget(QLabel("maximale Füllung"))
        speicherLayout.addWidget(self.maxFillInput)

        # Eingabe für Speicherkosten
        self.spezCostStorageInput = QLineEdit(self.speicherInputs)
        self.spezCostStorageInput.setText(str(self.tech_data.get('spez_Investitionskosten_Speicher', "750")))
        speicherLayout.addWidget(QLabel("spez. Investitionskosten Speicher in €/m³"))
        speicherLayout.addWidget(self.spezCostStorageInput)

        # Optimierung Speicher
        self.minVolumeoptInput = QLineEdit(self.speicherInputs)
        self.minVolumeoptInput.setText(str(self.tech_data.get('opt_Speicher_min', "0")))
        speicherLayout.addWidget(QLabel("Untere Grenze Speichervolumen Optimierung"))
        speicherLayout.addWidget(self.minVolumeoptInput)

        self.maxVolumeoptInput = QLineEdit(self.speicherInputs)
        self.maxVolumeoptInput.setText(str(self.tech_data.get('opt_Speicher_max', "100")))
        speicherLayout.addWidget(QLabel("Obere Grenze Speichervolumen Optimierung"))
        speicherLayout.addWidget(self.maxVolumeoptInput)
                                 
        self.speicherInputs.setLayout(speicherLayout)
        layout.addWidget(self.speicherInputs)

        self.setLayout(layout)

    def toggleSpeicherInputs(self):
        self.speicherInputs.setVisible(self.speicherAktivCheckbox.isChecked())

    def getInputs(self):
        inputs = {
            'P_BMK': float(self.PBMKInput.text()),
            'Größe_Holzlager': float(self.HLsizeInput.text()),
            'spez_Investitionskosten': float(self.BMKcostInput.text()),
            'spez_Investitionskosten_Holzlager': float(self.HLcostInput.text()),
            'Nutzungsgrad_BMK': float(self.BMKeffInput.text()),
            'min_Teillast': float(self.minLoadInput.text()),
            'speicher_aktiv': self.speicherAktivCheckbox.isChecked(),
            'opt_BMK_min': float(self.minPoptInput.text()),
            'opt_BMK_max': float(self.maxPoptInput.text()),
        }

        if self.speicherAktivCheckbox.isChecked():
            inputs.update({
                'Speicher_Volumen': float(self.speicherVolInput.text()),
                'T_vorlauf': float(self.vorlaufTempInput.text()),
                'T_ruecklauf': float(self.ruecklaufTempInput.text()),
                'initial_fill': float(self.initialFillInput.text()),
                'min_fill': float(self.minFillInput.text()),
                'max_fill': float(self.maxFillInput.text()),
                'spez_Investitionskosten_Speicher': float(self.spezCostStorageInput.text()),
                'opt_BMK_Speicher_min': float(self.minVolumeoptInput.text()),
                'opt_BMK_Speicher_max': float(self.maxVolumeoptInput.text())
            })

        return inputs
    
class GasBoilerDialog(QDialog):
    def __init__(self, tech_data=None):
        super(GasBoilerDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Eingabe für Gaskessel")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("aktuell keine Dimensionierungseingaben, Leistung wird anhand der Gesamtlast berechnet"))
        self.spezcostGKInput = QLineEdit(self)
        self.spezcostGKInput.setText(str(self.tech_data.get('spez_Investitionskosten', "30")))
        layout.addWidget(QLabel("spez. Investitionskosten in €/kW"))
        layout.addWidget(self.spezcostGKInput)

        self.setLayout(layout)

    def getInputs(self):
        inputs = {
            'spez_Investitionskosten': float(self.spezcostGKInput.text())
        }
        return inputs
    
class CHPDialog(QDialog):
    def __init__(self, tech_data=None):
        super(CHPDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Eingabe für thermische Leistung
        self.PBHKWInput = QLineEdit(self)
        self.PBHKWInput.setText(str(self.tech_data.get('th_Leistung_BHKW', "100")))
        layout.addWidget(QLabel("thermische Leistung"))
        layout.addWidget(self.PBHKWInput)

        # Eingabe für elektrischen Wirkungsgrad BHKW
        self.BHKWeleffInput = QLineEdit(self)
        self.BHKWeleffInput.setText(str(self.tech_data.get('el_Wirkungsgrad', "0.33")))
        layout.addWidget(QLabel("elektrischer Wirkungsgrad BHKW"))
        layout.addWidget(self.BHKWeleffInput)

        # Eingabe für KWK Wirkungsgrad
        self.KWKeffInput = QLineEdit(self)
        self.KWKeffInput.setText(str(self.tech_data.get('KWK_Wirkungsgrad', "0.9")))
        layout.addWidget(QLabel("KWK Wirkungsgrad"))
        layout.addWidget(self.KWKeffInput)

        # Eingabe für minimale Teillast
        self.minLoadInput = QLineEdit(self)
        self.minLoadInput.setText(str(self.tech_data.get('min_Teillast', "0.7")))
        layout.addWidget(QLabel("minimale Teillast"))
        layout.addWidget(self.minLoadInput)

        # Eingabe für spez. Investitionskosten BHKW
        self.BHKWcostInput = QLineEdit(self)
        self.BHKWcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_GBHKW', "1500")))
        layout.addWidget(QLabel("spez. Investitionskosten BHKW"))
        layout.addWidget(self.BHKWcostInput)

        # Optimierung BHKW
        self.minPoptInput = QLineEdit(self)
        self.minPoptInput.setText(str(self.tech_data.get('opt_BHKW_min', "0")))
        layout.addWidget(QLabel("Untere Grenze th. Leistung Optimierung"))
        layout.addWidget(self.minPoptInput)

        self.maxPoptInput = QLineEdit(self)
        self.maxPoptInput.setText(str(self.tech_data.get('opt_BHKW_max', "1000")))
        layout.addWidget(QLabel("Obere Grenze th. Leistung Optimierung"))
        layout.addWidget(self.maxPoptInput)

        # Checkbox für Speicher aktiv
        self.speicherAktivCheckbox = QCheckBox("Speicher aktiv", self)
        self.speicherAktivCheckbox.setChecked(self.tech_data.get('speicher_aktiv', False))
        self.speicherAktivCheckbox.stateChanged.connect(self.toggleSpeicherInputs)
        layout.addWidget(self.speicherAktivCheckbox)

        # Speicher Eingaben
        self.speicherInputs = QWidget()
        speicherLayout = QVBoxLayout()

        # Eingabe für Speicher Volumen
        self.speicherVolInput = QLineEdit(self.speicherInputs)
        self.speicherVolInput.setText(str(self.tech_data.get('Speicher_Volumen_BHKW', "20")))
        speicherLayout.addWidget(QLabel("Speicher Volumen"))
        speicherLayout.addWidget(self.speicherVolInput)

        # Eingabe für Vorlauftemperatur
        self.vorlaufTempInput = QLineEdit(self.speicherInputs)
        self.vorlaufTempInput.setText(str(self.tech_data.get('T_vorlauf', "90")))
        speicherLayout.addWidget(QLabel("Vorlauftemperatur"))
        speicherLayout.addWidget(self.vorlaufTempInput)

        # Eingabe für Rücklauftemperatur
        self.ruecklaufTempInput = QLineEdit(self.speicherInputs)
        self.ruecklaufTempInput.setText(str(self.tech_data.get('T_ruecklauf', "60")))
        speicherLayout.addWidget(QLabel("Rücklauftemperatur"))
        speicherLayout.addWidget(self.ruecklaufTempInput)

        # Eingabe für initiale Füllung
        self.initialFillInput = QLineEdit(self.speicherInputs)
        self.initialFillInput.setText(str(self.tech_data.get('initial_fill', "0.0")))
        speicherLayout.addWidget(QLabel("initiale Füllung"))
        speicherLayout.addWidget(self.initialFillInput)

        # Eingabe für minimale Füllung
        self.minFillInput = QLineEdit(self.speicherInputs)
        self.minFillInput.setText(str(self.tech_data.get('min_fill', "0.2")))
        speicherLayout.addWidget(QLabel("minimale Füllung"))
        speicherLayout.addWidget(self.minFillInput)

        # Eingabe für maximale Füllung
        self.maxFillInput = QLineEdit(self.speicherInputs)
        self.maxFillInput.setText(str(self.tech_data.get('max_fill', "0.8")))
        speicherLayout.addWidget(QLabel("maximale Füllung"))
        speicherLayout.addWidget(self.maxFillInput)

        # Eingabe für Speicherkosten
        self.spezCostStorageInput = QLineEdit(self.speicherInputs)
        self.spezCostStorageInput.setText(str(self.tech_data.get('spez_Investitionskosten_Speicher', "0.8")))
        speicherLayout.addWidget(QLabel("spez. Investitionskosten Speicher in €/m³"))
        speicherLayout.addWidget(self.spezCostStorageInput)

        # Optimierung Speicher
        self.minVolumeoptInput = QLineEdit(self.speicherInputs)
        self.minVolumeoptInput.setText(str(self.tech_data.get('opt_BHKW_Speicher_min', "0")))
        speicherLayout.addWidget(QLabel("Untere Grenze Speichervolumen Optimierung"))
        speicherLayout.addWidget(self.minVolumeoptInput)

        self.maxVolumeoptInput = QLineEdit(self.speicherInputs)
        self.maxVolumeoptInput.setText(str(self.tech_data.get('opt_BHKW_Speicher_max', "100")))
        speicherLayout.addWidget(QLabel("Obere Grenze Speichervolumen Optimierung"))
        speicherLayout.addWidget(self.maxVolumeoptInput)
                                 
        self.speicherInputs.setLayout(speicherLayout)
        layout.addWidget(self.speicherInputs)

        self.setLayout(layout)

        # Initiale Sichtbarkeit der Speicher Eingaben einstellen
        self.toggleSpeicherInputs()

    def toggleSpeicherInputs(self):
        self.speicherInputs.setVisible(self.speicherAktivCheckbox.isChecked())

    def getInputs(self):
        inputs = {
            'th_Leistung_BHKW': float(self.PBHKWInput.text()),
            'el_Wirkungsgrad': float(self.BHKWeleffInput.text()),
            'spez_Investitionskosten_GBHKW': float(self.BHKWcostInput.text()),
            'KWK_Wirkungsgrad': float(self.KWKeffInput.text()),
            'min_Teillast': float(self.minLoadInput.text()),
            'speicher_aktiv': self.speicherAktivCheckbox.isChecked(),
            'opt_BHKW_min': float(self.minPoptInput.text()),
            'opt_BHKW_max': float(self.maxPoptInput.text()),
        }

        if self.speicherAktivCheckbox.isChecked():
            inputs.update({
                'Speicher_Volumen_BHKW': float(self.speicherVolInput.text()),
                'T_vorlauf': float(self.vorlaufTempInput.text()),
                'T_ruecklauf': float(self.ruecklaufTempInput.text()),
                'initial_fill': float(self.initialFillInput.text()),
                'min_fill': float(self.minFillInput.text()),
                'max_fill': float(self.maxFillInput.text()),
                'spez_Investitionskosten_Speicher': float(self.spezCostStorageInput.text()),
                'opt_BHKW_Speicher_min': float(self.minVolumeoptInput.text()),
                'opt_BHKW_Speicher_max': float(self.maxVolumeoptInput.text())
            })

        return inputs
    
class HolzgasCHPDialog(QDialog):
    def __init__(self, tech_data=None):
        super(HolzgasCHPDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.PBHKWInput = QLineEdit(self)
        self.PBHKWInput.setText(str(self.tech_data.get('th_Leistung_BHKW', "100")))
        layout.addWidget(QLabel("thermische Leistung"))
        layout.addWidget(self.PBHKWInput)

        # Eingabe für elektrischen Wirkungsgrad BHKW
        self.BHKWeleffInput = QLineEdit(self)
        self.BHKWeleffInput.setText(str(self.tech_data.get('el_Wirkungsgrad', "0.33")))
        layout.addWidget(QLabel("elektrischer Wirkungsgrad BHKW"))
        layout.addWidget(self.BHKWeleffInput)

        # Eingabe für KWK Wirkungsgrad
        self.KWKeffInput = QLineEdit(self)
        self.KWKeffInput.setText(str(self.tech_data.get('KWK_Wirkungsgrad', "0.9")))
        layout.addWidget(QLabel("KWK Wirkungsgrad"))
        layout.addWidget(self.KWKeffInput)

        # Eingabe für minimale Teillast
        self.minLoadInput = QLineEdit(self)
        self.minLoadInput.setText(str(self.tech_data.get('min_Teillast', "0.7")))
        layout.addWidget(QLabel("minimale Teillast"))
        layout.addWidget(self.minLoadInput)

        self.BHKWcostInput = QLineEdit(self)
        self.BHKWcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_HBHKW', "1850")))
        layout.addWidget(QLabel("spez. Investitionskosten BHKW"))
        layout.addWidget(self.BHKWcostInput)

        # Optimierung BHKW
        self.minPoptInput = QLineEdit(self)
        self.minPoptInput.setText(str(self.tech_data.get('opt_BHKW_min', "0")))
        layout.addWidget(QLabel("Untere Grenze th. Leistung Optimierung"))
        layout.addWidget(self.minPoptInput)

        self.maxPoptInput = QLineEdit(self)
        self.maxPoptInput.setText(str(self.tech_data.get('opt_BHKW_max', "1000")))
        layout.addWidget(QLabel("Obere Grenze th. Leistung Optimierung"))
        layout.addWidget(self.maxPoptInput)

        # Checkbox für Speicher aktiv
        self.speicherAktivCheckbox = QCheckBox("Speicher aktiv", self)
        self.speicherAktivCheckbox.setChecked(self.tech_data.get('speicher_aktiv', False))
        self.speicherAktivCheckbox.stateChanged.connect(self.toggleSpeicherInputs)
        layout.addWidget(self.speicherAktivCheckbox)

        # Speicher Eingaben
        self.speicherInputs = QWidget()
        speicherLayout = QVBoxLayout()

        # Eingabe für Speicher Volumen
        self.speicherVolInput = QLineEdit(self.speicherInputs)
        self.speicherVolInput.setText(str(self.tech_data.get('Speicher_Volumen_BHKW', "20")))
        speicherLayout.addWidget(QLabel("Speicher Volumen"))
        speicherLayout.addWidget(self.speicherVolInput)

        # Eingabe für Vorlauftemperatur
        self.vorlaufTempInput = QLineEdit(self.speicherInputs)
        self.vorlaufTempInput.setText(str(self.tech_data.get('T_vorlauf', "90")))
        speicherLayout.addWidget(QLabel("Vorlauftemperatur"))
        speicherLayout.addWidget(self.vorlaufTempInput)

        # Eingabe für Rücklauftemperatur
        self.ruecklaufTempInput = QLineEdit(self.speicherInputs)
        self.ruecklaufTempInput.setText(str(self.tech_data.get('T_ruecklauf', "60")))
        speicherLayout.addWidget(QLabel("Rücklauftemperatur"))
        speicherLayout.addWidget(self.ruecklaufTempInput)

        # Eingabe für initiale Füllung
        self.initialFillInput = QLineEdit(self.speicherInputs)
        self.initialFillInput.setText(str(self.tech_data.get('initial_fill', "0.0")))
        speicherLayout.addWidget(QLabel("initiale Füllung"))
        speicherLayout.addWidget(self.initialFillInput)

        # Eingabe für minimale Füllung
        self.minFillInput = QLineEdit(self.speicherInputs)
        self.minFillInput.setText(str(self.tech_data.get('min_fill', "0.2")))
        speicherLayout.addWidget(QLabel("minimale Füllung"))
        speicherLayout.addWidget(self.minFillInput)

        # Eingabe für maximale Füllung
        self.maxFillInput = QLineEdit(self.speicherInputs)
        self.maxFillInput.setText(str(self.tech_data.get('max_fill', "0.8")))
        speicherLayout.addWidget(QLabel("maximale Füllung"))
        speicherLayout.addWidget(self.maxFillInput)

        # Eingabe für Speicherkosten
        self.spezCostStorageInput = QLineEdit(self.speicherInputs)
        self.spezCostStorageInput.setText(str(self.tech_data.get('spez_Investitionskosten_Speicher', "0.8")))
        speicherLayout.addWidget(QLabel("spez. Investitionskosten Speicher in €/m³"))
        speicherLayout.addWidget(self.spezCostStorageInput)

        # Optimierung Speicher
        self.minVolumeoptInput = QLineEdit(self.speicherInputs)
        self.minVolumeoptInput.setText(str(self.tech_data.get('opt_BHKW_Speicher_min', "0")))
        speicherLayout.addWidget(QLabel("Untere Grenze Speichervolumen Optimierung"))
        speicherLayout.addWidget(self.minVolumeoptInput)

        self.maxVolumeoptInput = QLineEdit(self.speicherInputs)
        self.maxVolumeoptInput.setText(str(self.tech_data.get('opt_BHKW_Speicher_max', "100")))
        speicherLayout.addWidget(QLabel("Obere Grenze Speichervolumen Optimierung"))
        speicherLayout.addWidget(self.maxVolumeoptInput)

        self.speicherInputs.setLayout(speicherLayout)
        layout.addWidget(self.speicherInputs)

        self.setLayout(layout)

        # Initiale Sichtbarkeit der Speicher Eingaben einstellen
        self.toggleSpeicherInputs()

    def toggleSpeicherInputs(self):
        self.speicherInputs.setVisible(self.speicherAktivCheckbox.isChecked())

    def getInputs(self):
        inputs = {
            'th_Leistung_BHKW': float(self.PBHKWInput.text()),
            'el_Wirkungsgrad': float(self.BHKWeleffInput.text()),
            'spez_Investitionskosten_GBHKW': float(self.BHKWcostInput.text()),
            'KWK_Wirkungsgrad': float(self.KWKeffInput.text()),
            'min_Teillast': float(self.minLoadInput.text()),
            'speicher_aktiv': self.speicherAktivCheckbox.isChecked(),
            'opt_BHKW_min': float(self.minPoptInput.text()),
            'opt_BHKW_max': float(self.maxPoptInput.text()),
        }

        if self.speicherAktivCheckbox.isChecked():
            inputs.update({
                'Speicher_Volumen_BHKW': float(self.speicherVolInput.text()),
                'T_vorlauf': float(self.vorlaufTempInput.text()),
                'T_ruecklauf': float(self.ruecklaufTempInput.text()),
                'initial_fill': float(self.initialFillInput.text()),
                'min_fill': float(self.minFillInput.text()),
                'max_fill': float(self.maxFillInput.text()),
                'spez_Investitionskosten_Speicher': float(self.spezCostStorageInput.text()),
                'opt_BHKW_Speicher_min': float(self.minVolumeoptInput.text()),
                'opt_BHKW_Speicher_max': float(self.maxVolumeoptInput.text())
            })

        return inputs
    
class GeothermalDialog(QWidget):
    def __init__(self, tech_data=None):
        super(GeothermalDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        form_layout = QFormLayout()

        self.areaGInput = QLineEdit(self)
        self.areaGInput.setText(str(self.tech_data.get('Fläche', "100")))
        form_layout.addRow(QLabel("Fläche Erdsondenfeld in m²"), self.areaGInput)

        self.depthInput = QLineEdit(self)
        self.depthInput.setText(str(self.tech_data.get('Bohrtiefe', "100")))
        form_layout.addRow(QLabel("Bohrtiefe Sonden in m"), self.depthInput)

        self.tempGInput = QLineEdit(self)
        self.tempGInput.setText(str(self.tech_data.get('Temperatur_Geothermie', "10")))
        form_layout.addRow(QLabel("Quelltemperatur in °C"), self.tempGInput)

        self.distholeInput = QLineEdit(self)
        self.distholeInput.setText(str(self.tech_data.get('Abstand_Sonden', "10")))
        form_layout.addRow(QLabel("Abstand Erdsonden in m"), self.distholeInput)

        self.costdethInput = QLineEdit(self)
        self.costdethInput.setText(str(self.tech_data.get('spez_Bohrkosten', "120")))
        form_layout.addRow(QLabel("spez. Bohrkosten pro Bohrmeter in €/m"), self.costdethInput)

        self.spezPInput = QLineEdit(self)
        self.spezPInput.setText(str(self.tech_data.get('spez_Entzugsleistung', "50")))
        form_layout.addRow(QLabel("spez. Entzugsleistung Untergrund in W/m"), self.spezPInput)

        self.VBHInput = QLineEdit(self)
        self.VBHInput.setText(str(self.tech_data.get('Vollbenutzungsstunden', "2400")))
        form_layout.addRow(QLabel("Vollbenutzungsstunden Sondenfeld in h"), self.VBHInput)

        self.WPGcostInput = QLineEdit(self)
        self.WPGcostInput.setText(str(self.tech_data.get('spezifische_Investitionskosten_WP', "1000")))
        form_layout.addRow(QLabel("spez. Investitionskosten Wärmepumpe in €/kW"), self.WPGcostInput)

        top_layout.addLayout(form_layout)

        # Visualization
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111, projection='3d')
        self.canvas = FigureCanvas(self.figure)
        top_layout.addWidget(self.canvas)

        main_layout.addLayout(top_layout)

        # Connect input changes to the visualization update
        self.areaGInput.textChanged.connect(self.updateVisualization)
        self.depthInput.textChanged.connect(self.updateVisualization)
        self.distholeInput.textChanged.connect(self.updateVisualization)

        self.setLayout(main_layout)
        self.updateVisualization()

    def updateVisualization(self):
        try:
            area = float(self.areaGInput.text())
            depth = float(self.depthInput.text())
            distance = float(self.distholeInput.text())
        except ValueError:
            area = 100
            depth = 100
            distance = 10

        self.ax.clear()

        # Calculate the number of boreholes in a grid
        side_length = np.sqrt(area)
        num_holes_per_side = int(side_length / distance) + 1
        x_positions = np.linspace(0, side_length, num_holes_per_side)
        y_positions = np.linspace(0, side_length, num_holes_per_side)
        x_positions, y_positions = np.meshgrid(x_positions, y_positions)

        # Draw the boreholes
        for x, y in zip(x_positions.flatten(), y_positions.flatten()):
            self.ax.plot([x, x], [y, y], [0, -depth], color='blue')

        # Set plot limits
        self.ax.set_xlim([0, side_length])
        self.ax.set_ylim([0, side_length])
        self.ax.set_zlim([-depth, 0])

        # Label axes
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (Tiefe in m)')

        self.ax.set_title(f"Sondenkonfiguration\nFläche: {area} m², Tiefe: {depth} m, Abstand: {distance} m")
        self.canvas.draw()

    def getInputs(self):
        inputs = {
            'Fläche': float(self.areaGInput.text()),
            'Bohrtiefe': float(self.depthInput.text()),
            'Temperatur_Geothermie': float(self.tempGInput.text()),
            'Abstand_Sonden': float(self.distholeInput.text()),
            'spez_Bohrkosten': float(self.costdethInput.text()),
            'spez_Entzugsleistung': float(self.spezPInput.text()),
            'Vollbenutzungsstunden': float(self.VBHInput.text()),
            'spezifische_Investitionskosten_WP': float(self.WPGcostInput.text())
        }
        return inputs
    
class WasteHeatPumpDialog(QDialog):
    def __init__(self, tech_data=None):
        super(WasteHeatPumpDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.PWHInput = QLineEdit(self)
        self.PWHInput.setText(str(self.tech_data.get('Kühlleistung_Abwärme', "30")))
        layout.addWidget(QLabel("Kühlleistung Abwärme in kW"))
        layout.addWidget(self.PWHInput)

        self.TWHInput = QLineEdit(self)
        self.TWHInput.setText(str(self.tech_data.get('Temperatur_Abwärme', "30")))
        layout.addWidget(QLabel("Temperatur Abwärme in °C"))
        layout.addWidget(self.TWHInput)

        self.WHcostInput = QLineEdit(self)
        self.WHcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_Abwärme', "500")))
        layout.addWidget(QLabel("spez. Investitionskosten Abwärmenutzung in €/kW"))
        layout.addWidget(self.WHcostInput)

        self.WPWHcostInput = QLineEdit(self)
        self.WPWHcostInput.setText(str(self.tech_data.get('spezifische_Investitionskosten_WP', "1000")))
        layout.addWidget(QLabel("spez. Invstitionskosten Wärmepumpe"))
        layout.addWidget(self.WPWHcostInput)

        self.setLayout(layout)

    def getInputs(self):
        inputs = {
            'Kühlleistung_Abwärme': float(self.PWHInput.text()),
            'Temperatur_Abwärme': float(self.TWHInput.text()),
            'spez_Investitionskosten_Abwärme': float(self.WHcostInput.text()),
            'spezifische_Investitionskosten_WP': float(self.WPWHcostInput.text())
        }
        return inputs
    
class RiverHeatPumpDialog(QDialog):
    def __init__(self, tech_data=None):
        super(RiverHeatPumpDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.PFWInput = QLineEdit(self)
        self.PFWInput.setText(str(self.tech_data.get('Wärmeleistung_FW_WP', "200")))
        layout.addWidget(QLabel("th. Leistung Wärmepumpe in kW"))
        layout.addWidget(self.PFWInput)

        self.TFWInput = QLineEdit(self)
        if isinstance(self.tech_data.get('Temperatur_FW_WP'), (float, int)) or self.tech_data == {}:
            self.TFWInput.setText(str(self.tech_data.get('Temperatur_FW_WP', "10")))
        layout.addWidget(QLabel("Flusstemperatur in °C"))
        layout.addWidget(self.TFWInput)

        self.csvButton = QPushButton("CSV für Flusstemperatur wählen", self)
        self.csvButton.clicked.connect(self.openCSV)
        layout.addWidget(self.csvButton)

        self.DTFWInput = QLineEdit(self)
        self.DTFWInput.setText(str(self.tech_data.get('dT', "0")))
        layout.addWidget(QLabel("Zulässige Abweichung Vorlauftemperatur Wärmepumpe von Netzvorlauftemperatur"))
        layout.addWidget(self.DTFWInput)

        self.RHcostInput = QLineEdit(self)
        self.RHcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_Flusswasser', "1000")))
        layout.addWidget(QLabel("spez. Invstitionskosten Flusswärmenutzung"))
        layout.addWidget(self.RHcostInput)

        self.WPRHcostInput = QLineEdit(self)
        self.WPRHcostInput.setText(str(self.tech_data.get('spezifische_Investitionskosten_WP', "1000")))
        layout.addWidget(QLabel("spez. Invstitionskosten Wärmepumpe"))
        layout.addWidget(self.WPRHcostInput)

        self.setLayout(layout)

    def openCSV(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        if filename:
            self.loadCSV(filename)

    def loadCSV(self, filename):
        data = np.loadtxt(filename, delimiter=';', skiprows=1, usecols=1).astype(float)
        self.csvData = data
        QMessageBox.information(self, "CSV geladen", f"CSV-Datei {filename} erfolgreich geladen.")

    def getInputs(self):
        inputs = {
            'Wärmeleistung_FW_WP': float(self.PFWInput.text()),
            'dT': float(self.DTFWInput.text()),
            'spez_Investitionskosten_Flusswasser': float(self.RHcostInput.text()),
            'spezifische_Investitionskosten_WP': float(self.WPRHcostInput.text())
        }
        try:
            if hasattr(self, 'csvData'):
                inputs['Temperatur_FW_WP'] = self.csvData
            elif isinstance(self.tech_data.get('Temperatur_FW_WP'), (float, int)):
                inputs['Temperatur_FW_WP'] = float(self.TFWInput.text())
            elif isinstance(self.tech_data.get('Temperatur_FW_WP'), np.ndarray):
                inputs['Temperatur_FW_WP'] = self.tech_data.get('Temperatur_FW_WP')
            else:
                inputs['Temperatur_FW_WP'] = float(self.TFWInput.text())
        except ValueError:
            print("Ungültige Eingabe")
        return inputs
