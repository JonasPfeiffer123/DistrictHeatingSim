from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGroupBox, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit)

class ExampleDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        mainLayout = QVBoxLayout()

        # Import-Gruppe
        importGroup = QGroupBox("Import")
        importLayout = QVBoxLayout()
        importBtn = QPushButton("Datei importieren")
        importLayout.addWidget(importBtn)
        importGroup.setLayout(importLayout)
        mainLayout.addWidget(importGroup)

        # Berechnungsmethode
        methodGroup = QGroupBox("Berechnungsmethode")
        methodLayout = QVBoxLayout()
        methodCombo = QComboBox()
        methodCombo.addItems(["Methode 1", "Methode 2", "Methode 3"])
        methodLayout.addWidget(methodCombo)
        methodGroup.setLayout(methodLayout)
        mainLayout.addWidget(methodGroup)

        # Netzkonfiguration
        networkGroup = QGroupBox("Netzkonfiguration")
        networkLayout = QVBoxLayout()
        networkEdit = QLineEdit("Standardkonfiguration")
        networkLayout.addWidget(networkEdit)
        networkGroup.setLayout(networkLayout)
        mainLayout.addWidget(networkGroup)

        # Optimierung
        optimizationGroup = QGroupBox("Optimierung")
        optimizationLayout = QVBoxLayout()
        optimizeBtn = QPushButton("Optimieren")
        optimizationLayout.addWidget(optimizeBtn)
        optimizationGroup.setLayout(optimizationLayout)
        mainLayout.addWidget(optimizationGroup)

        # Netzvorschau
        previewGroup = QGroupBox("Netzvorschau")
        previewLayout = QVBoxLayout()
        previewText = QTextEdit("Netzwerk-Status und Details")
        previewLayout.addWidget(previewText)
        previewGroup.setLayout(previewLayout)
        mainLayout.addWidget(previewGroup)

        # Diagrammvorschau
        chartGroup = QGroupBox("Diagrammvorschau")
        chartLayout = QVBoxLayout()
        chartText = QTextEdit("Diagramm-Informationen")
        chartLayout.addWidget(chartText)
        chartGroup.setLayout(chartLayout)
        mainLayout.addWidget(chartGroup)

        self.setLayout(mainLayout)
        self.setWindowTitle('Konfigurationsdialog')
        self.resize(400, 600)

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    ex = ExampleDialog()
    ex.show()
    sys.exit(app.exec_())