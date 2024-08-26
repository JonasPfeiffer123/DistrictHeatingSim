"""
Filename: cost_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-22
Description: Contains the CostTab.
"""

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont

from heat_generators.heat_generator_classes import *

class CostTab(QWidget):
    """
    The CostTab class represents the tab responsible for displaying and managing cost-related data 
    for the different components in a heat generation project.

    Attributes:
        data_added (pyqtSignal): Signal emitted when new data is added.
        data_manager (object): Reference to the data manager instance.
        parent (QWidget): Reference to the parent widget.
        results (dict): Stores results data.
        tech_objects (list): List of technology objects.
        individual_costs (list): List of individual costs for each component.
        summe_tech_kosten (float): Sum of the technology costs.
        base_path (str): Base path for the project.
        summe_investitionskosten (float): Sum of the investment costs.
        summe_annuität (float): Sum of the annuities.
        totalCostLabel (QLabel): Label to display total costs.
    """
    data_added = pyqtSignal(object)  # Signal that transfers data as an object
    
    def __init__(self, data_manager, parent=None):
        """
        Initializes the CostTab instance.

        Args:
            data_manager (object): Reference to the data manager instance.
            parent (QWidget, optional): Reference to the parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent
        self.results = {}
        self.tech_objects = []
        self.individual_costs = []
        self.summe_tech_kosten = 0  # Initialize the variable

        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)
        
        self.initUI()

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default path for the project.

        Args:
            new_base_path (str): The new base path for the project.
        """
        self.base_path = new_base_path

    def initUI(self):
        mainLayout = QVBoxLayout()


