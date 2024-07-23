"""
Filename: comparison_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Contains the ComparisonTab.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout,  QLabel)
from PyQt5.QtCore import pyqtSignal

class ComparisonTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent

        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)
        
        self.initUI()

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)

        self.labellabel = QLabel('Coming soon')
        self.mainLayout.addChildWidget(self.labellabel)

        self.setLayout(self.mainLayout)