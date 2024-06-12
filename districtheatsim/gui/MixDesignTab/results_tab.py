import itertools
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal

from heat_generators.heat_generator_classes import *

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
        
        self.initUI()

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)

        # Diagramme und Tabellen in ScrollArea packen
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollWidget = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollWidget)

        self.setupDiagrams()
        self.setupCalculationOptimization()

        self.scrollArea.setWidget(self.scrollWidget)
        self.mainLayout.addWidget(self.scrollArea)
        self.setLayout(self.mainLayout)

    ### Setup der Berechnungsergebnistabellen ###
    def setupCalculationOptimization(self):
        self.addLabel('Übersicht Erzeugung')

        # Layout für Ergebnisse und Kreisdiagramm
        self.resultsAndPieChartLayout = QHBoxLayout()
        self.scrollLayout.addLayout(self.resultsAndPieChartLayout)
        
        self.setupResultsTable()

        self.addLabel('Ergebnisse Wirtschaftlichkeit')
        self.setupAdditionalResultsTable()

    def addLabel(self, text):
        label = QLabel(text)
        self.scrollLayout.addWidget(label)

    ### Results Table ###
    def setupResultsTable(self):
        self.resultsTable = QTableWidget()
        self.resultsTable.setColumnCount(4)
        self.resultsTable.setHorizontalHeaderLabels(['Technologie', 'Wärmemenge (MWh)', 'Kosten (€/MWh)', 'Anteil (%)'])
        self.resultsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.resultsAndPieChartLayout.addWidget(self.resultsTable)

    def showResultsInTable(self, results):
        self.resultsTable.setRowCount(len(results['techs']))

        for i, (tech, wärmemenge, wgk, anteil) in enumerate(zip(results['techs'], results['Wärmemengen'], results['WGK'], results['Anteile'])):
            self.resultsTable.setItem(i, 0, QTableWidgetItem(tech))
            self.resultsTable.setItem(i, 1, QTableWidgetItem(f"{wärmemenge:.2f}"))
            self.resultsTable.setItem(i, 2, QTableWidgetItem(f"{wgk:.2f}"))
            self.resultsTable.setItem(i, 3, QTableWidgetItem(f"{anteil*100:.2f}%"))

        self.resultsTable.resizeColumnsToContents()
        self.adjustTableSize(self.resultsTable)

    ### Additional Results Table ###
    def setupAdditionalResultsTable(self):
        self.additionalResultsTable = QTableWidget()
        self.additionalResultsTable.setColumnCount(3)
        self.additionalResultsTable.setHorizontalHeaderLabels(['Ergebnis', 'Wert', 'Einheit'])
        self.additionalResultsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.scrollLayout.addWidget(self.additionalResultsTable)

    def showAdditionalResultsTable(self, result):
        self.results = result
        self.WGK_Infra = self.parent.costTab.summe_annuität / self.results['Jahreswärmebedarf']
        self.WGK_Gesamt = self.results['WGK_Gesamt'] + self.WGK_Infra

        data = [
            ("Jahreswärmebedarf", round(self.results['Jahreswärmebedarf'], 1), "MWh"),
            ("Stromerzeugung", round(self.results['Strommenge'], 2), "MWh"),
            ("Strombedarf", round(self.results['Strombedarf'], 2), "MWh"),
            ("Wärmegestehungskosten Erzeugeranlagen", round(self.results['WGK_Gesamt'], 2), "€/MWh"),
            ("Wärmegestehungskosten Netzinfrastruktur", round(self.WGK_Infra, 2), "€/MWh"),
            ("Wärmegestehungskosten Gesamt", round(self.WGK_Gesamt, 2), "€/MWh")
        ]

        self.additionalResultsTable.setRowCount(len(data))

        for i, (description, value, unit) in enumerate(data):
            self.additionalResultsTable.setItem(i, 0, QTableWidgetItem(description))
            self.additionalResultsTable.setItem(i, 1, QTableWidgetItem(str(value)))
            self.additionalResultsTable.setItem(i, 2, QTableWidgetItem(unit))

        self.additionalResultsTable.resizeColumnsToContents()
        self.adjustTableSize(self.additionalResultsTable)

    ### Table size adjustment function ###
    def adjustTableSize(self, table):
        header_height = table.horizontalHeader().height()
        rows_height = sum([table.rowHeight(i) for i in range(table.rowCount())])
        table.setFixedHeight(header_height + rows_height)

    ### Setup Diagramm-Plots ###
    def setupDiagrams(self):
        self.figure1 = Figure(figsize=(8, 6))
        self.canvas1 = FigureCanvas(self.figure1)
        self.canvas1.setMinimumSize(500, 500)
        self.scrollLayout.addWidget(self.canvas1)

        self.pieChartFigure = Figure(figsize=(6, 6))
        self.pieChartCanvas = FigureCanvas(self.pieChartFigure)
        self.pieChartCanvas.setMinimumSize(500, 500)
        self.scrollLayout.addWidget(self.pieChartCanvas)

    ### Plotten der Ergebnisse ###
    def plotResults(self, results):
        self.results = results

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
        ax.plot(t, Last, color='blue', label='Last')
        ax.legend()

    def updatePieChart(self):
        Anteile = self.results['Anteile']
        labels = self.results['techs']
        colors = self.results['colors']
        summe = sum(Anteile)
        if round(summe, 5) < 1:
            Anteile.append(1 - summe)
            labels.append("ungedeckter Bedarf")
            colors.append("black")

        self.pieChartFigure.clear()
        ax = self.pieChartFigure.add_subplot(111)
        wedges, texts, autotexts = ax.pie(
            Anteile, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, pctdistance=0.85
        )

        # Linienführung aktivieren
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_fontsize(10)
            autotext.set_color('black')
            autotext.set_weight('bold')

        ax.set_title("Anteile Wärmeerzeugung")
        ax.legend(loc='lower left')
        ax.axis("equal")

        self.pieChartCanvas.draw()