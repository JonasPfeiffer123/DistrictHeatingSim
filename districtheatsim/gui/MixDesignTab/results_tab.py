import sys
import itertools
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QScrollArea, QCheckBox, QComboBox, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal
import numpy as np
import matplotlib.pyplot as plt

class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super(CheckableComboBox, self).__init__(parent)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModelColumn(0)
        self.checked_items = []

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
            self.checked_items.remove(item.text())
        else:
            item.setCheckState(Qt.Checked)
            self.checked_items.append(item.text())
        self.updateText()

    def updateText(self):
        if self.checked_items:
            self.setEditText(', '.join(self.checked_items))
        else:
            self.setEditText('')

    def addItem(self, text, data=None):
        super(CheckableComboBox, self).addItem(text, data)
        item = self.model().item(self.count() - 1)
        item.setCheckState(Qt.Unchecked)
        #print(f"Added item: {text} with state Unchecked")

    def addItems(self, texts):
        for text in texts:
            self.addItem(text)

    def setItemChecked(self, text, checked=True):
        index = self.findText(text)
        if index != -1:
            item = self.model().item(index)
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            if checked:
                if text not in self.checked_items:
                    self.checked_items.append(text)
            else:
                if text in self.checked_items:
                    self.checked_items.remove(text)
            self.updateText()

    def clear(self):
        super(CheckableComboBox, self).clear()
        self.checked_items = []

    def checkedItems(self):
        return self.checked_items

class ResultsTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent
        self.results = {}
        self.selected_variables = []

        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)
        
        self.initUI()

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)

        # Dropdown menu for variable selection
        self.variableSelectionLayout = QHBoxLayout()
        self.variableComboBox = CheckableComboBox()
        self.variableComboBox.view().pressed.connect(self.updateSelectedVariables)
        
        #self.stackPlotCheckBox = QCheckBox("Stackplot")
        #self.stackPlotCheckBox.stateChanged.connect(self.updateSelectedVariables)
        
        self.secondYAxisCheckBox = QCheckBox("Second y-Axis")
        self.secondYAxisCheckBox.stateChanged.connect(self.updateSelectedVariables)

        self.variableSelectionLayout.addWidget(self.variableComboBox)
        #self.variableSelectionLayout.addWidget(self.stackPlotCheckBox)
        self.variableSelectionLayout.addWidget(self.secondYAxisCheckBox)

        self.mainLayout.addLayout(self.variableSelectionLayout)

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
        
    def setupDiagrams(self):
        self.figure1 = Figure(figsize=(8, 6))
        self.canvas1 = FigureCanvas(self.figure1)
        self.canvas1.setMinimumSize(500, 500)
        self.scrollLayout.addWidget(self.canvas1)

        self.pieChartFigure = Figure(figsize=(6, 6))
        self.pieChartCanvas = FigureCanvas(self.pieChartFigure)
        self.pieChartCanvas.setMinimumSize(500, 500)
        self.scrollLayout.addWidget(self.pieChartCanvas)

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
        self.waerme_ges_kW, self.strom_wp_kW = np.sum(self.results["waerme_ges_kW"]), np.sum(self.results["strom_wp_kW"])
        self.WGK_Infra = self.parent.costTab.summe_annuität / self.results['Jahreswärmebedarf']
        self.wgk_heat_pump_electricity = ((self.strom_wp_kW/1000) * self.parent.strompreis) / ((self.strom_wp_kW+self.waerme_ges_kW)/1000)
        self.WGK_Gesamt = self.results['WGK_Gesamt'] + self.WGK_Infra + self.wgk_heat_pump_electricity

        data = [
            ("Jahreswärmebedarf", round(self.results['Jahreswärmebedarf'], 1), "MWh"),
            ("Stromerzeugung", round(self.results['Strommenge'], 2), "MWh"),
            ("Strombedarf", round(self.results['Strombedarf'], 2), "MWh"),
            ("Wärmegestehungskosten Erzeugeranlagen", round(self.results['WGK_Gesamt'], 2), "€/MWh"),
            ("Wärmegestehungskosten Netzinfrastruktur", round(self.WGK_Infra, 2), "€/MWh"),
            ("Wärmegestehungskosten dezentrale Wärmepumpen", round(self.wgk_heat_pump_electricity, 2), "€/MWh"),
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

    def plotResults(self, results):
        self.results = results
        time_steps = results['time_steps']  # Array with length of 8760

        # Extract all variables with the same length as time_steps
        self.extracted_data = {}
        for tech_class in self.results['tech_classes']:
            for var_name in dir(tech_class):
                var_value = getattr(tech_class, var_name)
                if isinstance(var_value, (list, np.ndarray)) and len(var_value) == len(time_steps):
                    self.extracted_data[var_name] = var_value

        # Clear combo box from previous call
        self.variableComboBox.clear()
        # Populate the combo box with all variables
        self.variableComboBox.addItems(self.extracted_data.keys())
        self.variableComboBox.addItem("Last_L")
        # Initial plot of variables that start with "Wärmeleistung"
        initial_vars = [var_name for var_name in self.extracted_data.keys() if var_name.startswith("Wärmeleistung")]

        # Add "Last_L" to the initial variables
        initial_vars.append("Last_L")

        # Set initial selections
        for var in initial_vars:
            self.variableComboBox.setItemChecked(var, True)

        # Update selected variables
        self.selected_variables = self.variableComboBox.checkedItems()

        # Initial plot
        self.figure1.clear()
        self.plotVariables(self.figure1, time_steps, self.selected_variables)
        self.canvas1.draw()

        self.plotPieChart()

    def plotVariables(self, figure, time_steps, selected_vars):
        ax1 = figure.add_subplot(111)
        stackplot_vars = [var for var in selected_vars if var.startswith("Wärmeleistung")]
        other_vars = [var for var in selected_vars if var not in stackplot_vars and var != "Last_L"]

        # Plot stackplot variables
        stackplot_data = [self.extracted_data[var] for var in stackplot_vars if var in self.extracted_data]
        if stackplot_data:  # Ensure stackplot_data is not empty
            ax1.stackplot(time_steps, stackplot_data, labels=stackplot_vars)

        # Plot Last_L
        if "Last_L" in selected_vars:
            ax1.plot(time_steps, self.results["Last_L"], color='blue', label='Last', linewidth=0.5)

        # Plot other selected variables
        ax2 = ax1.twinx() if self.secondYAxisCheckBox.isChecked() else None
        for var_name in other_vars:
            if var_name in self.extracted_data:
                var_value = self.extracted_data[var_name]
                target_ax = ax2 if ax2 else ax1
                target_ax.plot(time_steps, var_value, label=var_name)

        ax1.set_title("Jahresdauerlinie")
        ax1.set_xlabel("Jahresstunden")
        ax1.set_ylabel("thermische Leistung in kW")
        ax1.grid()

        # Set legends
        if ax2:
            ax1.legend(loc='upper left')
            ax2.legend(loc='upper right')
        else:
            ax1.legend(loc='upper center')

    def updateSelectedVariables(self):
        # Update selected variables to only include those that still exist in extracted_data
        self.selected_variables = self.variableComboBox.checkedItems()
        self.figure1.clear()
        self.plotVariables(self.figure1, self.results['time_steps'], self.selected_variables)
        self.canvas1.draw()

    def plotPieChart(self):
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    data_manager = None  # Sie müssen hier ein geeignetes Datenmanager-Objekt übergeben
    main = ResultsTab(data_manager)
    main.show()
    sys.exit(app.exec_())
