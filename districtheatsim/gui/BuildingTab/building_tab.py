"""
Filename: building_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Contains the BuildingTab.
"""

import json
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QMessageBox
from PyQt5.QtCore import pyqtSignal

class BuildingTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent

        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        # Update the base path immediately with the current project folder
        self.updateDefaultPath(self.data_manager.project_folder)

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        self.geojson_path_label = QLabel("GeoJSON-Datei: Nicht ausgewählt", self)
        layout.addWidget(self.geojson_path_label)

        self.select_geojson_button = QPushButton("GeoJSON-Datei auswählen", self)
        self.select_geojson_button.clicked.connect(self.selectGeoJsonFile)
        layout.addWidget(self.select_geojson_button)

        self.process_button = QPushButton("Daten verarbeiten", self)
        self.process_button.clicked.connect(self.process_data)
        layout.addWidget(self.process_button)

        self.results_path_label = QLabel("Ergebnisse gespeichert in: Nicht verfügbar", self)
        layout.addWidget(self.results_path_label)

        self.setLayout(layout)

    def updateDefaultPath(self, path):
        self.base_path = path

    def selectGeoJsonFile(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'GeoJSON-Datei auswählen', '', 'GeoJSON Files (*.geojson);;All Files (*)')
        if fname:
            self.geojson_path = fname
            self.geojson_path_label.setText(f"GeoJSON-Datei: {fname}")
        else:
            self.geojson_path = None

    # Dummy-Berechnungsfunktion
    def berechnungen(self):
        lastgang_wärme = list(np.random.rand(8760))
        vorlauftemperatur = list(np.random.rand(8760) * 50 + 50)  # Dummy values between 50 and 100
        rücklauftemperatur = list(np.random.rand(8760) * 40 + 40)  # Dummy values between 40 and 80
        return lastgang_wärme, vorlauftemperatur, rücklauftemperatur

    def process_data(self):
        if not hasattr(self, 'geojson_path') or not self.geojson_path:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie zuerst eine GeoJSON-Datei aus.")
            return

        ergebnisse_path = QFileDialog.getSaveFileName(self, 'Ergebnisse speichern als', '', 'JSON Files (*.json);;All Files (*)')[0]
        if not ergebnisse_path:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Speicherort für die Ergebnisse aus.")
            return

        # GeoJSON-Datei laden
        try:
            with open(self.geojson_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der GeoJSON-Datei: {e}")
            return

        # Ergebnisse-Container
        ergebnisse = {}

        # Berechnungen für jedes Feature durchführen und Ergebnisse speichern
        for feature in geojson_data['features']:
            feature_id = feature['properties'].get('id')
            if feature_id is not None:
                lastgang_wärme, vorlauftemperatur, rücklauftemperatur = self.berechnungen()
                ergebnisse[feature_id] = {
                    "lastgang_wärme": lastgang_wärme,
                    "vorlauftemperatur": vorlauftemperatur,
                    "rücklauftemperatur": rücklauftemperatur
                }

        # Ergebnisse in eine separate JSON-Datei speichern
        try:
            with open(ergebnisse_path, 'w', encoding='utf-8') as f:
                json.dump(ergebnisse, f, indent=4)
            self.results_path_label.setText(f"Ergebnisse gespeichert in: {ergebnisse_path}")
            QMessageBox.information(self, "Erfolg", f"Ergebnisse wurden in {ergebnisse_path} gespeichert.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern der Ergebnisse: {e}")