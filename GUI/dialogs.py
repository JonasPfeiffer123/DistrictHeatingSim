from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, \
    QDialogButtonBox, QComboBox, QTableWidget, QPushButton, QTableWidgetItem

import pandas as pd

class TechInputDialog(QDialog):
    def __init__(self, tech_type):
        super().__init__()

        self.tech_type = tech_type
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f"Eingabe für {self.tech_type}")
        layout = QVBoxLayout()

        # Erstellen Sie hier Eingabefelder basierend auf self.tech_type
        # Beispiel für Solarthermie:
        if self.tech_type == "Solarthermie":
            # area solar
            self.areaSInput = QLineEdit(self)
            self.areaSInput.setText("200")
            layout.addWidget(QLabel("Kollektorbruttofläche in m²"))
            layout.addWidget(self.areaSInput)

            # volume solar heat storage
            self.vsInput = QLineEdit(self)
            self.vsInput.setText("20")
            layout.addWidget(QLabel("Solarspeichervolumen in m³"))
            layout.addWidget(self.vsInput)

            # type
            self.typeInput = QComboBox(self)
            self.techOptions = ["Vakuumröhrenkollektor", "Flachkollektor"]
            self.typeInput.addItems(self.techOptions)
            layout.addWidget(QLabel("Kollektortyp"))
            layout.addWidget(self.typeInput)

        if self.tech_type == "Biomassekessel":
            self.PBMKInput = QLineEdit(self)
            self.PBMKInput.setText("50")
            layout.addWidget(QLabel("thermische Leistung"))
            layout.addWidget(self.PBMKInput)

        if self.tech_type == "Gaskessel":
            layout.addWidget(QLabel("aktuell keine Dimensionierungseingaben, Leistung wird anhand der Gesamtlast berechnet"))

        if self.tech_type == "BHKW":
            self.PBHKWInput = QLineEdit(self)
            self.PBHKWInput.setText("40")
            layout.addWidget(QLabel("thermische Leistung"))
            layout.addWidget(self.PBHKWInput)

        if self.tech_type == "Holzgas-BHKW":
            self.PHBHKWInput = QLineEdit(self)
            self.PHBHKWInput.setText("30")
            layout.addWidget(QLabel("thermische Leistung"))
            layout.addWidget(self.PHBHKWInput)

        if self.tech_type == "Geothermie":
            self.areaGInput = QLineEdit(self)
            self.areaGInput.setText("100")
            self.depthInput = QLineEdit(self)
            self.depthInput.setText("100")
            self.tempGInput = QLineEdit(self)
            self.tempGInput.setText("10")

            layout.addWidget(QLabel("Fläche Erdsondenfeld in m²"))
            layout.addWidget(self.areaGInput)
            layout.addWidget(QLabel("Bohrtiefe Sonden in m³"))
            layout.addWidget(self.depthInput)
            layout.addWidget(QLabel("Quelltemperatur"))
            layout.addWidget(self.tempGInput)
        
        if self.tech_type == "Abwärme":
            self.PWHInput = QLineEdit(self)
            self.PWHInput.setText("30")
            layout.addWidget(QLabel("Kühlleistung Abwärme"))
            layout.addWidget(self.PWHInput)

            self.TWHInput = QLineEdit(self)
            self.TWHInput.setText("30")
            layout.addWidget(QLabel("Temperatur Abwärme"))
            layout.addWidget(self.TWHInput)

        # OK und Abbrechen Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def getInputs(self):
        if self.tech_type == "Solarthermie":
            return {
                "bruttofläche_STA": float(self.areaSInput.text()),
                "vs": float(self.vsInput.text()),
                "Typ": self.typeInput.itemText(self.typeInput.currentIndex())
            }
        elif self.tech_type == "Biomassekessel":
            return {
                "P_BMK": float(self.PBMKInput.text())
            }
        elif self.tech_type == "Gaskessel":
            return {}
        elif self.tech_type == "BHKW":
            return {
                "th_Leistung_BHKW": float(self.PBHKWInput.text())
            }
        elif self.tech_type == "Holzgas-BHKW":
            return {
                "th_Leistung_BHKW": float(self.PHBHKWInput.text())
            }
        elif self.tech_type == "Geothermie":
            return {
                "Fläche": float(self.areaGInput.text()),
                "Bohrtiefe": float(self.depthInput.text()),
                "Temperatur_Geothermie": float(self.tempGInput.text())
            }
        elif self.tech_type == "Abwärme":
            return {
                "Kühlleistung_Abwärme": float(self.PWHInput.text()),
                "Temperatur_Abwärme": float(self.TWHInput.text())
            }
        
class HeatDemandEditDialog(QDialog):
    def __init__(self, gdf_HAST, parent=None):
        super(HeatDemandEditDialog, self).__init__(parent)
        self.gdf_HAST = gdf_HAST
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

        self.gdf_HAST.to_file(self.parent().Datei_HausanschlussstationenInput.text(), driver='GeoJSON')
        self.accept()  # Schließt das Dialogfenster
