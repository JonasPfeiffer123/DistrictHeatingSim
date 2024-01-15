from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, \
    QDialogButtonBox, QComboBox, QTableWidget, QPushButton, QTableWidgetItem, \
    QFormLayout, QHBoxLayout, QFileDialog, QProgressBar, QMessageBox

import pandas as pd
import numpy as np

from osm_data.import_osm_data_geojson import build_query, download_data, save_to_file
from gui.threads import GeocodingThread

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

        if self.tech_type == "Biomassekessel":
            self.PBMKInput = QLineEdit(self)
            self.PBMKInput.setText(str(self.tech_data.get('P_BMK', "50")))
            layout.addWidget(QLabel("thermische Leistung"))
            layout.addWidget(self.PBMKInput)

        if self.tech_type == "Gaskessel":
            layout.addWidget(QLabel("aktuell keine Dimensionierungseingaben, Leistung wird anhand der Gesamtlast berechnet"))

        if self.tech_type == "BHKW":
            self.PBHKWInput = QLineEdit(self)
            self.PBHKWInput.setText(str(self.tech_data.get('th_Leistung_BHKW', "40")))
            layout.addWidget(QLabel("thermische Leistung"))
            layout.addWidget(self.PBHKWInput)

        if self.tech_type == "Holzgas-BHKW":
            self.PHBHKWInput = QLineEdit(self)
            self.PHBHKWInput.setText(str(self.tech_data.get('th_Leistung_BHKW', "30")))
            layout.addWidget(QLabel("thermische Leistung"))
            layout.addWidget(self.PHBHKWInput)

        if self.tech_type == "Geothermie":
            self.areaGInput = QLineEdit(self)
            self.areaGInput.setText(str(self.tech_data.get('Fläche', "100")))
            self.depthInput = QLineEdit(self)
            self.depthInput.setText(str(self.tech_data.get('Bohrtiefe', "100")))
            self.tempGInput = QLineEdit(self)
            self.tempGInput.setText(str(self.tech_data.get('Temperatur_Geothermie', "10")))

            layout.addWidget(QLabel("Fläche Erdsondenfeld in m²"))
            layout.addWidget(self.areaGInput)
            layout.addWidget(QLabel("Bohrtiefe Sonden in m³"))
            layout.addWidget(self.depthInput)
            layout.addWidget(QLabel("Quelltemperatur"))
            layout.addWidget(self.tempGInput)
        
        if self.tech_type == "Abwärme":
            self.PWHInput = QLineEdit(self)
            self.PWHInput.setText(str(self.tech_data.get('Kühlleistung_Abwärme', "30")))
            layout.addWidget(QLabel("Kühlleistung Abwärme"))
            layout.addWidget(self.PWHInput)

            self.TWHInput = QLineEdit(self)
            self.TWHInput.setText(str(self.tech_data.get('Temperatur_Abwärme', "30")))
            layout.addWidget(QLabel("Temperatur Abwärme"))
            layout.addWidget(self.TWHInput)

        if self.tech_type == "Flusswasser":
            self.PFWInput = QLineEdit(self)
            self.PFWInput.setText(str(self.tech_data.get('Wärmeleistung_FW_WP', "200")))
            layout.addWidget(QLabel("Wärmeleistung Wärmepumpe"))
            layout.addWidget(self.PFWInput)

            # Flusstemperatur direkt eingeben
            self.TFWInput = QLineEdit(self)
            if type(self.tech_data.get('Temperatur_FW_WP')) is float or self.tech_data == {}:
                self.TFWInput.setText(str(self.tech_data.get('Temperatur_FW_WP', "10")))
            layout.addWidget(QLabel("Flusstemperatur"))
            layout.addWidget(self.TFWInput)

            # Button zum Auswählen der CSV-Datei
            self.csvButton = QPushButton("CSV für Flusstemperatur wählen", self)
            self.csvButton.clicked.connect(self.openCSV)
            layout.addWidget(self.csvButton)

            self.DTFWInput = QLineEdit(self)
            self.DTFWInput.setText(str(self.tech_data.get('dT', "0")))
            layout.addWidget(QLabel("Zulässige Abweichung Vorlauftemperatur Wärmepumpe von Netzvorlauftemperatur"))
            layout.addWidget(self.DTFWInput)

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
        elif self.tech_type == "Biomassekessel":
            inputs["P_BMK"] = float(self.PBMKInput.text())
        elif self.tech_type == "Gaskessel":
            pass
        elif self.tech_type == "BHKW":
            inputs["th_Leistung_BHKW"] = float(self.PBHKWInput.text())
        elif self.tech_type == "Holzgas-BHKW":
            inputs["th_Leistung_BHKW"] = float(self.PHBHKWInput.text())
        elif self.tech_type == "Geothermie":
            inputs["Fläche"] = float(self.areaGInput.text())
            inputs["Bohrtiefe"] = float(self.depthInput.text())
            inputs["Temperatur_Geothermie"] = float(self.tempGInput.text())
        elif self.tech_type == "Abwärme":
            inputs["Kühlleistung_Abwärme"] = float(self.PWHInput.text())
            inputs["Temperatur_Abwärme"] = float(self.TWHInput.text())
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

        return inputs
        
