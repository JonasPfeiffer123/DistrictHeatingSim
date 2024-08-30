"""
Filename: comparison_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-30
Description: Contains the ComparisonTab.
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                             QPushButton, QTabWidget, QHBoxLayout)

from gui.ComparisonTab.stats_tab import StatsTab

class ComparisonTab(QWidget):
    def __init__(self, folder_manager, data_manager, parent=None):
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.data_manager = data_manager

        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.project_folder)

        self.initUI()

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)

        # Create a QTabWidget to hold the different comparison tabs
        self.tabWidget = QTabWidget()
        self.mainLayout.addWidget(self.tabWidget)
        
        # Create the StatsTab and add it to the QTabWidget
        self.statsTab = StatsTab(self.folder_manager)
        self.tabWidget.addTab(self.statsTab, "Projektübersicht")

        # Create different subtabs
        self.createSubTab("Kostenvergleich")
        self.createSubTab("Vergleich Wärmebedarf Gebäude")

        # Set the main layout
        self.setLayout(self.mainLayout)

    def createSubTab(self, title):
        subTab = QWidget()
        subTabLayout = QVBoxLayout(subTab)

        # Create a scroll area to contain the content
        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        subTabLayout.addWidget(scrollArea)

        # Create a widget to hold the content
        contentWidget = QWidget()
        scrollArea.setWidget(contentWidget)

        # Create a layout for the content widget
        contentLayout = QVBoxLayout(contentWidget)

        if title == "Kostenvergleich":
            contentLayout.addWidget(QLabel("Kostenvergleich"))
            contentLayout.addWidget(QLabel("Wärmegestehungskosten"))
            # Additional widgets and data specific to Costs

        elif title == "Vergleich Wärmebedarf Gebäude":
            contentLayout.addWidget(QLabel("Vergleich Wärmebedarf Gebäude"))
            contentLayout.addWidget(QLabel("Sanierungsvergleich Gebäude"))
            # Additional widgets and data specific to Net Length & Losses

        # Add the content layout to the content widget
        contentWidget.setLayout(contentLayout)

        # Add the subTab to the main QTabWidget
        self.tabWidget.addTab(subTab, title)