import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QTabWidget, QVBoxLayout
from gui.mix_design_tab import MixDesignTab

class MixDesignMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.variantTabWidget = QTabWidget()
        self.initUI()
    
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
        self.mixDesignTab = MixDesignTab()
        self.variantTabWidget.addTab(self.mixDesignTab, f'Variante {self.variantTabWidget.count() + 1}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MixDesignMainWindow()
    ex.show()
    sys.exit(app.exec_())