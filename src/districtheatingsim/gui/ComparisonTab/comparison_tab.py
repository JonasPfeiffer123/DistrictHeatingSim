"""
Filename: comparison_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-30
Description: This class is responsible for creating the main tab that holds the different comparison tabs.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, QTabWidget)

from gui.ComparisonTab.stat_comparison_tab import StatComparisonTab
from gui.ComparisonTab.cost_comparison_tab import CostComparisonTab
from gui.ComparisonTab.building_heat_demand_comparison_tab import BuildingHeatDemandComparisonTab

class ComparisonTab(QWidget):
    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.variant_folder)

        self.initUI()

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)

        # Create a QTabWidget to hold the different comparison tabs
        self.tabWidget = QTabWidget()
        self.mainLayout.addWidget(self.tabWidget)
        
        # Create the StatComparisonTab and add it to the QTabWidget
        self.statComparisonTab = StatComparisonTab(self.folder_manager, self.config_manager)
        self.tabWidget.addTab(self.statComparisonTab, "Projektübersicht")

        # Create the CostComparisonTab and add it to the QTabWidget
        self.statscostComparisonTab = CostComparisonTab(self.folder_manager, self.config_manager)
        self.tabWidget.addTab(self.statscostComparisonTab, "Kostenvergleich")

        # Create the BuildingHeatDemandComparisonTab and add it to the QTabWidget
        self.BHDComparisonTab = BuildingHeatDemandComparisonTab(self.folder_manager, self.config_manager)
        self.tabWidget.addTab(self.BHDComparisonTab, "Vergleich Wärmebedarf Gebäude")

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

        #if title == "Vergleich Wärmebedarf Gebäude":
        #    contentLayout.addWidget(QLabel("Vergleich Wärmebedarf Gebäude"))
        #    contentLayout.addWidget(QLabel("Sanierungsvergleich Gebäude"))
            # Additional widgets and data specific to Net Length & Losses

        # Add the content layout to the content widget
        contentWidget.setLayout(contentLayout)

        # Add the subTab to the main QTabWidget
        self.tabWidget.addTab(subTab, title)