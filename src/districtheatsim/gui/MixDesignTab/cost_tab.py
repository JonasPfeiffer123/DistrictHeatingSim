"""
Filename: cost_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
Description: Contains the CostTab.
"""

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont

from heat_generators.heat_generator_classes import *

class CostTab(QWidget):
    """
    The CostTab class represents the tab responsible for displaying and managing cost-related data 
    for the different components in a heat generation project.

    Attributes:
        data_added (pyqtSignal): Signal emitted when new data is added.
        data_manager (object): Reference to the data manager instance.
        parent (QWidget): Reference to the parent widget.
        results (dict): Stores results data.
        tech_objects (list): List of technology objects.
        individual_costs (list): List of individual costs for each component.
        summe_tech_kosten (float): Sum of the technology costs.
        base_path (str): Base path for the project.
        summe_investitionskosten (float): Sum of the investment costs.
        summe_annuität (float): Sum of the annuities.
        totalCostLabel (QLabel): Label to display total costs.
    """
    data_added = pyqtSignal(object)  # Signal that transfers data as an object
    
    def __init__(self, data_manager, parent=None):
        """
        Initializes the CostTab instance.

        Args:
            data_manager (object): Reference to the data manager instance.
            parent (QWidget, optional): Reference to the parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent
        self.results = {}
        self.tech_objects = []
        self.individual_costs = []
        self.summe_tech_kosten = 0  # Initialize the variable

        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)
        
        self.initUI()

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default path for the project.

        Args:
            new_base_path (str): The new base path for the project.
        """
        self.base_path = new_base_path

    def initUI(self):
        """
        Initializes the user interface components for the CostTab.
        """
        self.createMainScrollArea()
        self.setupInfrastructureCostsTable()
        self.setupCalculationOptimization()
        self.setupCostCompositionChart()
        self.setLayout(self.createMainLayout())
        
        # Create the total cost label
        self.totalCostLabel = QLabel()
        self.mainLayout.addWidget(self.totalCostLabel)

    def createMainScrollArea(self):
        """
        Creates the main scroll area for the tab.
        """
        self.mainScrollArea = QScrollArea(self)
        self.mainScrollArea.setWidgetResizable(True)
        self.mainWidget = QWidget()
        self.mainLayout = QVBoxLayout(self.mainWidget)
        self.mainScrollArea.setWidget(self.mainWidget)

    def createMainLayout(self):
        """
        Creates the main layout for the tab.

        Returns:
            QVBoxLayout: The main layout for the tab.
        """
        layout = QVBoxLayout(self)
        layout.addWidget(self.mainScrollArea)
        return layout

    def addLabel(self, text):
        """
        Adds a label to the main layout.

        Args:
            text (str): The text for the label.
        """
        label = QLabel(text)
        self.mainLayout.addWidget(label)
    
    ### Infrastructure Tables ###
    def setupInfrastructureCostsTable(self):
        """
        Sets up the infrastructure costs table.
        """
        self.addLabel('Wärmenetzinfrastruktur')
        self.infrastructureCostsTable = QTableWidget()
        self.infrastructureCostsTable.setColumnCount(7)  # An additional column for annuity
        self.infrastructureCostsTable.setHorizontalHeaderLabels(['Beschreibung', 'Kosten', 'T_N', 'f_Inst', 'f_W_Insp', 'Bedienaufwand', 'Annuität'])
        self.infrastructureCostsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mainLayout.addWidget(self.infrastructureCostsTable)

    def updateInfrastructureTable(self):
        """
        Updates the infrastructure costs table with data from the parent dialog.
        """
        values = self.parent.netInfrastructureDialog.getValues()
        infraObjects = self.parent.netInfrastructureDialog.getCurrentInfraObjects()
        columns = ['Beschreibung', 'Kosten', 'T_N', 'f_Inst', 'f_W_Insp', 'Bedienaufwand', 'Gesamtannuität']

        self.infrastructureCostsTable.setRowCount(len(infraObjects))
        self.infrastructureCostsTable.setColumnCount(len(columns))
        self.infrastructureCostsTable.setHorizontalHeaderLabels(columns)

        self.summe_investitionskosten = 0
        self.summe_annuität = 0
        self.individual_costs = []

        for i, obj in enumerate(infraObjects):
            self.infrastructureCostsTable.setItem(i, 0, QTableWidgetItem(obj.capitalize()))
            for j, col in enumerate(columns[1:], 1):
                key = f"{obj}_{col.lower()}"
                value = values.get(key, "")
                self.infrastructureCostsTable.setItem(i, j, QTableWidgetItem(str(value)))

            A0 = float(values.get(f"{obj}_kosten", 0))
            TN = int(values.get(f"{obj}_t_n", 0))
            f_Inst = float(values.get(f"{obj}_f_inst", 0))
            f_W_Insp = float(values.get(f"{obj}_f_w_insp", 0))
            Bedienaufwand = float(values.get(f"{obj}_bedienaufwand", 0))
            annuität = self.calc_annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand)
            self.infrastructureCostsTable.setItem(i, 6, QTableWidgetItem(f"{annuität:.1f}"))
            
            self.summe_investitionskosten += A0
            self.summe_annuität += annuität
            self.individual_costs.append((obj.capitalize(), A0))

        self.addSummaryRow()

    def addSummaryRow(self):
        """
        Adds a summary row to the infrastructure costs table.
        """
        summen_row_index = self.infrastructureCostsTable.rowCount()
        self.infrastructureCostsTable.insertRow(summen_row_index)

        boldFont = QFont()
        boldFont.setBold(True)

        summen_beschreibung_item = QTableWidgetItem("Summe Infrastruktur")
        summen_beschreibung_item.setFont(boldFont)
        self.infrastructureCostsTable.setItem(summen_row_index, 0, summen_beschreibung_item)

        summen_kosten_item = QTableWidgetItem(f"{self.summe_investitionskosten:.0f}")
        summen_kosten_item.setFont(boldFont)
        self.infrastructureCostsTable.setItem(summen_row_index, 1, summen_kosten_item)

        summen_annuität_item = QTableWidgetItem(f"{self.summe_annuität:.0f}")
        summen_annuität_item.setFont(boldFont)
        self.infrastructureCostsTable.setItem(summen_row_index, 6, summen_annuität_item)

        self.infrastructureCostsTable.resizeColumnsToContents()
        self.adjustTableSize(self.infrastructureCostsTable)

    def calc_annuität(self, A0, TN, f_Inst, f_W_Insp, Bedienaufwand):
        """
        Calculates the annuity for a given set of parameters.

        Args:
            A0 (float): Initial investment cost.
            TN (int): Lifetime of the investment.
            f_Inst (float): Installation factor.
            f_W_Insp (float): Maintenance and inspection factor.
            Bedienaufwand (float): Operating effort.

        Returns:
            float: The calculated annuity.
        """
        q = 1 + (self.parent.kapitalzins / 100)
        r = 1 + (self.parent.preissteigerungsrate / 100)
        t = int(self.parent.betrachtungszeitraum)
        stundensatz = self.parent.stundensatz
        return annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand, q=q, r=r, T=t, stundensatz=stundensatz)
    
    ### Setup of Calculation Result Tables ###
    def setupCalculationOptimization(self):
        """
        Sets up the calculation optimization table.
        """
        self.addLabel('Kosten Erzeuger')
        self.setupTechDataTable()

    def setupTechDataTable(self):
        """
        Sets up the technology data table.
        """
        self.techDataTable = QTableWidget()
        self.techDataTable.setColumnCount(4)
        self.techDataTable.setHorizontalHeaderLabels(['Name', 'Dimensionen', 'Kosten', 'Gesamtkosten'])
        self.techDataTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mainLayout.addWidget(self.techDataTable)

    def updateTechDataTable(self, tech_objects):
        """
        Updates the technology data table with the given technology objects.

        Args:
            tech_objects (list): List of technology objects.
        """
        self.techDataTable.setRowCount(len(tech_objects))

        self.summe_tech_kosten = 0

        for i, tech in enumerate(tech_objects):
            name, dimensions, costs, full_costs = self.extractTechData(tech)
            self.techDataTable.setItem(i, 0, QTableWidgetItem(name))
            self.techDataTable.setItem(i, 1, QTableWidgetItem(dimensions))
            self.techDataTable.setItem(i, 2, QTableWidgetItem(costs))
            self.techDataTable.setItem(i, 3, QTableWidgetItem(full_costs))
            self.summe_tech_kosten += float(full_costs)
            self.individual_costs.append((name, float(full_costs)))

        self.techDataTable.resizeColumnsToContents()
        self.adjustTableSize(self.techDataTable)
        self.addSummaryTechCosts()

    def addSummaryTechCosts(self):
        """
        Adds a summary row for the technology costs.
        """
        summen_row_index = self.techDataTable.rowCount()
        self.techDataTable.insertRow(summen_row_index)

        boldFont = QFont()
        boldFont.setBold(True)

        summen_beschreibung_item = QTableWidgetItem("Summe Erzeugerkosten")
        summen_beschreibung_item.setFont(boldFont)
        self.techDataTable.setItem(summen_row_index, 0, summen_beschreibung_item)

        summen_kosten_item = QTableWidgetItem(f"{self.summe_tech_kosten:.0f}")
        summen_kosten_item.setFont(boldFont)
        self.techDataTable.setItem(summen_row_index, 3, summen_kosten_item)

        self.techDataTable.resizeColumnsToContents()
        self.adjustTableSize(self.techDataTable)

    def updateSumLabel(self):
        """
        Updates the label displaying the total costs.
        """
        self.totalCostLabel.setText(f"Gesamtkosten: {self.summe_investitionskosten + self.summe_tech_kosten:.0f} €")

    def extractTechData(self, tech):
        """
        Extracts the data for a given technology object.

        Args:
            tech (object): The technology object.

        Returns:
            tuple: The extracted data (name, dimensions, costs, full costs).
        """
        if isinstance(tech, RiverHeatPump):
            dimensions = f"th. Leistung: {tech.Wärmeleistung_FW_WP} kW"
            costs = f"Investitionskosten Flusswärmenutzung: {tech.spez_Investitionskosten_Flusswasser * tech.Wärmeleistung_FW_WP:.1f}, Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP * tech.Wärmeleistung_FW_WP:.1f}"
            full_costs = f"{tech.spez_Investitionskosten_Flusswasser * tech.Wärmeleistung_FW_WP + tech.spezifische_Investitionskosten_WP * tech.Wärmeleistung_FW_WP:.1f}"

        elif isinstance(tech, AqvaHeat):
            dimensions = f"th. Leistung: {tech.Wärmeleistung_FW_WP} kW"
            costs = f"Investitionskosten Speicher: n/a"
            full_costs = f"-1"

        elif isinstance(tech, WasteHeatPump):
            dimensions = f"Kühlleistung Abwärme: {tech.Kühlleistung_Abwärme} kW, Temperatur Abwärme: {tech.Temperatur_Abwärme} °C, th. Leistung: {tech.max_Wärmeleistung} kW"
            costs = f"Investitionskosten Abwärmenutzung: {tech.spez_Investitionskosten_Abwärme * tech.max_Wärmeleistung:.1f}, Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP * tech.max_Wärmeleistung:.1f}"
            full_costs = f"{tech.spez_Investitionskosten_Abwärme * tech.max_Wärmeleistung + tech.spezifische_Investitionskosten_WP * tech.max_Wärmeleistung:.1f}"

        elif isinstance(tech, Geothermal):
            dimensions = f"Fläche: {tech.Fläche} m², Bohrtiefe: {tech.Bohrtiefe} m, Temperatur Geothermie: {tech.Temperatur_Geothermie} °C, Entzugsleistung: {tech.spez_Entzugsleistung} W/m, th. Leistung: {tech.max_Wärmeleistung} kW"
            costs = f"Investitionskosten Sondenfeld: {tech.Investitionskosten_Sonden:.1f}, Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP * tech.max_Wärmeleistung:.1f}"
            full_costs = f"{tech.Investitionskosten_Sonden + tech.spezifische_Investitionskosten_WP * tech.max_Wärmeleistung:.1f}"

        elif isinstance(tech, CHP):
            dimensions = f"th. Leistung: {tech.th_Leistung_BHKW} kW, el. Leistung: {tech.el_Leistung_Soll} kW"
            costs = f"Investitionskosten: {tech.Investitionskosten:.1f}"
            full_costs = f"{tech.Investitionskosten:.1f}"

        elif isinstance(tech, BiomassBoiler):
            dimensions = f"th. Leistung: {tech.P_BMK} kW, Größe Holzlager: {tech.Größe_Holzlager} t"
            costs = f"Investitionskosten Kessel: {tech.Investitionskosten_Kessel:.1f} €, Investitionskosten Holzlager: {tech.Investitionskosten_Holzlager:.1f} €"
            full_costs = f"{tech.Investitionskosten:.1f}"

        elif isinstance(tech, GasBoiler):
            dimensions = f"th. Leistung: {tech.P_max:.1f} kW"
            costs = f"Investitionskosten: {tech.Investitionskosten:.1f} €"
            full_costs = f"{tech.Investitionskosten:.1f}"
            
        elif isinstance(tech, SolarThermal):
            dimensions = f"Bruttokollektorfläche: {tech.bruttofläche_STA} m², Speichervolumen: {tech.vs} m³, Kollektortyp: {tech.Typ}"
            costs = f"Investitionskosten Speicher: {tech.Investitionskosten_Speicher:.1f} €, Investitionskosten STA: {tech.Investitionskosten_STA:.1f} €"
            full_costs = f"{tech.Investitionskosten:.1f}"

        else:
            dimensions = "N/A"
            costs = "N/A"
            full_costs = "N/A"

        return tech.name, dimensions, costs, full_costs
    
    ### Setup of Cost Composition Chart ###
    def setupCostCompositionChart(self):
        """
        Sets up the cost composition chart.
        """
        self.addLabel('Kostenzusammensetzung')
        self.figure, self.canvas = self.addFigure()
        self.mainLayout.addWidget(self.canvas)

    def addFigure(self):
        """
        Adds a figure to the canvas.

        Returns:
            tuple: The figure and canvas.
        """
        figure = Figure(figsize=(8, 6))
        canvas = FigureCanvas(figure)
        return figure, canvas

    def plotCostComposition(self):
        """
        Plots the cost composition chart.
        """
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        labels = [cost[0] for cost in self.individual_costs]
        sizes = [cost[1] for cost in self.individual_costs]
        colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99','#ff66b3','#c2c2f0','#ffb3e6']

        ax.barh(labels, sizes, color=colors)
        ax.set_title('Kostenzusammensetzung')
        ax.set_xlabel('Kosten (€)')
        ax.set_ylabel('Komponenten')

        self.canvas.draw()

    def adjustTableSize(self, table):
        """
        Adjusts the size of the table to fit its contents.

        Args:
            table (QTableWidget): The table to adjust.
        """
        header_height = table.horizontalHeader().height()
        rows_height = sum([table.rowHeight(i) for i in range(table.rowCount())])
        table.setFixedHeight(header_height + rows_height)
