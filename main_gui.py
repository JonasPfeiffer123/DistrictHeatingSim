import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget, QMenuBar, QAction, QFileDialog, QLabel
from PyQt5.QtCore import QObject, pyqtSignal
from gui.visualization_tab import VisualizationTab
from gui.calculation_tab import CalculationTab
from gui.mix_design_main_window import MixDesignMainWindow

from PyQt5.QtCore import QObject, pyqtSignal

class CentralDataManager(QObject):
    project_folder_changed = pyqtSignal(str)  # Signaldefinition

    def __init__(self):
        super(CentralDataManager, self).__init__()  # QObject Konstruktor aufrufen
        self.map_data = []
        self.project_folder = "project_data/Beispiel Zittau"  # Variable zum Speichern des ausgewählten Ordnerpfads

    def add_data(self, data):
        self.map_data.append(data)
        # Trigger any updates needed for the map

    def get_map_data(self):
        return self.map_data

    def set_project_folder(self, path):
        self.project_folder = path
        self.project_folder_changed.emit(path)  # Signal auslösen, wenn der Pfad geändert wird

class HeatSystemDesignGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.data_manager.project_folder_changed.connect(self.calcTab.updateDefaultPath)
        self.data_manager.project_folder_changed.connect(self.visTab.updateDefaultPath)
        self.data_manager.project_folder_changed.connect(self.mixDesignMainWindow.project_folder_changed.emit)

    def initUI(self):
        self.setWindowTitle("Hier könnte ein cooler Softwarename stehen")
        self.setGeometry(100, 100, 800, 600)  # Optional, standard size before full-screen

        self.layout1 = QVBoxLayout(self)

        self.initMenuBar()

        tabWidget = QTabWidget()
        self.layout1.addWidget(tabWidget)

        # Creating individual tabs
        self.data_manager = CentralDataManager()

        self.visTab = VisualizationTab(self.data_manager)
        self.calcTab = CalculationTab(self.data_manager)
        self.mixDesignMainWindow = MixDesignMainWindow()

        # Adding tabs to the tab widget
        tabWidget.addTab(self.visTab, "Räumliche Analyse")
        tabWidget.addTab(self.calcTab, "Wärmenetzberechnung")
        tabWidget.addTab(self.mixDesignMainWindow, "Erzeugerauslegung und Wirtschftlichkeitrechnung")

        # Ordnerauswahl Label
        if self.data_manager.project_folder != "" or self.data_manager.project_folder != None:
            self.folderLabel = QLabel(f"Standard-Projektordner: {self.data_manager.project_folder}")
        else:
            self.folderLabel = QLabel("Kein Ordner ausgewählt")
        self.layout1.addWidget(self.folderLabel)

        # Set the layout
        self.setLayout(self.layout1)

        # Maximize the main window to the screen size
        self.showMaximized()

    def initMenuBar(self):
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        networkMenu = self.menubar.addMenu('Datei')
        generateNetAction = QAction('Projektordner festlegen', self)
        networkMenu.addAction(generateNetAction)
        self.layout1.addWidget(self.menubar)

        # Verbindungen zu der Funktion
        generateNetAction.triggered.connect(self.ProjektordnerNameDialog)

    def ProjektordnerNameDialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Projektordner auswählen")
        if folder_path:
            self.data_manager.set_project_folder(folder_path)
            self.folderLabel.setText(f"Ausgewählter Projektordner: {folder_path}")
        else:
            self.folderLabel.setText("Kein Ordner ausgewählt")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HeatSystemDesignGUI()
    ex.show()
    sys.exit(app.exec_())
