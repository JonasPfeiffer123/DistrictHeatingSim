import sys
import os

import numpy as np

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, \
    QDialogButtonBox, QComboBox, QPushButton, QFileDialog, QMessageBox


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
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f"Eingabe für {self.tech_type}")
        layout = QVBoxLayout()

        if self.tech_type == "Solarthermie":
            self.areaSInput = QLineEdit(self)
            self.areaSInput.setText(str(self.tech_data.get('bruttofläche_STA', "200")))
            layout.addWidget(QLabel("Kollektorbruttofläche in m²"))
            layout.addWidget(self.areaSInput)

            # volume solar heat storage
            self.vsInput = QLineEdit(self)
            self.vsInput.setText(str(self.tech_data.get('vs', "20")))
            layout.addWidget(QLabel("Solarspeichervolumen in m³"))
            layout.addWidget(self.vsInput)

            # type
            self.typeInput = QComboBox(self)
            self.techOptions = ["Vakuumröhrenkollektor", "Flachkollektor"]
            self.typeInput.addItems(self.techOptions)

            # Setzen des aktuellen Kollektortyps, falls vorhanden
            if 'Typ' in self.tech_data:
                current_type_index = self.techOptions.index(self.tech_data['Typ'])
                self.typeInput.setCurrentIndex(current_type_index)

            layout.addWidget(QLabel("Kollektortyp"))
            layout.addWidget(self.typeInput)

            # max solar heat storage temperature
            self.TsmaxInput = QLineEdit(self)
            self.TsmaxInput.setText(str(self.tech_data.get('Tsmax', "90")))
            layout.addWidget(QLabel("Maximale Speichertemperatur in °C"))
            layout.addWidget(self.TsmaxInput)

            # Longitude
            self.LongitudeInput = QLineEdit(self)
            self.LongitudeInput.setText(str(self.tech_data.get('Longitude', "-14.4222")))
            layout.addWidget(QLabel("Longitude des Erzeugerstandortes"))
            layout.addWidget(self.LongitudeInput)

            # STD_Longitude
            self.STD_LongitudeInput = QLineEdit(self)
            self.STD_LongitudeInput.setText(str(self.tech_data.get('STD_Longitude', "15")))
            layout.addWidget(QLabel("STD_Longitude des Erzeugerstandortes"))
            layout.addWidget(self.STD_LongitudeInput)

            # Latitude
            self.LatitudeInput = QLineEdit(self)
            self.LatitudeInput.setText(str(self.tech_data.get('Latitude', "51.1676")))
            layout.addWidget(QLabel("Latitude des Erzeugerstandortes"))
            layout.addWidget(self.LatitudeInput)

            # East_West_collector_azimuth_angle
            self.East_West_collector_azimuth_angleInput = QLineEdit(self)
            self.East_West_collector_azimuth_angleInput.setText(str(self.tech_data.get('East_West_collector_azimuth_angle', "0")))
            layout.addWidget(QLabel("Azimuth-Ausrichtung des Kollektors in °"))
            layout.addWidget(self.East_West_collector_azimuth_angleInput)

            # Collector_tilt_angle
            self.Collector_tilt_angleInput = QLineEdit(self)
            self.Collector_tilt_angleInput.setText(str(self.tech_data.get('Collector_tilt_angle', "36")))
            layout.addWidget(QLabel("Neigungswinkel des Kollektors in ° (0-90)"))
            layout.addWidget(self.Collector_tilt_angleInput)

            # Return Temperature storage at start
            self.Tm_rlInput = QLineEdit(self)
            self.Tm_rlInput.setText(str(self.tech_data.get('Tm_rl', "60")))
            layout.addWidget(QLabel("Startwert Rücklauftemperatur in Speicher in °C"))
            layout.addWidget(self.Tm_rlInput)

            # storage level at start
            self.QsaInput = QLineEdit(self)
            self.QsaInput.setText(str(self.tech_data.get('Qsa', "0")))
            layout.addWidget(QLabel("Startwert Speicherfüllstand"))
            layout.addWidget(self.QsaInput)

            # storage level at start
            self.Vorwärmung_KInput = QLineEdit(self)
            self.Vorwärmung_KInput.setText(str(self.tech_data.get('Vorwärmung_K', "8")))
            layout.addWidget(QLabel("Mögliche Abweichung von Solltemperatur bei Vorwärmung"))
            layout.addWidget(self.Vorwärmung_KInput)

            # dT heat exchanger solar/storage
            self.DT_WT_Solar_KInput = QLineEdit(self)
            self.DT_WT_Solar_KInput.setText(str(self.tech_data.get('DT_WT_Solar_K', "5")))
            layout.addWidget(QLabel("Grädigkeit Wärmeübertrager Kollektor/Speicher"))
            layout.addWidget(self.DT_WT_Solar_KInput)

            # dT heat exchanger storage/net
            self.DT_WT_Netz_KInput = QLineEdit(self)
            self.DT_WT_Netz_KInput.setText(str(self.tech_data.get('DT_WT_Netz_K', "5")))
            layout.addWidget(QLabel("Grädigkeit Wärmeübertrager Speicher/Netz"))
            layout.addWidget(self.DT_WT_Netz_KInput)

            # cost storage and solar
            self.vscostInput = QLineEdit(self)
            self.vscostInput.setText(str(self.tech_data.get('kosten_speicher_spez', "750")))
            layout.addWidget(QLabel("spez. Kosten Solarspeicher in €/m³"))
            layout.addWidget(self.vscostInput)

            self.areaScostfkInput = QLineEdit(self)
            self.areaScostfkInput.setText(str(self.tech_data.get('kosten_fk_spez', "430")))
            layout.addWidget(QLabel("spez. Kosten Flachkollektor in €/m²"))
            layout.addWidget(self.areaScostfkInput)

            self.areaScostvrkInput = QLineEdit(self)
            self.areaScostvrkInput.setText(str(self.tech_data.get('kosten_vrk_spez', "590")))
            layout.addWidget(QLabel("spez. Kosten Vakuumröhrenkollektor in €/m²"))
            layout.addWidget(self.areaScostvrkInput)

        if self.tech_type == "Biomassekessel":
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

        if self.tech_type == "Gaskessel":
            layout.addWidget(QLabel("aktuell keine Dimensionierungseingaben, Leistung wird anhand der Gesamtlast berechnet"))
            self.spezcostGKInput = QLineEdit(self)
            self.spezcostGKInput.setText(str(self.tech_data.get('spez_Investitionskosten', "30")))
            layout.addWidget(QLabel("spez. Investitionskosten in €/kW"))
            layout.addWidget(self.spezcostGKInput)

        if self.tech_type == "BHKW":
            self.PBHKWInput = QLineEdit(self)
            self.PBHKWInput.setText(str(self.tech_data.get('th_Leistung_BHKW', "40")))
            layout.addWidget(QLabel("thermische Leistung"))
            layout.addWidget(self.PBHKWInput)

            self.GBHKWcostInput = QLineEdit(self)
            self.GBHKWcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_GBHKW', "1500")))
            layout.addWidget(QLabel("spez. Investitionskosten BHKW"))
            layout.addWidget(self.GBHKWcostInput)

        if self.tech_type == "Holzgas-BHKW":
            self.PHBHKWInput = QLineEdit(self)
            self.PHBHKWInput.setText(str(self.tech_data.get('th_Leistung_BHKW', "30")))
            layout.addWidget(QLabel("thermische Leistung"))
            layout.addWidget(self.PHBHKWInput)

            self.HBHKWcostInput = QLineEdit(self)
            self.HBHKWcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_HBHKW', "1850")))
            layout.addWidget(QLabel("spez. Investitionskosten BHKW"))
            layout.addWidget(self.HBHKWcostInput)

        if self.tech_type == "Geothermie":
            self.areaGInput = QLineEdit(self)
            self.areaGInput.setText(str(self.tech_data.get('Fläche', "100")))
            layout.addWidget(QLabel("Fläche Erdsondenfeld in m²"))
            layout.addWidget(self.areaGInput)

            self.depthInput = QLineEdit(self)
            self.depthInput.setText(str(self.tech_data.get('Bohrtiefe', "100")))
            layout.addWidget(QLabel("Bohrtiefe Sonden in m³"))
            layout.addWidget(self.depthInput)

            self.tempGInput = QLineEdit(self)
            self.tempGInput.setText(str(self.tech_data.get('Temperatur_Geothermie', "10")))
            layout.addWidget(QLabel("Quelltemperatur in °C"))
            layout.addWidget(self.tempGInput)

            self.distholeInput = QLineEdit(self)
            self.distholeInput.setText(str(self.tech_data.get('Abstand_Sonden', "10")))
            layout.addWidget(QLabel("Abstand Erdsonden in m"))
            layout.addWidget(self.distholeInput)

            self.costdethInput = QLineEdit(self)
            self.costdethInput.setText(str(self.tech_data.get('spez_Bohrkosten', "120")))
            layout.addWidget(QLabel("spez. Bohrkosten pro Bohrmeter in €/m"))
            layout.addWidget(self.costdethInput)

            self.spezPInput = QLineEdit(self)
            self.spezPInput.setText(str(self.tech_data.get('spez_Entzugsleistung', "50")))
            layout.addWidget(QLabel("spez. Entzugsleistung Untergrund in W/m"))
            layout.addWidget(self.spezPInput)

            self.VBHInput = QLineEdit(self)
            self.VBHInput.setText(str(self.tech_data.get('Vollbenutzungsstunden', "2400")))
            layout.addWidget(QLabel("Vollbenutzungsstunden Sondenfeld in h"))
            layout.addWidget(self.VBHInput)

            self.WPGcostInput = QLineEdit(self)
            self.WPGcostInput.setText(str(self.tech_data.get('spezifische_Investitionskosten_WP', "1000")))
            layout.addWidget(QLabel("spez. Invstitionskosten Wärmepumpe"))
            layout.addWidget(self.WPGcostInput)
        
        if self.tech_type == "Abwärme":
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

        if self.tech_type == "Flusswasser":
            self.PFWInput = QLineEdit(self)
            self.PFWInput.setText(str(self.tech_data.get('Wärmeleistung_FW_WP', "200")))
            layout.addWidget(QLabel("th. Leistung Wärmepumpe in kW"))
            layout.addWidget(self.PFWInput)

            # Flusstemperatur direkt eingeben
            self.TFWInput = QLineEdit(self)
            if type(self.tech_data.get('Temperatur_FW_WP')) is float or self.tech_data == {}:
                self.TFWInput.setText(str(self.tech_data.get('Temperatur_FW_WP', "10")))
            layout.addWidget(QLabel("Flusstemperatur in °C"))
            layout.addWidget(self.TFWInput)

            # Button zum Auswählen der CSV-Datei
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

        # OK und Abbrechen Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def openCSV(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        if filename:
            self.loadCSV(filename)

    def loadCSV(self, filename):
        # Laden der CSV-Daten als NumPy-Array
        # Beispiel für das Format: Erste Spalte Zeit, zweite Spalte Temperatur
        data = np.loadtxt(filename, delimiter=';', skiprows=1, usecols=1).astype(float)
        self.csvData = data
        # Optional: Bestätigen, dass die Datei geladen wurde
        QMessageBox.information(self, "CSV geladen", f"CSV-Datei {filename} erfolgreich geladen.")

    def getInputs(self):
        inputs = {}
        if self.tech_type == "Solarthermie":
            inputs['bruttofläche_STA'] = float(self.areaSInput.text())
            inputs["vs"] = float(self.vsInput.text())
            inputs["Typ"] = self.typeInput.itemText(self.typeInput.currentIndex())
            inputs["Tsmax"] = float(self.TsmaxInput.text())
            inputs["Longitude"] = float(self.LongitudeInput.text())
            inputs["STD_Longitude"] = int(self.STD_LongitudeInput.text())
            inputs["Latitude"] = float(self.LatitudeInput.text())
            inputs["East_West_collector_azimuth_angle"] = float(self.East_West_collector_azimuth_angleInput.text())
            inputs["Collector_tilt_angle"] = float(self.Collector_tilt_angleInput.text())
            inputs["Tm_rl"] = float(self.Tm_rlInput.text())
            inputs["Qsa"] = float(self.QsaInput.text())
            inputs["Vorwärmung_K"] = float(self.Vorwärmung_KInput.text())
            inputs["DT_WT_Solar_K"] = float(self.DT_WT_Solar_KInput.text())
            inputs["DT_WT_Netz_K"] = float(self.DT_WT_Netz_KInput.text())
            inputs["kosten_speicher_spez"] = float(self.vscostInput.text())
            inputs["kosten_fk_spez"] = float(self.areaScostfkInput.text())
            inputs["kosten_vrk_spez"] = float(self.areaScostvrkInput.text())

        elif self.tech_type == "Biomassekessel":
            inputs["P_BMK"] = float(self.PBMKInput.text())
            inputs["Größe_Holzlager"] = float(self.HLsizeInput.text())
            inputs["spez_Investitionskosten"] = float(self.BMKcostInput.text())
            inputs["spez_Investitionskosten_Holzlager"] = float(self.HLcostInput.text())
            
        elif self.tech_type == "Gaskessel":
            inputs["spez_Investitionskosten"] = float(self.spezcostGKInput.text())

        elif self.tech_type == "BHKW":
            inputs["th_Leistung_BHKW"] = float(self.PBHKWInput.text())
            inputs["spez_Investitionskosten_GBHKW"] = float(self.GBHKWcostInput.text())

        elif self.tech_type == "Holzgas-BHKW":
            inputs["th_Leistung_BHKW"] = float(self.PHBHKWInput.text())
            inputs["spez_Investitionskosten_HBHKW"] = float(self.HBHKWcostInput.text())

        elif self.tech_type == "Geothermie":
            inputs["Fläche"] = float(self.areaGInput.text())
            inputs["Bohrtiefe"] = float(self.depthInput.text())
            inputs["Temperatur_Geothermie"] = float(self.tempGInput.text())
            inputs["Abstand_Sonden"] = float(self.distholeInput.text())
            inputs["spez_Bohrkosten"] = float(self.costdethInput.text())
            inputs["spez_Entzugsleistung"] = float(self.spezPInput.text())
            inputs["Vollbenutzungsstunden"] = float(self.VBHInput.text())
            inputs["spezifische_Investitionskosten_WP"] = float(self.WPGcostInput.text())

        elif self.tech_type == "Abwärme":
            inputs["Kühlleistung_Abwärme"] = float(self.PWHInput.text())
            inputs["Temperatur_Abwärme"] = float(self.TWHInput.text())
            inputs["spez_Investitionskosten_Abwärme"] = float(self.WHcostInput.text())
            inputs["spezifische_Investitionskosten_WP"] = float(self.WPWHcostInput.text())

        if self.tech_type == "Flusswasser":
            inputs['Wärmeleistung_FW_WP'] = float(self.PFWInput.text())
            try:
                if hasattr(self, 'csvData'):
                    inputs['Temperatur_FW_WP'] = self.csvData
                elif type(self.tech_data.get('Temperatur_FW_WP')) is float:
                    # Wenn der gespeicherte Wert ein Float ist, verwenden Sie ihn
                    inputs['Temperatur_FW_WP'] = float(self.TFWInput.text())
                elif isinstance(self.tech_data.get('Temperatur_FW_WP'), np.ndarray):
                    # Wenn der gespeicherte Wert ein NumPy-Array ist, verwenden Sie es
                    inputs['Temperatur_FW_WP'] = self.tech_data.get('Temperatur_FW_WP')
                else:
                    # Standardfall, wenn keine Daten vorhanden sind
                    inputs['Temperatur_FW_WP'] = float(self.TFWInput.text())
            except ValueError:
                print("Ungültige Eingabe")
                    
            inputs['dT'] = float(self.DTFWInput.text())
            inputs["spez_Investitionskosten_Flusswasser"] = float(self.RHcostInput.text())
            inputs["spezifische_Investitionskosten_WP"] = float(self.WPRHcostInput.text())

        return inputs