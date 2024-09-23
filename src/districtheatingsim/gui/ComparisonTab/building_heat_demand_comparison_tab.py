"""
Filename: building_heat_demand_comparison_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-30
Description: This class is responsible for creating the tab that compares the heat demand of different buildings.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QVBoxLayout, QFileDialog, QWidget, QMessageBox, QHBoxLayout, QPushButton)

class BuildingHeatDemandComparisonTab(QWidget):
    def __init__(self, folder_manager, config_manager, parent=None):
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.config_manager = config_manager
        self.loaded_data = []
        self.loaded_filenames = []

        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.variant_folder)

        self.initUI()

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

    def initUI(self):
        self.layout = QVBoxLayout(self)

        # Add buttons to load and remove data
        button_layout = QHBoxLayout()

        self.loadButton = QPushButton("Projektdaten laden")
        self.loadButton.clicked.connect(self.addData)
        button_layout.addWidget(self.loadButton)

        self.removeButton = QPushButton("Projektdaten entfernen")
        self.removeButton.clicked.connect(self.removeData)
        button_layout.addWidget(self.removeButton)

        self.layout.addLayout(button_layout)

        # Initialize the plot area
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(800, 400)
        self.layout.addWidget(self.canvas)

        self.setLayout(self.layout)

    def addData(self):
        # Open a file dialog to select the base path for the data
        path, _ = QFileDialog.getOpenFileName(self, "Öffnen", self.base_path, "CSV-Dateien (*.csv)")
        if path:
            try:
                df = pd.read_csv(path, delimiter=';')
                self.loaded_data.append(df)
                self.loaded_filenames.append(os.path.basename(path))
                self.update_plot()
            except Exception as e:
                self.show_error_message("Fehler beim Hinzufügen des Datensatzes", f"Es ist ein Fehler aufgetreten: {str(e)}")

    def removeData(self):
        if self.loaded_data:
            self.loaded_data.pop()
            self.loaded_filenames.pop()
            self.update_plot()
        else:
            QMessageBox.warning(self, "Keine Daten", "Keine Daten zum Entfernen vorhanden.")

    def update_plot(self):
        if not self.loaded_data:
            self.figure.clear()
            self.canvas.draw()
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        all_data = pd.concat(self.loaded_data, keys=self.loaded_filenames, names=['Filename', 'Index'])
        all_data_grouped = all_data.groupby(['Adresse', 'Filename'])['Wärmebedarf'].sum().unstack('Filename').fillna(0)
        
        num_datasets = len(self.loaded_data)
        num_addresses = len(all_data_grouped)
        
        bar_width = 0.8 / num_datasets
        indices = np.arange(num_addresses)
        
        colors = plt.cm.Set1.colors[:num_datasets]

        for i, (filename, color) in enumerate(zip(all_data_grouped.columns, colors)):
            ax.barh(indices + i * bar_width, all_data_grouped[filename], bar_width, label=filename, color=color)

        ax.set_yticks(indices + bar_width * (num_datasets - 1) / 2)
        ax.set_yticklabels(all_data_grouped.index)
        ax.set_ylabel('Adresse')
        ax.set_xlabel('Wärmebedarf in kWh')
        ax.legend()
        
        self.canvas.draw()

    def show_error_message(self, title, message):
        QMessageBox.critical(self, title, message)