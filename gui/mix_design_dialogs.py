import numpy as np
import geopandas as gpd

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, \
    QDialogButtonBox, QComboBox, QTableWidget, QPushButton, QTableWidgetItem, \
    QHBoxLayout, QFileDialog, QMessageBox, QMenu, QInputDialog
from PyQt5.QtCore import Qt

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

            # volume solar heat storage
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
            'Gaspreis in €/MWh': float(self.gaspreisInput.text()),
            'Strompreis in €/MWh': float(self.strompreisInput.text()),
            'Holzpreis in €/MWh': float(self.holzpreisInput.text()),
            'BEW-Förderung': self.BEWComboBox.currentText(),
            'Kapitalzins in %': float(self.kapitalzinsInput.text()),
            'Preissteigerungsrate in %': float(self.preissteigerungsrateInput.text()),
            'Betrachtungszeitraum in a': int(self.betrachtungszeitraumInput.text()),
        }

class KostenBerechnungDialog(QDialog):
    def __init__(self, parent=None, label=None, value=None, type=None):
        super().__init__(parent)
        self.base_path = parent.base_path
        self.filename = f"{self.base_path}/Wärmenetz/dimensioniertes Wärmenetz.geojson"
        self.label = label
        self.value = value
        self.type = type
        self.total_cost = None
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        self.specCostLabel = QLabel(self.label)
        self.specCostInput = QLineEdit(self.value, self)
        self.layout.addWidget(self.specCostLabel)
        self.layout.addWidget(self.specCostInput)

        self.filenameLabel = QLabel("Datei Wärmenetz")
        self.filenameInput = QLineEdit(self.filename, self)
        self.layout.addWidget(self.filenameLabel)
        self.layout.addWidget(self.filenameInput)

        okButton = QPushButton("OK", self)
        cancelButton = QPushButton("Abbrechen", self)
        okButton.clicked.connect(self.onAccept)
        cancelButton.clicked.connect(self.reject)
        self.layout.addWidget(okButton)
        self.layout.addWidget(cancelButton)

    def onAccept(self):
        gdf_net = gpd.read_file(self.filename)
        gdf_net_filtered = gdf_net[gdf_net["name"]==self.type]

        if self.type == "flow line":
            self.length_values = gdf_net_filtered["length_m"].values.astype(float)
            self.cost_lines = self.length_values * float(self.specCostInput.text())
            self.total_cost = round(np.sum(self.cost_lines),0)

        if self.type == "HAST":
            self.qext_values = gdf_net_filtered["qext_W"].values.astype(float)/1000
            self.cost_lines = self.qext_values * float(self.specCostInput.text())
            self.total_cost = round(np.sum(self.cost_lines),0)

        self.accept()

class NetInfrastructureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_path = parent.base_path
        self.initUI()
        self.initDefaultValues()
         # Kontextmenü für vertikale Kopfzeilen
        self.table.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.verticalHeader().customContextMenuRequested.connect(self.openHeaderContextMenu)

    def initUI(self):
        self.layout = QVBoxLayout(self)

        # Erstellen der Tabelle
        self.table = QTableWidget(self)
        self.infraObjects = ['waermenetz', 'hausanschlussstationen', 'druckhaltung', 'hydraulik', 'elektroinstallation', 'planungskosten']
        self.table.setRowCount(len(self.infraObjects))
        self.table.setColumnCount(5)  # Für jede Eigenschaft eine Spalte
        self.table.setHorizontalHeaderLabels(['kosten', 'technische nutzungsdauer', 'f_inst', 'f_w_insp', 'bedienaufwand'])
        self.table.setVerticalHeaderLabels(self.infraObjects)
        self.layout.addWidget(self.table)

        # Button für die Kostenberechnung des Wärmenetzes hinzufügen
        self.berechneWärmenetzKostenButton = QPushButton("Kosten Wärmenetz aus geoJSON berechnen", self)
        self.berechneWärmenetzKostenButton.clicked.connect(self.berechneWaermenetzKosten)
        self.layout.addWidget(self.berechneWärmenetzKostenButton)

        # Button für die Kostenberechnung der Hausanschlussstationen hinzufügen
        self.berechneHausanschlussKostenButton = QPushButton("Kosten Hausanschlusstationen aus geoJSON berechnen", self)
        self.berechneHausanschlussKostenButton.clicked.connect(self.berechneHausanschlussKosten)
        self.layout.addWidget(self.berechneHausanschlussKostenButton)

        # Button-Leiste
        buttonLayout = QHBoxLayout()
        # Hinzufügen und Entfernen von Schaltflächen
        self.addButton = QPushButton("Zeile hinzufügen", self)
        self.removeButton = QPushButton("Zeile entfernen", self)
        self.addButton.clicked.connect(self.addRow)
        self.removeButton.clicked.connect(self.removeRow)
        buttonLayout.addWidget(self.addButton)
        buttonLayout.addWidget(self.removeButton)

        okButton = QPushButton("OK", self)
        cancelButton = QPushButton("Abbrechen", self)
        okButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)
        self.layout.addLayout(buttonLayout)

    def renameHeader(self, row):
        newName, okPressed = QInputDialog.getText(self, "Name ändern", "Neuer Name:", QLineEdit.Normal, "")
        if okPressed and newName != '':
            self.table.verticalHeaderItem(row).setText(newName)
            self.infraObjects[row] = newName

    def openHeaderContextMenu(self, position):
        menu = QMenu()

        renameAction = menu.addAction("Umbenennen")
        action = menu.exec_(self.table.verticalHeader().mapToGlobal(position))

        if action == renameAction:
            row = self.table.verticalHeader().logicalIndexAt(position)
            if row != -1:
                self.renameHeader(row)

    def addRow(self):
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        new_row_name = f"Neues Objekt"
        self.table.setVerticalHeaderItem(row_count, QTableWidgetItem(new_row_name))
        self.infraObjects.append(new_row_name)

    def removeRow(self):
        current_row = self.table.currentRow()
        if current_row != -1:
            # Entfernen Sie das Element aus der infraObjects-Liste
            del self.infraObjects[current_row]
            self.table.removeRow(current_row)

    def initDefaultValues(self):
        # Standardwerte wie zuvor definiert
        defaultValues = {
            'waermenetz': {
                'kosten': "2000000",
                'technische nutzungsdauer': "40",
                'f_inst': "1",
                'f_w_insp': "0",
                'bedienaufwand': "5"
            },
            'hausanschlussstationen': {
                'kosten': "100000",
                'technische nutzungsdauer': "20",
                'f_inst': "1",
                'f_w_insp': "1",
                'bedienaufwand': "2"
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

        for i, obj in enumerate(self.infraObjects):
            for j, field in enumerate(['kosten', 'technische nutzungsdauer', 'f_inst', 'f_w_insp', 'bedienaufwand']):
                self.table.setItem(i, j, QTableWidgetItem(str(defaultValues[obj][field])))

    def updateTableValue(self, row, column, value):
        """
        Aktualisiert den Wert in der Tabelle.

        :param row: Zeilenindex der Tabelle, beginnend bei 0.
        :param column: Spaltenindex der Tabelle, beginnend bei 0.
        :param value: Der neue Wert, der in die Zelle eingetragen werden soll.
        """
        # Überprüfung, ob der angegebene Zeilen- und Spaltenindex gültig ist
        if 0 <= row < self.table.rowCount() and 0 <= column < self.table.columnCount():
            self.table.setItem(row, column, QTableWidgetItem(str(value)))
        else:
            print("Fehler: Ungültiger Zeilen- oder Spaltenindex.")

    def berechneWaermenetzKosten(self):
        dialog = KostenBerechnungDialog(self, label="spez. Kosten Wärmenetz pro m_Trasse (inkl. Tiefbau) in €/m", value="1000", type="flow line")
        dialog.setWindowTitle("Kosten Wärmenetz berechnen")
        if dialog.exec_():
            cost_net = dialog.total_cost
            self.updateTableValue(row=0, column=0, value=cost_net)

    def berechneHausanschlussKosten(self):
        dialog = KostenBerechnungDialog(self, label="spez. Kosten Hausanschlussstationen pro kW max. Wärmebedarf in €/kW", value="250", type="HAST")
        dialog.setWindowTitle("Kosten Hausanschlussstationen berechnen")
        if dialog.exec_():
            cost_net = dialog.total_cost
            self.updateTableValue(row=1, column=0, value=cost_net)

    def getCurrentInfraObjects(self):
        return self.infraObjects
    
    def getValues(self):
        values = {}
        for i, obj in enumerate(self.infraObjects):
            for j, field in enumerate(['kosten', 'technische nutzungsdauer', 'f_inst', 'f_w_insp', 'bedienaufwand']):
                key = f"{obj}_{field}"
                item = self.table.item(i, j)
                # Überprüfen Sie, ob das Element vorhanden ist
                if item is not None:
                    values[key] = float(item.text())
                else:
                    # Standardwert oder eine geeignete Behandlung, wenn das Element nicht vorhanden ist
                    values[key] = 0.0  # oder ein anderer angemessener Standardwert
        return values
    

class TemperatureDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.initDefaultValues()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        self.temperatureDataFileLabel = QLabel("TRY-Datei:", self)
        self.temperatureDataFileInput = QLineEdit(self)
        self.selectTRYFileButton = QPushButton('csv-Datei auswählen')
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

    def initDefaultValues(self):
        self.temperatureDataFileInput.setText("heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat")

    def getValues(self):
        return {
            'TRY-filename': self.temperatureDataFileInput.text()
        }
    
class HeatPumpDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wärmepumpendaten")
        self.initUI()
        self.initDefaultValues()

    def initUI(self):
        # Hauptlayout
        mainLayout = QVBoxLayout(self)

        # Datenfelder und Label
        dataLayout = QVBoxLayout()
        self.heatPumpDataFileLabel = QLabel("csv-Datei mit Wärmepumpenkennfeld:")
        self.heatPumpDataFileInput = QLineEdit()
        self.heatPumpDataFileInput.setPlaceholderText("heat_generators/Kennlinien WP.csv")
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

    def initDefaultValues(self):
        # Standardwert, könnte durch Benutzerinteraktion überschrieben werden
        self.heatPumpDataFileInput.setText("heat_generators/Kennlinien WP.csv")

    def getValues(self):
        # Zurückgeben der Werte zur weiteren Verarbeitung
        return {
            'COP-filename': self.heatPumpDataFileInput.text()
        }