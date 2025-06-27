"""
Renovation Tab Module
=====================

Main container for renovation analysis tabs using MVP architecture.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-29
"""

from PyQt5.QtWidgets import QVBoxLayout, QProgressBar, QWidget, QTabWidget

from districtheatingsim.gui.RenovationTab.RenovationTab1 import RenovationTab1
from districtheatingsim.gui.RenovationTab.RenovationTab2 import RenovationTab2

class RenovationTabPresenter:
    """
    Presenter for renovation tab, managing interaction between model and view.
    """
    def __init__(self, folder_manager, data_manager, config_manager, view):
        """
        Initialize renovation tab presenter.
        
        Parameters
        ----------
        folder_manager : object
            Project folder manager.
        data_manager : object
            Application data manager.
        config_manager : object
            Configuration manager.
        view : RenovationTabView
            Associated view component.
        """
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager
        self.view = view

        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)

        # Initialize view with tabs
        self.initTabs()

    def initTabs(self):
        """Initialize renovation analysis sub-tabs."""
        renovation_tab1 = RenovationTab1(self.folder_manager)
        renovation_tab2 = RenovationTab2(self.folder_manager, self.data_manager)

        self.view.addTab(renovation_tab1, "Wirtschaftlichkeitsrechnung Sanierung Quartier")
        self.view.addTab(renovation_tab2, "Wirtschaftlichkeitsrechnung Sanierung Einzelgebäude")

    def updateDefaultPath(self, new_base_path):
        """
        Update project default path.

        Parameters
        ----------
        new_base_path : str
            New base path for the project.
        """
        self.view.base_path = new_base_path

class RenovationTabView(QWidget):
    """
    View component for renovation tab UI display.
    """
    def __init__(self, parent=None):
        """
        Initialize renovation tab view.
        
        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """Initialize UI components."""
        main_layout = QVBoxLayout(self)

        # Create tabs
        self.tabs = QTabWidget(self)
        main_layout.addWidget(self.tabs, stretch=1)

        self.progressBar = QProgressBar(self)
        main_layout.addWidget(self.progressBar)

    def addTab(self, widget, title):
        """
        Add tab to tab widget.

        Parameters
        ----------
        widget : QWidget
            Widget to add as tab.
        title : str
            Tab title.
        """
        self.tabs.addTab(widget, title)

class RenovationTab(QWidget):
    """
    Main renovation tab widget with MVP architecture.
    
    Entry point for renovation analysis functionality containing
    district and individual building renovation tabs.
    """
    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initialize renovation tab with MVP components.
        
        Parameters
        ----------
        folder_manager : object
            Project folder manager.
        data_manager : object
            Application data manager.
        config_manager : object
            Configuration manager.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)

        # Initialize View
        self.view = RenovationTabView(self)

        # Initialize Presenter
        self.presenter = RenovationTabPresenter(folder_manager, data_manager, config_manager, self.view)