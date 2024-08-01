"""
Filename: lod2_dialogs.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
Description: Contains the Dialogs for the LOD2Tab.
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFileDialog
from PyQt5.QtGui import QFont

class FilterDialog(QDialog):
    """
    A dialog window for filtering LOD2 data based on different input files and methods.

    Attributes:
        base_path (str): The base path for default file locations.
        inputLOD2geojsonLineEdit (QLineEdit): Line edit for input LOD2 geojson file path.
        inputLOD2geojsonButton (QPushButton): Button to browse for input LOD2 geojson file.
        inputfilterPolygonLineEdit (QLineEdit): Line edit for input filter polygon file path.
        inputfilterPolygonButton (QPushButton): Button to browse for input filter polygon file.
        inputfilterBuildingDataLineEdit (QLineEdit): Line edit for input filter building data csv file path.
        inputfilterBuildingDataButton (QPushButton): Button to browse for input filter building data csv file.
        outputLOD2geojsonLineEdit (QLineEdit): Line edit for output LOD2 geojson file path.
        outputLOD2geojsonButton (QPushButton): Button to browse for output LOD2 geojson file.
        filterMethodComboBox (QComboBox): Combo box to select the filter method.
    """
    def __init__(self, base_path, parent=None):
        """
        Initializes the FilterDialog.

        Args:
            base_path (str): The base path for default file locations.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.base_path = base_path
        self.setWindowTitle("LOD2-Daten filtern")
        self.setGeometry(300, 300, 600, 400)
        
        layout = QVBoxLayout(self)
        font = QFont()
        font.setPointSize(10)

        self.inputLOD2geojsonLineEdit, self.inputLOD2geojsonButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\lod2_data.geojson", font)
        layout.addLayout(self.createFileInputLayout("Eingabe-LOD2-geojson:", self.inputLOD2geojsonLineEdit, self.inputLOD2geojsonButton, font))

        self.inputfilterPolygonLineEdit, self.inputfilterPolygonButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\Quartierabgrenzung.geojson", font)
        layout.addLayout(self.createFileInputLayout("Eingabe-Filter-Polygon-shapefile:", self.inputfilterPolygonLineEdit, self.inputfilterPolygonButton, font))

        self.inputfilterBuildingDataLineEdit, self.inputfilterBuildingDataButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\data_input.csv", font)
        layout.addLayout(self.createFileInputLayout("Eingabe-Filter-Gebäude-csv:", self.inputfilterBuildingDataLineEdit, self.inputfilterBuildingDataButton, font))

        self.outputLOD2geojsonLineEdit, self.outputLOD2geojsonButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\Quartier LOD2.geojson", font)
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
        """
        Creates a file input widget with a QLineEdit and a QPushButton.

        Args:
            default_path (str): The default path to be displayed in the QLineEdit.
            font (QFont): The font to be used for the widgets.

        Returns:
            tuple: A tuple containing the QLineEdit and QPushButton.
        """
        lineEdit = QLineEdit(default_path)
        lineEdit.setFont(font)
        button = QPushButton("Durchsuchen")
        button.setFont(font)
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, label_text, lineEdit, button, font):
        """
        Creates a horizontal layout for the file input widgets.

        Args:
            label_text (str): The text for the QLabel.
            lineEdit (QLineEdit): The QLineEdit for file input.
            button (QPushButton): The QPushButton for browsing files.
            font (QFont): The font to be used for the QLabel.

        Returns:
            QHBoxLayout: The horizontal layout containing the label, line edit, and button.
        """
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def selectFile(self, lineEdit):
        """
        Opens a file dialog to select a file and sets the selected file path to the QLineEdit.

        Args:
            lineEdit (QLineEdit): The QLineEdit to set the selected file path.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", f"{self.base_path}/Gebäudedaten", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def updateFilterInputVisibility(self):
        """
        Updates the visibility of the file input widgets based on the selected filter method.
        """
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