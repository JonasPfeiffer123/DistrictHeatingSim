"""
Filename: RenovationTab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Contains the main RenovationTab, container of RenovationTab1 and RenovationTab2
"""

from PyQt5.QtWidgets import QVBoxLayout, QProgressBar, QWidget, QTabWidget
from PyQt5.QtCore import pyqtSignal

from gui.RenovationTab.RenovationTab1 import RenovationTab1
from gui.RenovationTab.RenovationTab2 import RenovationTab2

class RenovationTab(QWidget):
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
        main_layout = QVBoxLayout(self)

        # Create tabs
        tabs = QTabWidget(self)
        main_layout.addWidget(tabs)

        self.RenovationTab1 = RenovationTab1(self.data_manager)
        self.RenovationTab2 = RenovationTab2(self.data_manager)

        tabs.addTab(self.RenovationTab1, "Wirtschaftlichkeitsrechnung Sanierung Quartier")
        tabs.addTab(self.RenovationTab2, "Wirtschaftlichkeitsrechnung Sanierung Einzelgebäude")
        
        self.progressBar = QProgressBar(self)
        main_layout.addWidget(self.progressBar)

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path