import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QTabWidget
from gui.mix_design_tab import MixDesignTab
from PyQt5.QtCore import pyqtSignal

class MixDesignMainWindow(QMainWindow):
    # Proxy-Signal definieren
    project_folder_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.variantTabWidget = QTabWidget()
        self.initUI()
        self.project_folder_changed.connect(self.updateTabsDefaultPath)

    
    def initUI(self):
        # Erstellen der Menüleiste
        menuBar = self.menuBar()

        # Menü für Varianten-Verwaltung
        variantMenu = menuBar.addMenu('Datei')

        # Aktion zum Hinzufügen einer neuen Variante
        addVariantAction = QAction('Variante hinzufügen', self)
        addVariantAction.triggered.connect(self.addVariant)
        variantMenu.addAction(addVariantAction)

        # Setup des Haupt-Tab-Widgets
        self.setCentralWidget(self.variantTabWidget)
        self.addVariant()  # Erste Variante hinzufügen

    def addVariant(self):
        mixDesignTab = MixDesignTab()
        self.variantTabWidget.addTab(mixDesignTab, f'Variante {self.variantTabWidget.count() + 1}')
        # Verbinden Sie das Proxy-Signal mit der updateDefaultPath Methode des neuen Tabs
        self.project_folder_changed.connect(mixDesignTab.updateDefaultPath)

    def updateTabsDefaultPath(self, new_path):
        # Diese Methode könnte notwendig sein, um alle aktuell offenen Tabs zu aktualisieren
        for index in range(self.variantTabWidget.count()):
            tab = self.variantTabWidget.widget(index)
            if hasattr(tab, 'updateDefaultPath'):
                tab.updateDefaultPath(new_path)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MixDesignMainWindow()
    ex.show()
    sys.exit(app.exec_())