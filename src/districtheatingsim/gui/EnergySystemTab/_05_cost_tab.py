"""
Cost Tab Module
===============

This module contains the CostTab class, which is responsible for displaying and managing cost-related data for different components in a heat generation project.
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
"""

import pandas as pd

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QHBoxLayout, QPushButton, QLineEdit, QInputDialog, QMenu)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from districtheatingsim.heat_generators.annuity import annuity
from districtheatingsim.gui.EnergySystemTab._10_utilities import CollapsibleHeader
from districtheatingsim.gui.EnergySystemTab._02_energy_system_dialogs import KostenBerechnungDialog

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
    
    def __init__(self, folder_manager, config_manager, parent=None):
        """
        Initializes the CostTab instance.

        Args:
            folder_manager (object): Reference to the folder manager instance.
            parent (QWidget, optional): Reference to the parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.config_manager = config_manager
        self.parent = parent
        self.results = {}
        self.tech_objects = []
        self.individual_costs = []
        self.summe_tech_kosten = 0  # Initialize the variable

        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.variant_folder)

        self.data = self.initData()  # Initialize the DataFrame
        self.initUI()

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default path for the project.

        Args:
            new_base_path (str): The new base path for the project.
        """
        self.base_path = new_base_path

    def initData(self):
        """
        Initializes the data as a pandas DataFrame with an index name and calculates the Annuität.
        """
        # Create the initial DataFrame
        data = pd.DataFrame({
            'Kosten': [2000000, 100000, 20000, 40000, 15000, 500000],
            'T_N': [40, 20, 20, 40, 15, 20],
            'F_inst': [1, 1, 1, 1, 1, 0],
            'F_w_insp': [0, 1, 1, 0, 1, 0],
            'Bedienaufwand': [5, 2, 2, 0, 5, 0]
        }, index=['Wärmenetz', 'Hausanschlussstationen', 'Druckhaltung', 'Hydraulik', 'Elektroinstallation', 'Planungskosten'])
        data.index.name = "Komponente"

        # Calculate Annuität for each row
        data['Annuität'] = data.apply(
            lambda row: self.calc_annuität(
                row['Kosten'], row['T_N'], row['F_inst'], row['F_w_insp'], row['Bedienaufwand']
            ),
            axis=1
        )

        # Create the summary row as a DataFrame
        total_row = pd.DataFrame({
            'Kosten': [data['Kosten'].sum()],
            'T_N': [''],  # No meaningful value for T_N in the summary row
            'F_inst': [''],  # No meaningful value for F_inst in the summary row
            'F_w_insp': [''],  # No meaningful value for F_w_insp in the summary row
            'Bedienaufwand': [''],  # No meaningful value for Bedienaufwand in the summary row
            'Annuität': [data['Annuität'].sum()]
        }, index=['Summe Infrastruktur'])

        # Concatenate the summary row with the original data
        data = pd.concat([data, total_row])

        return data

    def initUI(self):
        """
        Initializes the user interface components for the CostTab.
        """
        # Create the main scroll area with full expansion
        self.createMainScrollArea()

        # Infrastructure Costs Section
        self.setupInfrastructureCostsTable()
        
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
        self.mainLayout.addWidget(self.infrastructure_section, 2)
        self.mainLayout.addWidget(self.tech_section, 2)
        self.mainLayout.addWidget(self.cost_composition_section, 2)

        # Initialize and style total cost label as QLabel
        self.totalCostLabel = QLabel("Gesamtkosten: 0 €")
        self.totalCostLabel.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        self.mainLayout.addWidget(self.totalCostLabel, alignment=Qt.AlignmentFlag.AlignLeft)

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
        self.mainScrollArea.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

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
        """
        Sets up the infrastructure costs table.
        """

        self.infrastructure_widget = QWidget()
        self.infrastructure_section = CollapsibleHeader("Kosten Wärmenetzinfrastruktur", self.infrastructure_widget)
        self.infrastructure_layout = QVBoxLayout(self.infrastructure_widget)

        self.infrastructureCostsTable = QTableWidget()
        self.infrastructureCostsTable.setColumnCount(len(self.data.columns))
        self.infrastructureCostsTable.setRowCount(len(self.data))
        self.infrastructureCostsTable.setHorizontalHeaderLabels(self.data.columns.tolist())
        self.infrastructureCostsTable.setVerticalHeaderLabels(self.data.index.tolist())
        self.infrastructureCostsTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.infrastructureCostsTable.setAlternatingRowColors(True)

        self.updateInfrastructureTable()

        self.infrastructureCostsTable.itemChanged.connect(self.updateDataFromTable)
        self.infrastructureCostsTable.verticalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.infrastructureCostsTable.verticalHeader().customContextMenuRequested.connect(self.openHeaderContextMenu)

        self.infrastructure_layout.addWidget(self.infrastructureCostsTable)

        # Add buttons for row management
        buttonLayout = QHBoxLayout()

        self.addButton = QPushButton("Zeile hinzufügen")
        self.removeButton = QPushButton("Zeile entfernen")
        self.berechneWärmenetzKostenButton = QPushButton("Kosten Wärmenetz aus geoJSON berechnen", self)
        self.berechneHausanschlussKostenButton = QPushButton("Kosten Hausanschlusstationen aus geoJSON berechnen", self)

        self.addButton.clicked.connect(self.addRow)
        self.removeButton.clicked.connect(self.removeRow)
        self.berechneWärmenetzKostenButton.clicked.connect(self.berechneWaermenetzKosten)
        self.berechneHausanschlussKostenButton.clicked.connect(self.berechneHausanschlussKosten)

        buttonLayout.addWidget(self.addButton)
        buttonLayout.addWidget(self.removeButton)
        buttonLayout.addWidget(self.berechneWärmenetzKostenButton)
        buttonLayout.addWidget(self.berechneHausanschlussKostenButton)

        self.infrastructure_layout.addLayout(buttonLayout)

    def updateInfrastructureTable(self):
        """
        Updates the infrastructure costs table with data from the DataFrame.
        Ensures proper formatting and correct handling of indices.
        """
        # Update the table dimensions
        self.infrastructureCostsTable.setRowCount(len(self.data))
        self.infrastructureCostsTable.setColumnCount(len(self.data.columns))
        self.infrastructureCostsTable.setHorizontalHeaderLabels(self.data.columns.tolist())
        self.infrastructureCostsTable.setVerticalHeaderLabels(self.data.index.tolist())  # Update vertical headers

        # Iterate over the DataFrame rows
        self.infrastructureCostsTable.blockSignals(True)
        for row_idx, (index, row) in enumerate(self.data.iterrows()):
            for col_idx, (col_name, value) in enumerate(row.items()):
                # Apply formatting based on column type
                if col_name == 'Kosten' or col_name == 'Annuität':
                    formatted_value = self.format_cost(value) if value != '' else ''
                elif col_name == 'T_N':
                    formatted_value = f"{value} a" if value != '' else ''  # Append 'a' for years
                elif col_name in ['F_inst', 'F_w_insp']:
                    formatted_value = f"{value} %" if value != '' else ''  # Convert to percentage and add '%'
                elif col_name == 'Bedienaufwand':
                    formatted_value = f"{value} h" if value != '' else ''  # Append 'h' for hours
                else:
                    formatted_value = str(value)

                # Ensure the value is set correctly in the table
                self.infrastructureCostsTable.setItem(row_idx, col_idx, QTableWidgetItem(formatted_value))
        self.infrastructureCostsTable.blockSignals(False)

        # Adjust table size and column widths
        self.infrastructureCostsTable.resizeColumnsToContents()
        self.infrastructureCostsTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.adjustTableSize(self.infrastructureCostsTable)

    def format_cost(self, value):
        """
        Formats the cost value in European style with spaces as thousand separators.

        Args:
            value (float): The cost value.

        Returns:
            str: Formatted cost string.
        """
        return f"{value:,.0f} €".replace(",", " ")

    def updateDataFromTable(self, item):
        """
        Updates the DataFrame with values from the QTableWidget and recalculates Annuität.

        Args:
            item (QTableWidgetItem): The changed table item.
        """
        row = item.row()
        col = item.column()
        value = item.text()

        try:
            # Remove unit suffixes before conversion
            value = value.replace("€", "").replace("a", "").replace("%", "").replace("h", "").replace(" ", "").strip()
            # Attempt to convert the stripped value to a float or int
            if '.' in value or 'e' in value.lower():
                self.data.iloc[row, col] = float(value)
            else:
                self.data.iloc[row, col] = int(value)
        except ValueError:
            self.data.iloc[row, col] = value  # Handle non-numeric values gracefully

        # Recalculate Annuität for the updated row
        self.data.at[self.data.index[row], 'Annuität'] = self.calc_annuität(
            float(self.data.at[self.data.index[row], 'Kosten']),
            int(self.data.at[self.data.index[row], 'T_N']),
            float(self.data.at[self.data.index[row], 'F_inst']),
            float(self.data.at[self.data.index[row], 'F_w_insp']),
            float(self.data.at[self.data.index[row], 'Bedienaufwand'])
        )

        # Update the Annuität column in the table
        annuity_value = self.data.at[self.data.index[row], 'Annuität']
        self.infrastructureCostsTable.blockSignals(True)
        self.infrastructureCostsTable.setItem(row, self.data.columns.get_loc('Annuität'), QTableWidgetItem(self.format_cost(annuity_value)))
        self.infrastructureCostsTable.blockSignals(False)
        
        # Recalculate the summary row
        self.updateSummaryRow()

        # Refresh the table to include the updated summary row
        self.updateInfrastructureTable()

    def addRow(self):
        """
        Adds a new row to the table and DataFrame, with default values and calculated Annuität.
        The new row is added above the summary row.
        """
        # Remove the summary row temporarily
        if 'Summe Infrastruktur' in self.data.index:
            self.data = self.data.drop('Summe Infrastruktur')

        # Create a new row with default values
        new_row_name = f"Neues Objekt {len(self.data) + 1}"
        default_values = {
            'Kosten': 0,
            'T_N': 0,
            'F_inst': 0,
            'F_w_insp': 0,
            'Bedienaufwand': 0,
            'Annuität': self.calc_annuität(0, 0, 0, 0, 0)
        }
        new_row = pd.DataFrame(default_values, index=[new_row_name])

        # Insert the new row into the DataFrame
        self.data = pd.concat([self.data, new_row])

        # Recalculate the summary row and ensure it is the last row
        self.updateSummaryRow()

        # Refresh the table
        self.updateInfrastructureTable()

    def removeRow(self):
        """
        Removes the selected row from the table and DataFrame.
        """
        current_row = self.infrastructureCostsTable.currentRow()
        if current_row != -1:
            # Remove the summary row temporarily
            if 'Summe Infrastruktur' in self.data.index:
                self.data = self.data.drop('Summe Infrastruktur')

            # Remove the selected row
            self.data = self.data.drop(self.data.index[current_row])

            # Recalculate the summary row
            self.updateSummaryRow()

            # Refresh the table
            self.updateInfrastructureTable()

    def openHeaderContextMenu(self, position):
        """
        Opens the context menu for the vertical header.

        Args:
            position (QPoint): The position where the context menu should be opened.
        """
        menu = QMenu()
        renameAction = menu.addAction("Umbenennen")
        action = menu.exec_(self.infrastructureCostsTable.verticalHeader().mapToGlobal(position))

        if action == renameAction:
            row = self.infrastructureCostsTable.verticalHeader().logicalIndexAt(position)
            if row != -1:
                self.renameHeader(row)

    def renameHeader(self, row):
        """
        Renames the header item at the specified row.

        Args:
            row (int): The row index of the header item to rename.
        """
        newName, okPressed = QInputDialog.getText(self, "Name ändern", "Neuer Name:", QLineEdit.EchoMode.Normal, "")
        if okPressed and newName:
            old_name = self.data.index[row]
            self.data.rename(index={old_name: newName}, inplace=True)
            self.infrastructureCostsTable.setVerticalHeaderLabels(self.data.index.tolist())

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
        if TN == 0: # Avoid division by zero
            return 0.0
        
        q = float(self.parent.economic_parameters["capital_interest_rate"])
        r = float(self.parent.economic_parameters["inflation_rate"])
        t = int(self.parent.economic_parameters["time_period"])
        stundensatz = self.parent.economic_parameters["hourly_rate"]

        return annuity(A0, TN, f_Inst, f_W_Insp, Bedienaufwand, interest_rate_factor=q, inflation_rate_factor=r, consideration_time_period_years=t, hourly_rate=stundensatz)
    
    def updateSummaryRow(self):
        """
        Recalculates the summary row and appends it to the DataFrame.
        """
        # Remove existing summary row if it exists
        if 'Summe Infrastruktur' in self.data.index:
            self.data = self.data.drop('Summe Infrastruktur')

        # Recalculate the summary row
        total_row = pd.DataFrame({
            'Kosten': [self.data['Kosten'].sum()],
            'T_N': [''],  # No meaningful value for T_N in the summary row
            'F_inst': [''],  # No meaningful value for F_inst in the summary row
            'F_w_insp': [''],  # No meaningful value for F_w_insp in the summary row
            'Bedienaufwand': [''],  # No meaningful value for Bedienaufwand in the summary row
            'Annuität': [self.data['Annuität'].sum()]
        }, index=['Summe Infrastruktur'])

        # Append the summary row to the DataFrame
        self.data = pd.concat([self.data, total_row])
    
    def updateTableValue(self, row, column, value):
        """
        Updates the value in the specified table cell.

        Args:
            row (int): The row index.
            column (int): The column index.
            value (Any): The value to set.
        """
        if 0 <= row < self.infrastructureCostsTable.rowCount() and 0 <= column < self.infrastructureCostsTable.columnCount():
            self.infrastructureCostsTable.setItem(row, column, QTableWidgetItem(self.format_cost(value)))
        else:
            print("Fehler: Ungültiger Zeilen- oder Spaltenindex.")
    
    def berechneWaermenetzKosten(self):
        """
        Opens the dialog to calculate the cost of the heating network and updates the table.
        """
        dialog = KostenBerechnungDialog(self, label="spez. Kosten Wärmenetz pro m_Trasse (inkl. Tiefbau) in €/m", value="1000", type="flow line")
        dialog.setWindowTitle("Kosten Wärmenetz berechnen")
        if dialog.exec():
            cost_net = dialog.total_cost
            self.updateTableValue(row=0, column=0, value=cost_net)

    def berechneHausanschlussKosten(self):
        """
        Opens the dialog to calculate the cost of house connection stations and updates the table.
        """
        dialog = KostenBerechnungDialog(self, label="spez. Kosten Hausanschlussstationen pro kW max. Wärmebedarf in €/kW", value="250", type="HAST")
        dialog.setWindowTitle("Kosten Hausanschlussstationen berechnen")
        if dialog.exec():
            cost_net = dialog.total_cost
            self.updateTableValue(row=1, column=0, value=cost_net)
    
    ### Setup of Calculation Result Tables ###
    def setupTechDataTable(self):
        self.techDataTable = QTableWidget()
        self.techDataTable.setColumnCount(4)
        self.techDataTable.setHorizontalHeaderLabels(['Name', 'Dimensionen', 'Kosten', 'Gesamtkosten'])
        self.techDataTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.techDataTable.setAlternatingRowColors(True)

    def updateTechDataTable(self, tech_objects):
        """
        Updates the technology data table with the given technology objects.

        Args:
            tech_objects (list): List of technology objects.
        """
        self.individual_costs = []  # Reset individual costs
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
        Updates the label displaying the total costs using the summary row from the DataFrame.
        """
        # Extract the total costs from the summary row
        if 'Summe Infrastruktur' in self.data.index:
            total_cost = self.data.at['Summe Infrastruktur', 'Kosten']
        else:
            total_cost = 0  # Fallback if the summary row is missing

        # Format the total cost
        formatted_total_cost = self.format_cost(total_cost)

        # Update the label
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
        Clears the diagrams before replotting.
        """

        # Combine costs from self.data (excluding the summary row) and individual costs
        data_costs = [
            (index, self.data.at[index, 'Kosten'])
            for index in self.data.index
            if index != 'Summe Infrastruktur'  # Exclude the summary row
        ]
        combined_costs = data_costs + self.individual_costs

        # Data for the charts
        labels = [cost[0] for cost in combined_costs]
        sizes = [cost[1] for cost in combined_costs]

        ### Bar Chart
        self.bar_chart_figure.clf()  # Clear the figure before plotting
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
        self.pie_chart_figure.clf()  # Clear the figure before plotting
        ax2 = self.pie_chart_figure.add_subplot(111)  # Full plot for pie chart

        # Calculate percentages for legend
        total = sum(sizes)
        percent_labels = [f"{label} ({size / total * 100:.1f}%)" for label, size in zip(labels, sizes)]

        wedges, _ = ax2.pie(
            sizes,
            labels=None,  # No labels on the pie itself
            autopct=None,  # No percentage labels on the pie
            startangle=140,
            explode=[0.1 if label == "Wärmenetz" else 0 for label in labels],
            labeldistance=1.1,
            pctdistance=0.85
        )
        # Extract colors from pie chart for consistency
        pie_colors = [wedge.get_facecolor() for wedge in wedges]
        ax2.set_title('Kostenzusammensetzung (Relativ in %)')
        ax2.legend(wedges, percent_labels, loc="best", bbox_to_anchor=(1, 0.5))

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