class HeatDemandEditDialog(QDialog):
    def __init__(self, gdf_HAST, hastInput, parent=None):
        super(HeatDemandEditDialog, self).__init__(parent)
        self.gdf_HAST = gdf_HAST
        self.hastInput = hastInput
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        # Erstelle eine Tabelle für die Bearbeitung
        self.heatDemandTable = QTableWidget(self)
        self.loadHeatDemandData()
        self.layout.addWidget(self.heatDemandTable)

        # Speicher-Button
        saveButton = QPushButton("Änderungen speichern", self)
        saveButton.clicked.connect(self.saveHeatDemandData)
        self.layout.addWidget(saveButton)

    def loadHeatDemandData(self):
        df = pd.DataFrame(self.gdf_HAST.drop(columns=[self.gdf_HAST.geometry.name]))
        self.heatDemandTable.setRowCount(len(df))
        self.heatDemandTable.setColumnCount(len(df.columns))
        self.heatDemandTable.setHorizontalHeaderLabels(df.columns)

        for i, row in df.iterrows():
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                self.heatDemandTable.setItem(i, j, item)

    def saveHeatDemandData(self):
        for i in range(self.heatDemandTable.rowCount()):
            for j, column_name in enumerate(self.gdf_HAST.drop(columns=[self.gdf_HAST.geometry.name]).columns):
                cell_value = self.heatDemandTable.item(i, j).text()
                self.gdf_HAST.at[i, column_name] = cell_value

        self.gdf_HAST.to_file(self.hastInput, driver='GeoJSON')
        self.accept()  # Schließt das Dialogfenster

class LayerGenerationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Layer-Generierung")

        layout = QVBoxLayout(self)

        # Formularlayout für Eingaben
        formLayout = QFormLayout()

        # Dateiauswahl für Street Layer und Data CSV
        self.streetLayerInput, self.streetLayerButton = self.createFileInput("net_generation_QGIS/Straßen Zittau.geojson")
        self.dataCsvInput, self.dataCsvButton = self.createFileInput("geocoding/data_output_zi_ETRS89.csv")

        # Koordinateneingaben
        self.xCoordInput = QLineEdit("486267.306999999971595", self)
        self.yCoordInput = QLineEdit("5637294.910000000149012", self)

        formLayout.addRow("GeoJSON-Straßen-Layer:", self.createFileInputLayout(self.streetLayerInput, self.streetLayerButton))
        formLayout.addRow("CSV mit Gebäudestandorten:", self.createFileInputLayout(self.dataCsvInput, self.dataCsvButton))
        formLayout.addRow("X-Koordinate Erzeugerstandort:", self.xCoordInput)
        formLayout.addRow("Y-Koordinate Erzeugerstandort:", self.yCoordInput)

        # Buttons für OK und Abbrechen
        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.clicked.connect(self.reject)

        layout.addLayout(formLayout)
        layout.addWidget(self.okButton)
        layout.addWidget(self.cancelButton)

    def createFileInput(self, default_path):
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, lineEdit, button):
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def selectFile(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def getInputs(self):
        return {
            "streetLayer": self.streetLayerInput.text(),
            "dataCsv": self.dataCsvInput.text(),
            "xCoord": self.xCoordInput.text(),
            "yCoord": self.yCoordInput.text()
        }
    
class DownloadOSMDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags_to_download = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Download OSM-Data")

        layout = QVBoxLayout(self)

        # Stadtname Eingabefeld
        self.cityLineEdit, cityButton = self.createCityInput("Zittau")
        layout.addLayout(self.createFileInputLayout(self.cityLineEdit, cityButton))
        
        # Dateiname Eingabefeld
        self.filenameLineEdit, fileButton = self.createFileInput("osm_data/osm_data.geojson")
        layout.addLayout(self.createFileInputLayout(self.filenameLineEdit, fileButton))

        # Tags-Auswahl
        self.tagsLayout = QFormLayout()
        layout.addLayout(self.tagsLayout)
        self.addTagField()  # Erstes Tag-Feld hinzufügen
        
        # Buttons zum Hinzufügen/Entfernen von Tags
        self.addTagButton = QPushButton("Tag hinzufügen", self)
        self.addTagButton.clicked.connect(self.addTagField)
        self.removeTagButton = QPushButton("Tag entfernen", self)
        self.removeTagButton.clicked.connect(self.removeTagField)
        layout.addWidget(self.addTagButton)
        layout.addWidget(self.removeTagButton)
        
        # Buttons für OK und Abbrechen
        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.onAccept)
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.clicked.connect(self.reject)
        
        layout.addWidget(self.okButton)
        layout.addWidget(self.cancelButton)

    def createFileInput(self, default_path):
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, lineEdit, button):
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def selectFile(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)
    
    def createCityInput(self, placeholder_text):
        lineEdit = QLineEdit(placeholder_text)
        button = QPushButton("Stadt bestätigen")
        button.clicked.connect(lambda: self.setCityName(lineEdit))
        return lineEdit, button

    def setCityName(self, lineEdit):
        self.city_name = lineEdit.text()
    
    def addTagField(self):
        keyLineEdit = QLineEdit()
        valueLineEdit = QLineEdit()
        self.tagsLayout.addRow(keyLineEdit, valueLineEdit)
        self.tags_to_download.append((keyLineEdit, valueLineEdit))
    
    def removeTagField(self):
        if self.tags_to_download:
            keyLineEdit, valueLineEdit = self.tags_to_download.pop()
            self.tagsLayout.removeRow(keyLineEdit)
    
    def onAccept(self):
        # Daten sammeln
        self.filename = self.filenameLineEdit.text()
        tags = {key.text(): value.text() for key, value in self.tags_to_download if key.text()}
        
        # Abfrage erstellen und Daten herunterladen
        self.downloadOSMData(self.city_name, tags, self.filename)
        self.accept()

    # Die Methode des Dialogs, die die anderen Funktionen aufruft
    def downloadOSMData(self, city_name, tags, filename):
        # Erstelle die Overpass-Abfrage
        query = build_query(city_name, tags)
        # Lade die Daten herunter
        geojson_data = download_data(query)
        # Speichere die Daten als GeoJSON
        save_to_file(geojson_data, filename)

class GeocodeAdressesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Adressdaten geocodieren")

        layout = QVBoxLayout(self)

        # Stadtname Eingabefeld
        self.inputfilenameLineEdit, fileButton = self.createFileInput("geocoding/data_input_zi.csv")
        layout.addLayout(self.createFileInputLayout(self.inputfilenameLineEdit, fileButton))
        
        # Dateiname Eingabefeld
        self.outputfilenameLineEdit, fileButton = self.createFileInput("geocoding/data_output_zi_ETRS89.csv")
        layout.addLayout(self.createFileInputLayout(self.outputfilenameLineEdit, fileButton))
        
        # Buttons für OK und Abbrechen
        self.okButton = QPushButton("OK", self)
        self.okButton.clicked.connect(self.onAccept)
        self.cancelButton = QPushButton("Abbrechen", self)
        self.cancelButton.clicked.connect(self.reject)
        
        layout.addWidget(self.okButton)
        layout.addWidget(self.cancelButton)

        self.progressBar = QProgressBar(self)
        layout.addWidget(self.progressBar)

    def createFileInput(self, default_path):
        lineEdit = QLineEdit(default_path)
        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, lineEdit, button):
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def selectFile(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def onAccept(self):
        # Daten sammeln
        self.inputfilename = self.inputfilenameLineEdit.text()
        self.outputfilename = self.outputfilenameLineEdit.text()
        
        # Abfrage erstellen und Daten herunterladen
        self.geocodeAdresses(self.inputfilename, self.outputfilename)

    # Die Methode des Dialogs, die die anderen Funktionen aufruft
    def geocodeAdresses(self, inputfilename, outputfilename):
        # Stellen Sie sicher, dass der vorherige Thread beendet wird
        if hasattr(self, 'geocodingThread') and self.geocodingThread.isRunning():
            self.geocodingThread.terminate()
            self.geocodingThread.wait()
        self.geocodingThread = GeocodingThread(inputfilename, outputfilename)
        self.geocodingThread.calculation_done.connect(self.on_generation_done)
        self.geocodingThread.calculation_error.connect(self.on_generation_error)
        self.geocodingThread.start()
        self.progressBar.setRange(0, 0)  # Aktiviert den indeterministischen Modus

    def on_generation_done(self, results):
        self.accept()

    def on_generation_error(self, error_message):
        QMessageBox.critical(self, "Fehler beim Geocoding", error_message)
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus

class GeojsonDialog(QDialog):
    def __init__(self, generate_callback, edit_hast_callback, import_layers_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Netz aus GeoJSON generieren")
        self.generate_callback = generate_callback
        self.edit_hast_callback = edit_hast_callback
        self.import_layers_callback = import_layers_callback
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Standardpfade
        default_paths = {
            'Erzeugeranlagen': 'net_generation/Erzeugeranlagen.geojson',
            'HAST': 'net_generation/HAST.geojson',
            'Vorlauf': 'net_generation/Vorlauf.geojson',
            'Rücklauf': 'net_generation/Rücklauf.geojson'
        }

        # Eingabefelder und Dateiauswahl-Buttons
        self.vorlaufInput = self.createFileInput("Vorlauf GeoJSON:", default_paths['Vorlauf'])
        self.ruecklaufInput = self.createFileInput("Rücklauf GeoJSON:", default_paths['Rücklauf'])
        self.hastInput = self.createFileInput("HAST GeoJSON:", default_paths['HAST'])
        self.erzeugeranlagenInput = self.createFileInput("Erzeugeranlagen GeoJSON:", default_paths['Erzeugeranlagen'])

        layout.addLayout(self.vorlaufInput)
        layout.addLayout(self.ruecklaufInput)
        layout.addLayout(self.hastInput)
        layout.addLayout(self.erzeugeranlagenInput)

        # Hinzufügen der Berechnungsmethoden-Auswahl
        self.calcMethodInput = QComboBox(self)
        self.calcMethodInput.addItems(["Datensatz", "BDEW", "VDI4655"])
        layout.addWidget(QLabel("Berechnungsmethode:"))
        layout.addWidget(self.calcMethodInput)

        # Hinzufügen der Gebäudetypen-Auswahl
        self.buildingTypeInput = QComboBox(self)
        layout.addWidget(QLabel("Gebäudetyp:"))
        layout.addWidget(self.buildingTypeInput)
        self.updateBuildingType()  # Initialisiert die Gebäudetypen basierend auf der Berechnungsmethode

        self.calcMethodInput.currentIndexChanged.connect(self.updateBuildingType)

        # Button für "Hausanschlussstationen bearbeiten"
        self.editHASTButton = QPushButton("Hausanschlussstationen bearbeiten", self)
        self.editHASTButton.clicked.connect(self.editHAST)
        layout.addWidget(self.editHASTButton)

        # Button für "Layers in Karte importieren"
        self.importLayersButton = QPushButton("Layers in Karte importieren", self)
        self.importLayersButton.clicked.connect(self.importLayers)
        layout.addWidget(self.importLayersButton)

        # Button zum Starten der Netzgenerierung
        self.generateButton = QPushButton("Netz generieren", self)
        self.generateButton.clicked.connect(self.generateNetwork)
        layout.addWidget(self.generateButton)

    def createFileInput(self, label_text, default_text):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        line_edit = QLineEdit(default_text)
        button = QPushButton("Datei auswählen")
        button.clicked.connect(lambda: self.selectFilename(line_edit))
        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return layout

    def selectFilename(self, line_edit):
        fname, _ = QFileDialog.getOpenFileName(self, 'Datei auswählen', '', 'GeoJSON Files (*.geojson);;All Files (*)')
        if fname:
            line_edit.setText(fname)

    def updateBuildingType(self):
        self.buildingTypeInput.clear()
        if self.calcMethodInput.currentText() == "VDI4655":
            self.buildingTypeInput.setDisabled(False)
            self.buildingTypeInput.addItems(["EFH", "MFH"])
        elif self.calcMethodInput.currentText() == "BDEW":
            self.buildingTypeInput.setDisabled(False)
            self.buildingTypeInput.addItems(["HEF", "HMF", "GKO", "GHA", "GMK", "GBD", "GBH", "GWA", "GGA", "GBA", "GGB", "GPD", "GMF", "GHD"])
        else:
            self.buildingTypeInput.setDisabled(True)

    def editHAST(self):
        hast_path = self.hastInput.itemAt(1).widget().text()  # Annahme: QLineEdit ist das zweite Widget im Layout
        if self.edit_hast_callback:
            self.edit_hast_callback(hast_path)

    def importLayers(self):
        if self.import_layers_callback:
            self.import_layers_callback(
                self.vorlaufInput.itemAt(1).widget().text(),
                self.ruecklaufInput.itemAt(1).widget().text(),
                self.hastInput.itemAt(1).widget().text(),
                self.erzeugeranlagenInput.itemAt(1).widget().text()
            )

    def generateNetwork(self):
        if self.generate_callback:
            self.generate_callback(
                self.vorlaufInput.itemAt(1).widget().text(),
                self.ruecklaufInput.itemAt(1).widget().text(),
                self.hastInput.itemAt(1).widget().text(),
                self.erzeugeranlagenInput.itemAt(1).widget().text(),
                self.calcMethodInput.currentText(),
                self.buildingTypeInput.currentText() if self.calcMethodInput.currentText() != "Datensatz" else None
            )
        self.accept()

class StanetDialog(QDialog):
    def __init__(self, generate_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Netz aus Stanet-CSV generieren")
        self.generate_callback = generate_callback
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Standardpfad
        default_path = "net_simulation_pandapipes/stanet files/Beleg_1/Beleg_1.CSV"

        # Eingabefeld und Dateiauswahl-Button
        self.stanetCsvInputLayout = self.createFileInput("Stanet CSV:", default_path)
        layout.addLayout(self.stanetCsvInputLayout)

        # Button zum Starten der Netzgenerierung
        self.generateButton = QPushButton("Netz generieren", self)
        self.generateButton.clicked.connect(self.generateNetwork)
        layout.addWidget(self.generateButton)

    def createFileInput(self, label_text, default_text):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        line_edit = QLineEdit(default_text)
        button = QPushButton("Datei auswählen")
        button.clicked.connect(lambda: self.selectFilename(line_edit))
        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return layout

    def selectFilename(self, line_edit):
        fname, _ = QFileDialog.getOpenFileName(self, 'Datei auswählen', '', 'CSV Files (*.csv);;All Files (*)')
        if fname:
            line_edit.setText(fname)

    def generateNetwork(self):
        if self.generate_callback:
            self.generate_callback(self.stanetCsvInputLayout.itemAt(1).widget().text())
        self.accept()

class EconomicParametersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.initDefaultValues()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        self.gaspreisLabel = QLabel("Gaspreis (€/MWh):", self)
        self.gaspreisInput = QLineEdit(self)
        self.layout.addWidget(self.gaspreisLabel)
        self.layout.addWidget(self.gaspreisInput)

        self.strompreisLabel = QLabel("Strompreis (€/MWh):", self)
        self.strompreisInput = QLineEdit(self)
        self.layout.addWidget(self.strompreisLabel)
        self.layout.addWidget(self.strompreisInput)

        self.holzpreisLabel = QLabel("Holzpreis (€/MWh):", self)
        self.holzpreisInput = QLineEdit(self)
        self.layout.addWidget(self.holzpreisLabel)
        self.layout.addWidget(self.holzpreisInput)

        self.BEWLabel = QLabel("Berücksichtigung BEW-Förderung?:", self)
        self.BEWComboBox = QComboBox(self)
        self.BEWComboBox.addItems(["Nein", "Ja"])
        self.layout.addWidget(self.BEWLabel)
        self.layout.addWidget(self.BEWComboBox)

        self.kapitalzinsLabel = QLabel("Kapitalzins (%):", self)
        self.kapitalzinsInput = QLineEdit(self)
        self.layout.addWidget(self.kapitalzinsLabel)
        self.layout.addWidget(self.kapitalzinsInput)

        self.preissteigerungsrateLabel = QLabel("Preissteigerungsrate (%):", self)
        self.preissteigerungsrateInput = QLineEdit(self)
        self.layout.addWidget(self.preissteigerungsrateLabel)
        self.layout.addWidget(self.preissteigerungsrateInput)

        self.betrachtungszeitraumLabel = QLabel("Betrachtungszeitraum (Jahre):", self)
        self.betrachtungszeitraumInput = QLineEdit(self)
        self.layout.addWidget(self.betrachtungszeitraumLabel)
        self.layout.addWidget(self.betrachtungszeitraumInput)

        self.setLayout(self.layout)

        buttonLayout = QHBoxLayout()
        okButton = QPushButton("OK", self)
        cancelButton = QPushButton("Abbrechen", self)
        
        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)

        self.layout.addLayout(buttonLayout)

    def initDefaultValues(self):
        self.gaspreisInput.setText("70")
        self.strompreisInput.setText("150")
        self.holzpreisInput.setText("50")
        self.BEWComboBox.setCurrentIndex(0)  # Setzt die Auswahl auf "Nein"
        self.kapitalzinsInput.setText("5")
        self.preissteigerungsrateInput.setText("3")
        self.betrachtungszeitraumInput.setText("20")

    def getValues(self):
        return {
            'gaspreis': float(self.gaspreisInput.text()),
            'strompreis': float(self.strompreisInput.text()),
            'holzpreis': float(self.holzpreisInput.text()),
            'BEW': self.BEWComboBox.currentText(),
            'kapitalzins': float(self.kapitalzinsInput.text()),
            'preissteigerungsrate': float(self.preissteigerungsrateInput.text()),
            'betrachtungszeitraum': int(self.betrachtungszeitraumInput.text()),
        }
    
class NetInfrastructureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.initDefaultValues()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        # Liste von Infrastruktur-Objekten
        self.infraObjects = ['waermenetz', 'druckhaltung', 'hydraulik', 'elektroinstallation', 'planungskosten']
        self.inputs = {}  # Speichert die Eingabefelder für jedes Objekt

        for obj in self.infraObjects:
            self.initInfraObjectGroup(obj)

        # Button-Leiste
        buttonLayout = QHBoxLayout()
        okButton = QPushButton("OK", self)
        cancelButton = QPushButton("Abbrechen", self)
        
        # Verbinden der Buttons mit ihren Funktionen
        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)

        self.layout.addLayout(buttonLayout)

    def initInfraObjectGroup(self, obj_name):
        # Erstellen einer Untergruppe von Feldern für jedes Infrastruktur-Objekt
        groupLayout = QVBoxLayout()
        nameLabel = QLabel(f"{obj_name.capitalize()}:", self)
        groupLayout.addWidget(nameLabel)

        # Zusätzliche Felder
        for field in ['kosten','technische nutzungsdauer', 'f_inst', 'f_w_insp', 'bedienaufwand']:
            label = QLabel(f"{field} für {obj_name}:", self)
            inputField = QLineEdit(self)
            groupLayout.addWidget(label)
            groupLayout.addWidget(inputField)
            # Speichern der Eingabefelder im Dictionary
            self.inputs[f"{obj_name}_{field}"] = inputField

        # Fügen Sie die Gruppe zum Hauptlayout hinzu
        self.layout.addLayout(groupLayout)

    def initDefaultValues(self):
        # Standardwerte für jedes Infrastruktur-Objekt
        defaultValues = {
            'waermenetz': {
                'kosten': "2000000",
                'technische nutzungsdauer': "40",
                'f_inst': "1",
                'f_w_insp': "0",
                'bedienaufwand': "5"
            },
            'druckhaltung': {
                'kosten': "20000",
                'technische nutzungsdauer': "20",
                'f_inst': "1",
                'f_w_insp': "1",
                'bedienaufwand': "2"
            },
            'hydraulik': {
                'kosten': "40000",
                'technische nutzungsdauer': "40",
                'f_inst': "1",
                'f_w_insp': "0",
                'bedienaufwand': "0"
            },
            'elektroinstallation': {
                'kosten': "15000",
                'technische nutzungsdauer': "15",
                'f_inst': "1",
                'f_w_insp': "1",
                'bedienaufwand': "5"
            },
            'planungskosten': {
                'kosten': "500000",
                'technische nutzungsdauer': "20",
                'f_inst': "0",
                'f_w_insp': "0",
                'bedienaufwand': "0"
            }
        }

        for obj in self.infraObjects:
            for field in ['kosten', 'technische nutzungsdauer', 'f_inst', 'f_w_insp', 'bedienaufwand']:
                key = f"{obj}_{field}"
                if key in self.inputs: # Überprüfen, ob der Schlüssel existiert
                    self.inputs[key].setText(defaultValues[obj][field])

    def getValues(self):
        # Extrahiere die Werte aus allen Eingabefeldern
        values = {}
        for key, inputField in self.inputs.items():
            values[key] = float(inputField.text())
        return values