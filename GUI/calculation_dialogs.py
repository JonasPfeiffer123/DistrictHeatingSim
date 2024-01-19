from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, QComboBox, \
    QTableWidget, QPushButton, QTableWidgetItem, QHBoxLayout, QFileDialog
import pandas as pd


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

        # Hinzufügen zusätzlicher Eingabefelder für die neuen Parameter
        self.supplyTemperatureInput = QLineEdit("85")
        layout.addWidget(QLabel("Vorlauftemperatur:"))
        layout.addWidget(self.supplyTemperatureInput)

        self.returnTemperatureInput = QLineEdit("60")
        layout.addWidget(QLabel("Rücklauftemperatur:"))
        layout.addWidget(self.returnTemperatureInput)

        self.flowPressureInput = QLineEdit("4")
        layout.addWidget(QLabel("Vorlaufdruck:"))
        layout.addWidget(self.flowPressureInput)
        
        self.liftPressureInput = QLineEdit("1.5")
        layout.addWidget(QLabel("Druckdifferenz Vorlauf/Rücklauf:"))
        layout.addWidget(self.liftPressureInput)

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
                self.buildingTypeInput.currentText() if self.calcMethodInput.currentText() != "Datensatz" else None,
                float(self.returnTemperatureInput.text()),
                float(self.supplyTemperatureInput.text()),
                float(self.flowPressureInput.text()),
                float(self.liftPressureInput.text())
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