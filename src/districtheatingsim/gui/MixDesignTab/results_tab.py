"""
Filename: results_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
Description: Contains the ResultsTab.
"""

import sys
import numpy as np

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QScrollArea, QCheckBox, QApplication)
from PyQt5.QtCore import pyqtSignal

from districtheatingsim.gui.MixDesignTab.utilities import CheckableComboBox, CollapsibleHeader

class ResultsTab(QWidget):
    """
    A QWidget subclass representing the ResultsTab.

    Attributes:
        data_added (pyqtSignal): A signal that emits data as an object.
        data_manager (DataManager): An instance of the DataManager class for managing data.
        parent (QWidget): The parent widget.
        results (dict): A dictionary to store results.
        selected_variables (list): A list of selected variables for plotting.
    """
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager, parent=None):
        """
        Initializes the ResultsTab.

        Args:
            data_manager (DataManager): The data manager.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent
        self.results = {}
        self.selected_variables = []

        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.variant_folder)
        
        self.initUI()

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default base path.

        Args:
            new_base_path (str): The new base path.
        """
        self.base_path = new_base_path

    def initUI(self):
        """
        Initializes the UI components of the ResultsTab.
        """
        self.mainLayout = QVBoxLayout(self)

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
        """
        Sets up the collapsible diagrams for the ResultsTab.
        """

        # Layout for variable selection (ComboBox and Checkbox)
        self.variableSelectionLayout = QHBoxLayout()
        self.variableComboBox = CheckableComboBox()
        self.variableComboBox.view().pressed.connect(self.updateSelectedVariables)

        self.secondYAxisCheckBox = QCheckBox("Second y-Axis")
        self.secondYAxisCheckBox.stateChanged.connect(self.updateSelectedVariables)

        self.variableSelectionLayout.addWidget(self.variableComboBox)
        self.variableSelectionLayout.addWidget(self.secondYAxisCheckBox)

        # First Diagram (Stackplot and Line Plot)
        self.figure1 = Figure(figsize=(8, 6))
        self.canvas1 = FigureCanvas(self.figure1)
        self.canvas1.setMinimumSize(500, 500)
        self.diagram1_widget = QWidget()
        diagram1_layout = QVBoxLayout(self.diagram1_widget)
        diagram1_layout.addLayout(self.variableSelectionLayout)  # Add the ComboBox and Checkbox layout
        diagram1_layout.addWidget(self.canvas1)
        self.diagram1_section = CollapsibleHeader("Jahresdauerlinie Diagramm", self.diagram1_widget)
        self.scrollLayout.addWidget(self.diagram1_section)

        # Second Diagram (Pie Chart)
        self.pieChartFigure = Figure(figsize=(6, 6))
        self.pieChartCanvas = FigureCanvas(self.pieChartFigure)
        self.pieChartCanvas.setMinimumSize(500, 500)
        self.diagram2_widget = QWidget()
        diagram2_layout = QVBoxLayout(self.diagram2_widget)
        diagram2_layout.addWidget(self.pieChartCanvas)
        self.diagram2_section = CollapsibleHeader("Anteile Wärmeerzeugung Diagramm", self.diagram2_widget)
        self.scrollLayout.addWidget(self.diagram2_section)

    def setupCalculationOptimization(self):
        """
        Sets up the collapsible calculation optimization section.
        """

        # First Table (Results Table)
        self.setupResultsTable()

        self.table1_widget = QWidget()
        table1_layout = QVBoxLayout(self.table1_widget)
        table1_layout.addWidget(self.resultsTable)
        self.table1_section = CollapsibleHeader("Ergebnisse Erzeugung", self.table1_widget)
        self.scrollLayout.addWidget(self.table1_section)

        # Second Table (Additional Results Table)
        self.setupAdditionalResultsTable()

        self.table2_widget = QWidget()
        table2_layout = QVBoxLayout(self.table2_widget)
        table2_layout.addWidget(self.additionalResultsTable)
        self.table2_section = CollapsibleHeader("Ergebnisse Wirtschaftlichkeit", self.table2_widget)
        self.scrollLayout.addWidget(self.table2_section)

    def addLabel(self, text):
        """
        Adds a label to the layout.

        Args:
            text (str): The text for the label.
        """
        label = QLabel(text)
        self.scrollLayout.addWidget(label)

    def setupResultsTable(self):
        """
        Sets up the results table with additional columns for operational hours and starts.
        """
        self.resultsTable = QTableWidget()
        self.resultsTable.setColumnCount(9)  # Updated to include new columns
        self.resultsTable.setHorizontalHeaderLabels([
            'Technologie', 'Wärmemenge (MWh)', 'Anzahl Betriebsstunden', 
            'Anzahl Starts', 'Betriebsstunden/Start', 'Kosten (€/MWh)', 
            'Anteil (%)', 'CO2-eq (t_CO2/MWh_th)', 'Primärenergiefaktor'
        ])
        self.resultsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def showResultsInTable(self, results):
        """
        Displays the results in the results table, including calculated operational metrics.
        Args:
            results (dict): The results to display.
        """
        self.resultsTable.setRowCount(len(results['techs']))

        # Iterate over each technology and calculate operational metrics
        for i, (tech, wärmemenge, wgk, anteil, spec_emission, primary_energy, wärmeleistung) in enumerate(
                zip(results['techs'], results['Wärmemengen'], results['WGK'], 
                    results['Anteile'], results['specific_emissions_L'], results['primärenergie_L'], results['Wärmeleistung_L'])):

            # Ensure wärmemenge is treated as a NumPy array for consistency
            if not isinstance(wärmeleistung, (list, np.ndarray)):
                wärmeleistung = [wärmeleistung]  # Convert scalar to list for single value cases
            wärmeleistung = np.array(wärmeleistung)

            # Calculate 'Anzahl Betriebsstunden' (sum of hours with non-zero output)
            betriebsstunden = np.count_nonzero(wärmeleistung)  # Counts all non-zero hours
            # Calculate 'Anzahl Starts' (counts transitions from 0 to > 0)
            starts = np.sum((wärmeleistung[:-1] == 0) & (wärmeleistung[1:] > 0))
            # Calculate 'Betriebsstunden/Start' (average hours per start)
            betriebsstunden_pro_start = betriebsstunden / starts if starts > 0 else 0

            # Populate the table with calculated values
            self.resultsTable.setItem(i, 0, QTableWidgetItem(tech))
            self.resultsTable.setItem(i, 1, QTableWidgetItem(f"{np.sum(wärmemenge):.2f}"))
            self.resultsTable.setItem(i, 2, QTableWidgetItem(f"{betriebsstunden}"))
            self.resultsTable.setItem(i, 3, QTableWidgetItem(f"{starts}"))
            self.resultsTable.setItem(i, 4, QTableWidgetItem(f"{betriebsstunden_pro_start:.2f}"))
            self.resultsTable.setItem(i, 5, QTableWidgetItem(f"{wgk:.2f}"))
            self.resultsTable.setItem(i, 6, QTableWidgetItem(f"{anteil * 100:.2f}"))
            self.resultsTable.setItem(i, 7, QTableWidgetItem(f"{spec_emission:.4f}"))
            self.resultsTable.setItem(i, 8, QTableWidgetItem(f"{primary_energy / np.sum(wärmemenge):.4f}"))

        self.resultsTable.resizeColumnsToContents()
        self.adjustTableSize(self.resultsTable)

    def setupAdditionalResultsTable(self):
        """
        Sets up the additional results table.
        """
        self.additionalResultsTable = QTableWidget()
        self.additionalResultsTable.setColumnCount(3)
        self.additionalResultsTable.setHorizontalHeaderLabels(['Ergebnis', 'Wert', 'Einheit'])
        self.additionalResultsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def showAdditionalResultsTable(self, result):
        """
        Displays the additional results in the additional results table.

        Args:
            result (dict): The results to display.
        """
        self.results = result
        self.waerme_ges_kW, self.strom_wp_kW = np.sum(self.results["waerme_ges_kW"]), np.sum(self.results["strom_wp_kW"])
        self.WGK_Infra = self.parent.costTab.summe_annuität / self.results['Jahreswärmebedarf']
        self.wgk_heat_pump_electricity = ((self.strom_wp_kW/1000) * self.parent.electricity_price) / ((self.strom_wp_kW+self.waerme_ges_kW)/1000)
        self.WGK_Gesamt = self.results['WGK_Gesamt'] + self.WGK_Infra + self.wgk_heat_pump_electricity

        data = [
            ("Jahreswärmebedarf", round(self.results['Jahreswärmebedarf'], 1), "MWh"),
            ("Stromerzeugung", round(self.results['Strommenge'], 2), "MWh"),
            ("Strombedarf", round(self.results['Strombedarf'], 2), "MWh"),
            ("Wärmegestehungskosten Erzeugeranlagen", round(self.results['WGK_Gesamt'], 2), "€/MWh"),
            ("Wärmegestehungskosten Netzinfrastruktur", round(self.WGK_Infra, 2), "€/MWh"),
            ("Wärmegestehungskosten dezentrale Wärmepumpen", round(self.wgk_heat_pump_electricity, 2), "€/MWh"),
            ("Wärmegestehungskosten Gesamt", round(self.WGK_Gesamt, 2), "€/MWh"),
            ("spez. CO2-Emissionen Wärme", round(self.results["specific_emissions_Gesamt"], 4), "t_CO2/MWh_th"),
            ("CO2-Emissionen Wärme", round(self.results["specific_emissions_Gesamt"]*self.results['Jahreswärmebedarf'], 2), "t_CO2"),
            ("Primärenergiefaktor", round(self.results["primärenergiefaktor_Gesamt"], 4), "-")
        ]

        self.additionalResultsTable.setRowCount(len(data))

        for i, (description, value, unit) in enumerate(data):
            self.additionalResultsTable.setItem(i, 0, QTableWidgetItem(description))
            self.additionalResultsTable.setItem(i, 1, QTableWidgetItem(str(value)))
            self.additionalResultsTable.setItem(i, 2, QTableWidgetItem(unit))

        self.additionalResultsTable.resizeColumnsToContents()
        self.adjustTableSize(self.additionalResultsTable)

    def adjustTableSize(self, table):
        """
        Adjusts the size of the table to fit its contents.

        Args:
            table (QTableWidget): The table to adjust.
        """
        header_height = table.horizontalHeader().height()
        rows_height = sum([table.rowHeight(i) for i in range(table.rowCount())])
        table.setFixedHeight(header_height + rows_height)

    def plotResults(self, results):
        """
        Plots the results in the diagrams.

        Args:
            results (dict): The results to plot.
        """
        self.results = results
        time_steps = results['time_steps']

        self.extracted_data = {}
        for tech_class in self.results['tech_classes']:
            for var_name in dir(tech_class):
                var_value = getattr(tech_class, var_name)
                if isinstance(var_value, (list, np.ndarray)) and len(var_value) == len(time_steps):
                    unique_var_name = f"{tech_class.name}_{var_name}"
                    self.extracted_data[unique_var_name] = var_value

        self.variableComboBox.clear()
        self.variableComboBox.addItems(self.extracted_data.keys())
        self.variableComboBox.addItem("Last_L")

        initial_vars = [var_name for var_name in self.extracted_data.keys() if "_Wärmeleistung" in var_name]
        initial_vars.append("Last_L")

        for var in initial_vars:
            self.variableComboBox.setItemChecked(var, True)

        self.selected_variables = self.variableComboBox.checkedItems()

        self.figure1.clear()
        self.plotVariables(self.figure1, time_steps, self.selected_variables)
        self.canvas1.draw()

        self.plotPieChart()

    def plotVariables(self, figure, time_steps, selected_vars):
        """
        Plots the selected variables in the diagram.

        Args:
            figure (Figure): The figure to plot on.
            time_steps (list): The list of time steps.
            selected_vars (list): The list of selected variables.
        """
        ax1 = figure.add_subplot(111)
        stackplot_vars = [var for var in selected_vars if "_Wärmeleistung" in var]
        other_vars = [var for var in selected_vars if var not in stackplot_vars and var != "Last_L"]

        stackplot_data = [self.extracted_data[var] for var in stackplot_vars if var in self.extracted_data]
        if stackplot_data:
            ax1.stackplot(time_steps, stackplot_data, labels=stackplot_vars)

        if "Last_L" in selected_vars:
            ax1.plot(time_steps, self.results["Last_L"], color='blue', label='Last', linewidth=0.5)

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

        if ax2:
            ax1.legend(loc='upper left')
            ax2.legend(loc='upper right')
        else:
            ax1.legend(loc='upper center')

    def updateSelectedVariables(self):
        """
        Updates the selected variables and re-plots the diagram.
        """
        self.selected_variables = self.variableComboBox.checkedItems()
        self.figure1.clear()
        self.plotVariables(self.figure1, self.results['time_steps'], self.selected_variables)
        self.canvas1.draw()

    def plotPieChart(self):
        """
        Plots the pie chart for the energy shares.
        """
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
