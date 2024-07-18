from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFileDialog
from PyQt5.QtGui import QFont

class FilterDialog(QDialog):
    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.setWindowTitle("LOD2-Daten filtern")
        self.setGeometry(300, 300, 600, 400)
        
        layout = QVBoxLayout(self)
        font = QFont()
        font.setPointSize(10)

        self.inputLOD2geojsonLineEdit, self.inputLOD2geojsonButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\lod2_data\\lod2_data.geojson", font)
        layout.addLayout(self.createFileInputLayout("Eingabe-LOD2-geojson:", self.inputLOD2geojsonLineEdit, self.inputLOD2geojsonButton, font))

        self.inputfilterPolygonLineEdit, self.inputfilterPolygonButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\lod2_data\\quartier_1.geojson", font)
        layout.addLayout(self.createFileInputLayout("Eingabe-Filter-Polygon-shapefile:", self.inputfilterPolygonLineEdit, self.inputfilterPolygonButton, font))

        self.inputfilterBuildingDataLineEdit, self.inputfilterBuildingDataButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\data_output_ETRS89.csv", font)
        layout.addLayout(self.createFileInputLayout("Eingabe-Filter-Gebäude-csv:", self.inputfilterBuildingDataLineEdit, self.inputfilterBuildingDataButton, font))

        self.outputLOD2geojsonLineEdit, self.outputLOD2geojsonButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\lod2_data\\filtered_LOD_quartier_1.geojson", font)
        layout.addLayout(self.createFileInputLayout("Ausgabe-LOD2-geojson:", self.outputLOD2geojsonLineEdit, self.outputLOD2geojsonButton, font))

        self.filterMethodComboBox = QComboBox(self)
        self.filterMethodComboBox.addItems(["Filter by Building Data CSV", "Filter by Polygon"])
        self.filterMethodComboBox.currentIndexChanged.connect(self.updateFilterInputVisibility)
        layout.addWidget(self.filterMethodComboBox)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Abbrechen")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self.updateFilterInputVisibility()

    def createFileInput(self, default_path, font):
        lineEdit = QLineEdit(default_path)
        lineEdit.setFont(font)
        button = QPushButton("Durchsuchen")
        button.setFont(font)
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, label_text, lineEdit, button, font):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def selectFile(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def updateFilterInputVisibility(self):
        filter_method = self.filterMethodComboBox.currentText()
        if filter_method == "Filter by Polygon":
            self.inputfilterPolygonLineEdit.show()
            self.inputfilterBuildingDataLineEdit.hide()
            self.inputfilterPolygonButton.show()
            self.inputfilterBuildingDataButton.hide()
        elif filter_method == "Filter by Building Data CSV":
            self.inputfilterPolygonLineEdit.hide()
            self.inputfilterBuildingDataLineEdit.show()
            self.inputfilterPolygonButton.hide()
            self.inputfilterBuildingDataButton.show()