from PyQt5.QtCore import pyqtSignal

"""
Filename: comparison_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
Description: Contains the ComparisonTab. Currently no content.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, QPushButton)

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

        self.labellabel = QLabel("""Brainstorming: What is needed?
                                 Add project button
                                 remove project button
                                 show stats like number of houses
                                 heat demand
                                 net length
                                 net losses
                                 costs
                                 heat generation
                                 heat production costs
                                 and all the other stuff
                                 its just enabling to output all the data
                                 """)
        self.mainLayout.addWidget(self.labellabel)

        self.setLayout(self.mainLayout)
        # Create a scroll area to contain the content
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.mainLayout.addWidget(self.scrollArea)

        # Create a widget to hold the content
        self.contentWidget = QWidget()
        self.scrollArea.setWidget(self.contentWidget)

        # Create a layout for the content widget
        self.contentLayout = QVBoxLayout(self.contentWidget)

        # Add project button
        self.addProjectButton = QPushButton("Add Project")
        self.addProjectButton.clicked.connect(self.addProject)
        self.contentLayout.addWidget(self.addProjectButton)

        # Remove project button
        self.removeProjectButton = QPushButton("Remove Project")
        self.removeProjectButton.clicked.connect(self.removeProject)
        self.contentLayout.addWidget(self.removeProjectButton)

        # Show stats
        self.statsLabel = QLabel("Stats:")
        self.contentLayout.addWidget(self.statsLabel)

        # Add other stats labels here
        self.heatDemandLabel = QLabel("Heat Demand:")
        self.contentLayout.addWidget(self.heatDemandLabel)

        self.netLengthLabel = QLabel("Net Length:")
        self.contentLayout.addWidget(self.netLengthLabel)

        self.netLossesLabel = QLabel("Net Losses:")
        self.contentLayout.addWidget(self.netLossesLabel)

        self.costsLabel = QLabel("Costs:")
        self.contentLayout.addWidget(self.costsLabel)

        self.heatGenerationLabel = QLabel("Heat Generation:")
        self.contentLayout.addWidget(self.heatGenerationLabel)

        self.heatProductionCostsLabel = QLabel("Heat Production Costs:")
        self.contentLayout.addWidget(self.heatProductionCostsLabel)

        # Set the content layout
        self.contentWidget.setLayout(self.contentLayout)

    def addProject(self):
        # Implement your logic to add a project here
        # For example, you can open a file dialog to select a project file
        # and then update the UI accordingly
        pass

    def removeProject(self):
        # Implement your logic to remove a project here
        # For example, you can remove the selected project from the UI
        pass