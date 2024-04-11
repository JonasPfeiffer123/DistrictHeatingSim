import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget, QMenuBar, QAction, QFileDialog, QLabel, QDialog, QPushButton, QMessageBox, QInputDialog
from PyQt5.QtCore import QObject, pyqtSignal
from gui.visualization_tab import VisualizationTab
from gui.calculation_tab import CalculationTab
from gui.mix_design_tab import MixDesignTab

# defines the map path
def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'heating_network_generation')

    return os.path.join(base_path, relative_path)

class StartDialog(QDialog):
    def __init__(self, parent=None):
        super(StartDialog, self).__init__(parent)
        self.parent = parent

        self.setWindowTitle("Projekt Auswahl")
        self.setGeometry(100, 100, 300, 100)
        layout = QVBoxLayout()

        self.openProjectBtn = QPushButton("Projekt öffnen")
        self.newProjectBtn = QPushButton("Neues Projekt erstellen")
        layout.addWidget(self.openProjectBtn)
        layout.addWidget(self.newProjectBtn)

        self.setLayout(layout)

        self.openProjectBtn.clicked.connect(self.openProject)
        self.newProjectBtn.clicked.connect(self.newProject)

    def openProject(self):
        self.parent.openExistingProject()
        self.accept()

    def newProject(self):
        self.parent.createNewProject()
        self.accept()

class CentralDataManager(QObject):
    project_folder_changed = pyqtSignal(str)  # definition of the signal

    def __init__(self):
        super(CentralDataManager, self).__init__()  # calling QObject constructor
        self.map_data = []
        self.project_folder = get_resource_path("project_data\Bad Muskau")  # variable project folder path
        print(self.project_folder)
    def add_data(self, data):
        self.map_data.append(data)
        # Trigger any updates needed for the map

    def get_map_data(self):
        return self.map_data

    def set_project_folder(self, path):
        self.project_folder = path
        self.project_folder_changed.emit(path)  # emit signal if path got changed

class HeatSystemDesignGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.data_manager = CentralDataManager()

        self.initUI()

        self.data_manager.project_folder_changed.connect(self.calcTab.updateDefaultPath)
        self.data_manager.project_folder_changed.connect(self.visTab.updateDefaultPath)
        self.data_manager.project_folder_changed.connect(self.mixDesignTab.updateDefaultPath)

        self.showStartDialog()

    def createNewProject(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Speicherort für neues Projekt wählen")
        if folder_path:
            projectName, ok = QInputDialog.getText(self, 'Neues Projekt', 'Projektnamen eingeben:')
            if ok and projectName:
                try:
                    full_path = os.path.join(folder_path, projectName)
                    os.makedirs(full_path)
                    for subdir in ["Gebäudedaten", "Lastgang", "Raumanalyse", "Wärmenetz"]:
                        os.makedirs(os.path.join(full_path, subdir))
                    QMessageBox.information(self, "Projekt erstellt", f"Projekt '{projectName}' wurde erfolgreich erstellt.")
                    self.setProjectFolderPath(full_path)
                except Exception as e:
                    QMessageBox.critical(self, "Fehler", f"Ein Fehler ist aufgetreten: {e}")

    def openExistingProject(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Projektordner auswählen")
        if folder_path:
            self.setProjectFolderPath(folder_path)

    def setProjectFolderPath(self, path):
        self.projectFolderPath = path
        self.data_manager.set_project_folder(path)
        self.folderLabel.setText(f"Ausgewählter Projektordner: {path}")

    def showStartDialog(self):
        self.startDialog = StartDialog(self)
        if self.startDialog.exec_() == QDialog.Accepted:
            if self.projectFolderPath:
                self.data_manager.set_project_folder(self.projectFolderPath)
                self.folderLabel.setText(f"Ausgewählter Projektordner: {self.projectFolderPath}")
            else:
                self.folderLabel.setText("Kein Ordner ausgewählt")

    def initUI(self):
        self.setWindowTitle("DistrictHeatSim")
        self.setGeometry(100, 100, 800, 600)  # Optional, standard size before full-screen

        self.layout1 = QVBoxLayout(self)

        self.initMenuBar()

        tabWidget = QTabWidget()
        self.layout1.addWidget(tabWidget)

        self.visTab = VisualizationTab(self.data_manager)
        self.calcTab = CalculationTab(self.data_manager)
        self.mixDesignTab = MixDesignTab(self.data_manager)

        # Adding tabs to the tab widget
        tabWidget.addTab(self.visTab, "Räumliche Analyse")
        tabWidget.addTab(self.calcTab, "Wärmenetzberechnung")
        tabWidget.addTab(self.mixDesignTab, "Erzeugerauslegung und Wirtschftlichkeitrechnung")

        # folder path Label
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

        fileMenu = self.menubar.addMenu('Datei')

        chooseProjectFolderAction = QAction('Projektordner festlegen', self)
        createNewProjectFolderAction = QAction('Neues Projekt erstellen', self)
        fileMenu.addAction(chooseProjectFolderAction)
        fileMenu.addAction(createNewProjectFolderAction)

        self.layout1.addWidget(self.menubar)

        # connection to function
        chooseProjectFolderAction.triggered.connect(self.openExistingProject)
        createNewProjectFolderAction.triggered.connect(self.createNewProject)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HeatSystemDesignGUI()
    ex.show()
    sys.exit(app.exec_())
