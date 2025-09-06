"""
Comparison Tab Module
====================

Main tab widget containing multiple comparison sub-tabs for project analysis.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-30
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, QTabWidget)

from districtheatingsim.gui.ComparisonTab.stat_comparison_tab import StatComparisonTab
from districtheatingsim.gui.ComparisonTab.cost_comparison_tab import CostComparisonTab
from districtheatingsim.gui.ComparisonTab.building_heat_demand_comparison_tab import BuildingHeatDemandComparisonTab

class ComparisonTab(QWidget):
    """
    Main tab widget for project comparison and analysis.
    """
    
    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initialize comparison tab with sub-tabs.

        Parameters
        ----------
        folder_manager : FolderManager
            Project folder manager.
        data_manager : DataManager
            Application data manager.
        config_manager : ConfigManager
            Configuration manager.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.variant_folder)

        self.initUI()

    def updateDefaultPath(self, new_base_path):
        """
        Update base path when project folder changes.

        Parameters
        ----------
        new_base_path : str
            New base path.
        """
        self.base_path = new_base_path

    def initUI(self):
        """Initialize user interface with comparison sub-tabs."""
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
        """
        Create scrollable sub-tab widget.

        Parameters
        ----------
        title : str
            Tab title.
        """
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