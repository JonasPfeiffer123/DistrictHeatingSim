import itertools
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt, pyqtSignal

from heat_generators.heat_generator_classes import *
from gui.checkable_combobox import CheckableComboBox

class ResultsTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent
        self.results = {}
        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)
        self.tech_objects = []
        self.initUI()

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

    def initUI(self):
        mainScrollArea = QScrollArea(self)
        mainScrollArea.setWidgetResizable(True)

        mainWidget = QWidget()
        mainLayout = QVBoxLayout(mainWidget)

        self.mainLayout = mainLayout
        self.setupCalculationOptimization()
        self.setupDiagrams(mainLayout)

        mainScrollArea.setWidget(mainWidget)

        tabLayout = QVBoxLayout(self)
        tabLayout.addWidget(mainScrollArea)  # Scrollbereich darunter hinzufügen
        self.setLayout(tabLayout)
    
    ### Setup der Berechnungsergebnistabellen ###
    def setupCalculationOptimization(self):
        self.resultLabel = QLabel('Übersicht Erzeugung')
        self.mainLayout.addWidget(self.resultLabel)

        # Hier die neue HBox für die ResultsTable und das Diagramm hinzufügen
        self.resultsAndPieChartLayout = QHBoxLayout()
        self.mainLayout.addLayout(self.resultsAndPieChartLayout)
        
        self.setupResultsTable()
        self.setupPieChart()

        self.resultLabel = QLabel('Ergebnisse Wirtschaftlichkeit')
        self.mainLayout.addWidget(self.resultLabel)
        self.setupAdditionalResultsTable()

    ### Results Table ###
    def setupResultsTable(self):
        # Tabelle initialisieren
        self.resultsTable = QTableWidget()
        self.resultsTable.setColumnCount(4)  # Anzahl der Spalten
        self.resultsTable.setHorizontalHeaderLabels(['Technologie', 'Wärmemenge (MWh)', 'Kosten (€/MWh)', 'Anteil (%)'])
        self.resultsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Spaltenbreite anpassen
        self.resultsAndPieChartLayout.addWidget(self.resultsTable)

    def showResultsInTable(self, results):
        self.resultsTable.setRowCount(len(results['techs']))  # Zeilenanzahl basierend auf der Anzahl der Technologien

        for i, (tech, wärmemenge, wgk, anteil) in enumerate(zip(results['techs'], results['Wärmemengen'], results['WGK'], results['Anteile'])):
            # Setzen der Zellenwerte für jede Zeile
            self.resultsTable.setItem(i, 0, QTableWidgetItem(tech))
            self.resultsTable.setItem(i, 1, QTableWidgetItem(f"{wärmemenge:.2f}"))
            self.resultsTable.setItem(i, 2, QTableWidgetItem(f"{wgk:.2f}"))
            self.resultsTable.setItem(i, 3, QTableWidgetItem(f"{anteil*100:.2f}%"))

        self.resultsTable.resizeColumnsToContents()  # Passt die Spaltenbreite an den Inhalt an
        self.adjustTableSize(self.resultsTable)  # Anpassen der Größe der Tabelle
    
    ### Additional Results Table ###
    def setupAdditionalResultsTable(self):
        # Tabelle initialisieren
        self.additionalResultsTable = QTableWidget()
        self.additionalResultsTable.setColumnCount(3)  # Anzahl der Spalten
        self.additionalResultsTable.setHorizontalHeaderLabels(['Ergebnis', 'Wert', 'Einheit'])
        self.additionalResultsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Spaltenbreite anpassen
        self.mainLayout.addWidget(self.additionalResultsTable)

    def showAdditionalResultsTable(self, result):
        self.results = result
        self.WGK_Infra = self.parent.costTab.summe_annuität/self.results['Jahreswärmebedarf']
        self.WGK_Gesamt = self.results['WGK_Gesamt'] + self.WGK_Infra

        # Daten für die Tabelle
        data = [
            ("Jahreswärmebedarf", round(self.results['Jahreswärmebedarf'],1), "MWh"),
            ("Stromerzeugung", round(self.results['Strommenge'], 2), "MWh"),
            ("Strombedarf", round(self.results['Strombedarf'], 2), "MWh"),
            ("Wärmegestehungskosten Erzeugeranlagen", round(self.results['WGK_Gesamt'], 2), "€/MWh"),
            ("Wärmegestehungskosten Netzinfrastruktur", round(self.WGK_Infra, 2), "€/MWh"),
            ("Wärmegestehungskosten Gesamt", round(self.WGK_Gesamt, 2), "€/MWh")
        ]

        self.additionalResultsTable.setRowCount(len(data))

        # Daten in die Tabelle einfügen
        for i, (description, value, unit) in enumerate(data):
            self.additionalResultsTable.setItem(i, 0, QTableWidgetItem(description))
            self.additionalResultsTable.setItem(i, 1, QTableWidgetItem(str(value)))
            self.additionalResultsTable.setItem(i, 2, QTableWidgetItem(unit))

        self.additionalResultsTable.resizeColumnsToContents()
        self.adjustTableSize(self.additionalResultsTable)

    ### Table size adjustment function ###
    def adjustTableSize(self, table):
        # header row height
        header_height = table.horizontalHeader().height()
        # hight of all rows
        rows_height = sum([table.rowHeight(i) for i in range(table.rowCount())])
        # configuring table height
        table.setFixedHeight(header_height + rows_height)
                
    ### Setup Diagramm-Plots ###
    def setupDiagrams(self, mainLayout):
        diagramScrollArea, diagramWidget, diagramLayout = self.setupDiagramScrollArea()
        self.figure1, self.canvas1 = self.addFigure(diagramLayout)
        diagramScrollArea.setWidget(diagramWidget)
        mainLayout.addWidget(diagramScrollArea)

    def setupDiagramScrollArea(self):
        diagramScrollArea = QScrollArea()
        diagramScrollArea.setWidgetResizable(True)
        diagramScrollArea.setMinimumSize(800, 1200)

        diagramWidget = QWidget()
        diagramLayout = QVBoxLayout(diagramWidget)

        return diagramScrollArea, diagramWidget, diagramLayout

    def addFigure(self, layout):
        figure = Figure(figsize=(8, 6))  # Breite und Höhe in Zoll einstellen
        canvas = FigureCanvas(figure)
        canvas.setMinimumSize(400, 400)  # Größe in Pixel
        layout.addWidget(canvas)
        return figure, canvas
    
    def setupPieChart(self):
        # Kreisdiagramm erstellen
        self.pieChartFigure = Figure(figsize=(6, 6))
        self.pieChartCanvas = FigureCanvas(self.pieChartFigure)
        self.pieChartCanvas.setMinimumSize(800, 600)  # Größe in Pixel
        self.resultsAndPieChartLayout.addWidget(self.pieChartCanvas)

    ### Plotten der Ergebnisse ###
    def plotResults(self, results):
        self.results = results
        if not hasattr(self, 'dataSelectionDropdown'):
            self.createPlotControlDropdown()

        self.figure1.clear()
        self.plotStackPlot(self.figure1, results['time_steps'], results['Wärmeleistung_L'], results['techs'], results['colors'], results['Last_L'])
        self.canvas1.draw()

        self.updatePieChart()

    def plotStackPlot(self, figure, t, data, labels, colors, Last):
        ax = figure.add_subplot(111)
        ax.stackplot(t, data, labels=labels, colors=colors)
        ax.set_title("Jahresdauerlinie")
        ax.set_xlabel("Jahresstunden")
        ax.set_ylabel("thermische Leistung in kW")
        ax.legend(loc='upper center')
        ax.grid()

        # Hinzufügen von Last_L als Linienplot
        ax1 = self.figure1.gca()  # Get current axis
        print(Last)
        ax1.plot(t, Last, color='blue')  # Zeichnen der Last_L Linie

    def updatePlot(self):
        self.figure1.clear()
        ax = self.figure1.add_subplot(111)
        color_cycle = itertools.cycle(['b', 'g', 'r', 'c', 'm', 'y', 'k'])

        # Gehen Sie alle Optionen im Dropdown-Menü durch und zeichnen Sie nur die ausgewählten
        for i in range(self.dataSelectionDropdown.count()):
            if self.dataSelectionDropdown.itemChecked(i):
                key = self.dataSelectionDropdown.itemText(i)
                data = self.results[key]
                color = next(color_cycle)
                if key == 'Wärmeleistung_L':
                    # Stackplot für Wärmeleistung_L
                    ax.stackplot(self.results['time_steps'], data, labels=self.results['techs'], colors=self.results['colors'])
                else:
                    # Plotten der anderen Daten als Linienplot
                    ax.plot(self.results['time_steps'], data, label=key, color=color)

        ax.set_xlabel("Zeit")
        ax.set_ylabel("Werte")
        ax.legend(loc='upper left')
        ax.grid()
        self.canvas1.draw()

    def updatePieChart(self):
        # Daten für das Kreisdiagramm
        Anteile = self.results['Anteile']
        labels = self.results['techs']
        colors = self.results['colors']
        summe = sum(Anteile)
        if summe < 1:
            # Fügen Sie den fehlenden Anteil hinzu, um die Lücke darzustellen
            Anteile.append(1 - summe)
            labels.append("ungedeckter Bedarf")  # Oder einen anderen passenden Text für den leeren Bereich

        self.pieChartFigure.clear()
        ax = self.pieChartFigure.add_subplot(111)
        ax.pie(Anteile, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax.set_title("Anteile Wärmeerzeugung")
        ax.legend(loc='lower left')
        ax.axis("equal")  # Stellt sicher, dass der Pie-Chart kreisförmig bleibt

        self.pieChartCanvas.draw()

    ### Dropdown Diagramm ###
    def createPlotControlDropdown(self):
        self.dropdownLayout = QHBoxLayout()
        self.dataSelectionDropdown = CheckableComboBox(self)

        # Hier wird angenommen, dass die erste Reihe von Daten standardmäßig geplottet wird.
        initial_checked = True

        # Füllen des Dropdown-Menüs mit Optionen und Setzen des Checkbox-Zustands
        for label in self.results.keys():
            if label.endswith('_L'):
                self.dataSelectionDropdown.addItem(label)
                item = self.dataSelectionDropdown.model().item(self.dataSelectionDropdown.count() - 1, 0)
                # Prüfen, ob es sich um "Wärmeleistung_L" oder "Last_L" handelt und entsprechend markieren
                if label == 'Wärmeleistung_L':
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Checked if initial_checked else Qt.Unchecked)
                    initial_checked = False  # Nur das erste Element wird standardmäßig ausgewählt

        self.dropdownLayout.addWidget(self.dataSelectionDropdown)
        self.mainLayout.addLayout(self.dropdownLayout)

        # Verbindung des Dropdown-Menüs mit der Aktualisierungsfunktion
        self.dataSelectionDropdown.checkedStateChanged.connect(self.updatePlot)