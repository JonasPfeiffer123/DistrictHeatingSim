"""
Filename: cost_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains the CostTab.
"""

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

from districtheatingsim.heat_generators.annuity import annuität
from districtheatingsim.gui.MixDesignTab.utilities import CollapsibleHeader

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
        self.updateDefaultPath(self.data_manager.variant_folder)
        
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
        # Create the main scroll area with full expansion
        self.createMainScrollArea()

        # Infrastructure Costs Section
        self.infrastructure_widget = QWidget()
        infrastructure_layout = QVBoxLayout(self.infrastructure_widget)
        self.setupInfrastructureCostsTable()
        infrastructure_layout.addWidget(self.infrastructureCostsTable)
        self.infrastructure_section = CollapsibleHeader("Kosten Wärmenetzinfrastruktur", self.infrastructure_widget)
        
        # Technology Costs Section
        self.tech_widget = QWidget()
        tech_layout = QVBoxLayout(self.tech_widget)
        self.setupTechDataTable()
        tech_layout.addWidget(self.techDataTable)
        self.tech_section = CollapsibleHeader("Kosten Erzeuger", self.tech_widget)

        # Cost Composition Section
        self.cost_composition_widget = QWidget()
        cost_composition_layout = QVBoxLayout(self.cost_composition_widget)
        self.setupCostCompositionChart()
        cost_composition_layout.addWidget(self.bar_chart_canvas)  # Add bar chart
        cost_composition_layout.addWidget(self.pie_chart_canvas)  # Add pie chart
        self.cost_composition_section = CollapsibleHeader("Kostenzusammensetzung", self.cost_composition_widget)

        # Add all sections to the main layout with stretch factors
        self.mainLayout.addWidget(self.infrastructure_section, 1)
        self.mainLayout.addWidget(self.tech_section, 1)
        self.mainLayout.addWidget(self.cost_composition_section, 2)

        # Initialize and style total cost label as QLabel
        self.totalCostLabel = QLabel("Gesamtkosten: 0 €")
        self.totalCostLabel.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        self.mainLayout.addWidget(self.totalCostLabel, alignment=Qt.AlignLeft)

        # Set the main layout to use all available space in the scroll area
        self.mainScrollArea.setWidget(self.mainWidget)
        self.mainLayout.setContentsMargins(10, 10, 10, 10)  # Adjust margins if needed

        # Set the layout for the entire CostTab widget
        self.setLayout(self.createMainLayout())

    def createMainScrollArea(self):
        """
        Creates the main scroll area for the tab and sets it to take full width and height.
        """
        self.mainScrollArea = QScrollArea(self)
        self.mainScrollArea.setWidgetResizable(True)
        self.mainWidget = QWidget()
        self.mainLayout = QVBoxLayout(self.mainWidget)
        self.mainScrollArea.setWidget(self.mainWidget)
        self.mainScrollArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def createMainLayout(self):
        """
        Creates the main layout for the tab with adjusted spacing and margins for better alignment.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)  # Set uniform margins for the tab
        layout.setSpacing(10)  # Adjust spacing between sections

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
        self.infrastructureCostsTable = QTableWidget()
        self.infrastructureCostsTable.setColumnCount(7)
        self.infrastructureCostsTable.setHorizontalHeaderLabels(
            ['Beschreibung', 'Kosten', 'T_N', 'f_Inst', 'f_W_Insp', 'Bedienaufwand', 'Annuität']
        )
        self.infrastructureCostsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.infrastructureCostsTable.setAlternatingRowColors(True)

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

                # Apply formatting with units
                if col == 'Kosten' and value != "":
                    formatted_value = self.format_cost(float(value))
                elif col == 'T_N' and value != "":
                    formatted_value = f"{value} a"  # Append 'a' for years
                elif col in ['f_Inst', 'f_W_Insp'] and value != "":
                    formatted_value = f"{value} %"  # Convert to percentage and add '%'
                elif col == 'Bedienaufwand' and value != "":
                    formatted_value = f"{value} h"  # Append 'h' for hours
                elif col == 'Gesamtannuität' and value != "":
                    formatted_value = self.format_cost(float(value))
                else:
                    formatted_value = str(value)
                
                self.infrastructureCostsTable.setItem(i, j, QTableWidgetItem(formatted_value))

            # Calculate annuity and format it
            A0 = float(values.get(f"{obj}_kosten", 0))
            TN = int(values.get(f"{obj}_t_n", 0))
            f_Inst = float(values.get(f"{obj}_f_inst", 0))
            f_W_Insp = float(values.get(f"{obj}_f_w_insp", 0))
            Bedienaufwand = float(values.get(f"{obj}_bedienaufwand", 0))
            annuität = self.calc_annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand)
            
            # Set formatted annuity in the table
            self.infrastructureCostsTable.setItem(i, 6, QTableWidgetItem(self.format_cost(annuität)))
            
            # Update total investment and annuity sums
            self.summe_investitionskosten += A0
            self.summe_annuität += annuität
            self.individual_costs.append((obj.capitalize(), A0))

        self.addSummaryRow()

    def format_cost(self, value):
        """
        Formats the cost value in European style with spaces as thousand separators.

        Args:
            value (float): The cost value.

        Returns:
            str: Formatted cost string.
        """
        return f"{value:,.0f} €".replace(",", " ")


    def addSummaryRow(self):
        """
        Adds a summary row to the infrastructure costs table with bold formatting.
        """
        summen_row_index = self.infrastructureCostsTable.rowCount()
        self.infrastructureCostsTable.insertRow(summen_row_index)

        boldFont = QFont()
        boldFont.setBold(True)

        summen_beschreibung_item = QTableWidgetItem("Summe Infrastruktur")
        summen_beschreibung_item.setFont(boldFont)
        self.infrastructureCostsTable.setItem(summen_row_index, 0, summen_beschreibung_item)

        formatted_cost = self.format_cost(self.summe_investitionskosten)
        summen_kosten_item = QTableWidgetItem(formatted_cost)
        summen_kosten_item.setFont(boldFont)
        self.infrastructureCostsTable.setItem(summen_row_index, 1, summen_kosten_item)

        formatted_annuität = self.format_cost(self.summe_annuität)
        summen_annuität_item = QTableWidgetItem(formatted_annuität)
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
        q = 1 + (self.parent.capital_interest_rate / 100)
        r = 1 + (self.parent.inflation_rate / 100)
        t = int(self.parent.time_period)
        stundensatz = self.parent.hourly_rate
        return annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand, q=q, r=r, T=t, stundensatz=stundensatz)
    
    ### Setup of Calculation Result Tables ###
    def setupTechDataTable(self):
        self.techDataTable = QTableWidget()
        self.techDataTable.setColumnCount(4)
        self.techDataTable.setHorizontalHeaderLabels(['Name', 'Dimensionen', 'Kosten', 'Gesamtkosten'])
        self.techDataTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.techDataTable.setAlternatingRowColors(True)

    def updateTechDataTable(self, tech_objects):
        """
        Updates the technology data table with the given technology objects.

        Args:
            tech_objects (list): List of technology objects.
        """
        self.techDataTable.setRowCount(len(tech_objects))

        self.summe_tech_kosten = 0

        for i, tech in enumerate(tech_objects):
            name, dimensions, costs, full_costs = tech.extract_tech_data()
            self.techDataTable.setItem(i, 0, QTableWidgetItem(name))
            self.techDataTable.setItem(i, 1, QTableWidgetItem(dimensions))
            self.techDataTable.setItem(i, 2, QTableWidgetItem(costs))
            self.techDataTable.setItem(i, 3, QTableWidgetItem(self.format_cost(float(full_costs))))
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

        formatted_cost = self.format_cost(self.summe_tech_kosten)
        summen_kosten_item = QTableWidgetItem(formatted_cost)
        summen_kosten_item.setFont(boldFont)
        self.techDataTable.setItem(summen_row_index, 3, summen_kosten_item)

        self.techDataTable.resizeColumnsToContents()
        self.adjustTableSize(self.techDataTable)

    def updateSumLabel(self):
        """
        Updates the label displaying the total costs.
        """
        total_cost = self.summe_investitionskosten + self.summe_tech_kosten
        formatted_total_cost = self.format_cost(total_cost)
        self.totalCostLabel.setText(f"Gesamtkosten: {formatted_total_cost}")
    
    ### Setup of Cost Composition Chart ###
    def setupCostCompositionChart(self):
        """
        Sets up two separate figures for the bar chart and pie chart.
        """
        # Create bar chart figure and canvas
        self.bar_chart_figure, self.bar_chart_canvas = self.addFigure()
        self.bar_chart_canvas.setMinimumHeight(400)

        # Create pie chart figure and canvas
        self.pie_chart_figure, self.pie_chart_canvas = self.addFigure()
        self.pie_chart_canvas.setMinimumHeight(400)

    def addFigure(self):
        """
        Creates and returns a new figure and its canvas.

        Returns:
            tuple: The figure and canvas.
        """
        figure = Figure(figsize=(8, 6))
        canvas = FigureCanvas(figure)
        return figure, canvas
    
    def plotCostComposition(self):
        """
        Plots the cost composition with two separate figures: a bar chart and a pie chart.
        """
        # Data for the charts
        labels = [cost[0] for cost in self.individual_costs]
        sizes = [cost[1] for cost in self.individual_costs]

        ### Bar Chart
        self.bar_chart_figure.clear()
        ax1 = self.bar_chart_figure.add_subplot(111)  # Full plot for bar chart
        bar_colors = ax1.barh(labels, sizes, height=0.5)  # Bar chart with default colors
        ax1.set_title('Kostenzusammensetzung (Absolut in €)')
        ax1.set_xlabel('Kosten (€)')
        ax1.set_ylabel('Komponenten')

        # Display exact cost values next to each bar
        for i, (size, label) in enumerate(zip(sizes, labels)):
            formatted_size = self.format_cost(size)
            ax1.text(size, i, formatted_size, va='center')

        ### Pie Chart
        self.pie_chart_figure.clear()
        ax2 = self.pie_chart_figure.add_subplot(111)  # Full plot for pie chart
        wedges, _, _ = ax2.pie(
            sizes,
            labels=None,
            autopct='%1.1f%%',
            startangle=140,
            explode=[0.1 if label == "Wärmenetz" else 0 for label in labels],
            labeldistance=1.1,
            pctdistance=0.85
        )
        # Extract colors from pie chart for consistency
        pie_colors = [wedge.get_facecolor() for wedge in wedges]
        ax2.set_title('Kostenzusammensetzung (Relativ in %)')
        ax2.legend(labels, loc="best", bbox_to_anchor=(1, 0.5))

        # Apply consistent colors to the bar chart
        for bar, color in zip(bar_colors, pie_colors):
            bar.set_color(color)

        # Draw both charts
        self.bar_chart_canvas.draw()
        self.pie_chart_canvas.draw()

    def adjustTableSize(self, table):
        """
        Adjusts the size of the table to fit its contents.

        Args:
            table (QTableWidget): The table to adjust.
        """
        header_height = table.horizontalHeader().height()
        rows_height = sum([table.rowHeight(i) for i in range(table.rowCount())])
        table.setFixedHeight(header_height + rows_height)

    def totalCostLabel(self):
        """
        Returns the total cost label.
        """
        # Create the total cost label
        self.totalCostLabel = QLabel()
