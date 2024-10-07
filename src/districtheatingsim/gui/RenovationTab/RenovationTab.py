"""
Filename: RenovationTab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-29
Description: Contains the main RenovationTab, container of RenovationTab1 and RenovationTab2.
"""

from PyQt5.QtWidgets import QVBoxLayout, QProgressBar, QWidget, QTabWidget
from PyQt5.QtCore import pyqtSignal

from gui.RenovationTab.RenovationTab1 import RenovationTab1
from gui.RenovationTab.RenovationTab2 import RenovationTab2

class RenovationTabPresenter:
    """
    The Presenter class for the RenovationTab, managing interaction between the Model and View.
    """
    def __init__(self, folder_manager, data_manager, config_manager, view):
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager
        self.view = view

        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)

        # Initialize view with tabs
        self.initTabs()

    def initTabs(self):
        """
        Initialize the tabs with the appropriate views.
        """

        renovation_tab1 = RenovationTab1(self.folder_manager)
        renovation_tab2 = RenovationTab2(self.folder_manager, self.data_manager)

        self.view.addTab(renovation_tab1, "Wirtschaftlichkeitsrechnung Sanierung Quartier")
        self.view.addTab(renovation_tab2, "Wirtschaftlichkeitsrechnung Sanierung Einzelgebäude")

    def updateDefaultPath(self, new_base_path):
        """
        Update the default path for the project.

        Args:
            new_base_path (str): The new base path for the project.
        """
        self.view.base_path = new_base_path

class RenovationTabView(QWidget):
    """
    The View class for the RenovationTab, responsible for displaying the UI.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """
        Initialize the UI components of the RenovationTab.
        """
        main_layout = QVBoxLayout(self)

        # Create tabs
        self.tabs = QTabWidget(self)
        main_layout.addWidget(self.tabs, stretch=1)  # Set stretch to 1 to use available space

        self.progressBar = QProgressBar(self)
        main_layout.addWidget(self.progressBar)

    def addTab(self, widget, title):
        """
        Add a tab to the tab widget.

        Args:
            widget (QWidget): The widget to be added as a tab.
            title (str): The title of the tab.
        """
        self.tabs.addTab(widget, title)

class RenovationTab(QWidget):
    """
    The main entry point for the RenovationTab, initializing the MVP components.
    """
    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        super().__init__(parent)

        # Initialize View
        self.view = RenovationTabView(self)

        # Initialize Presenter
        self.presenter = RenovationTabPresenter(folder_manager, data_manager, config_manager, self.view)