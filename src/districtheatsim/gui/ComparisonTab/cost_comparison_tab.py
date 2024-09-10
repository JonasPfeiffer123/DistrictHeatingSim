"""
Filename: cost_comparison_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-30
Description: Contains the CostComparisonTab.
"""

import os
import json
import numpy as np
import traceback

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, 
                             QFileDialog, QHBoxLayout, QMessageBox, QHeaderView, QScrollArea, 
                             QGridLayout, QLabel)
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class CostComparisonTab(QWidget):
    def __init__(self, folder_manager, parent=None):
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.folder_paths = []
        self.variant_data = []

        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.project_folder)

        self.initUI()

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

    def initUI(self):
        self.layout = QVBoxLayout(self)

        # Add buttons to load and remove data
        button_layout = QHBoxLayout()

        self.loadButton = QPushButton("Projektdaten laden")
        self.loadButton.clicked.connect(self.addData)
        button_layout.addWidget(self.loadButton)

        self.removeButton = QPushButton("Projektdaten entfernen")
        self.removeButton.clicked.connect(self.removeData)
        button_layout.addWidget(self.removeButton)

        self.layout.addLayout(button_layout)

        # Add a scroll area for dynamic content
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollContent = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollContent)
        self.scrollArea.setWidget(self.scrollContent)
        self.layout.addWidget(self.scrollArea)

        # Create a layout for the tables and pie charts
        self.tableLayout = QVBoxLayout()
        self.scrollLayout.addLayout(self.tableLayout)

        self.pieChartLayout = QGridLayout()
        self.scrollLayout.addLayout(self.pieChartLayout)

        # Set up the additional results table
        self.setupAdditionalResultsTable()

        self.setLayout(self.layout)

    def addData(self):
        # Open a file dialog to select the base path for the data
        folder_path = QFileDialog.getExistingDirectory(self, "Ordner auswählen", self.base_path)

        if folder_path:
            self.folder_paths.append(folder_path)
            data = self.load_variant_data(folder_path)
            if data:
                self.variant_data.append(data)
                self.display_data_in_table()
                self.display_additional_results()
                self.updatePieCharts()

    def removeData(self):
        if self.variant_data:
            self.variant_data.pop()
            self.folder_paths.pop()
            self.display_data_in_table()
            self.updatePieCharts()
            if self.variant_data:
                self.display_additional_results()
            else:
                self.clearAllTables()
        else:
            QMessageBox.warning(self, "Keine Daten", "Keine Daten zum Entfernen vorhanden.")

    def clearAllTables(self):
        """
        Clears all tables and pie charts when no data is available.
        """
        self.tableLayout.takeAt(0).widget().deleteLater()
        self.pieChartLayout.takeAt(0).widget().deleteLater()

    def load_variant_data(self, folder_path):
        try:
            # Load the JSON file
            json_file_path = os.path.join(folder_path, 'results', 'results.json')  # Assuming the results are stored in 'results.json'
            with open(json_file_path, 'r') as json_file:
                data_loaded = json.load(json_file)
            
            results_loaded = data_loaded.get('results', {})

            # Convert lists back to numpy arrays if necessary
            for key, value in results_loaded.items():
                if isinstance(value, list) and not all(isinstance(i, dict) for i in value):
                    results_loaded[key] = np.array(value)

            return self.process_results(results_loaded)
        except Exception as e:
            tb_str = traceback.format_exc()
            QMessageBox.critical(self, "Loading Failed", f"Error loading data for {folder_path}:\n\n{str(e)}\n\nTraceback:\n{tb_str}")
            raise e

    def process_results(self, results):
        """
        Processes the loaded results for comparison.
        """
        try:
            # Handle primärenergiefaktor_Gesamt which can be a float or a list
            primärenergiefaktor_Gesamt = results.get('primärenergiefaktor_Gesamt', 0)
            Wärmemengen = results.get('Wärmemengen', [])

            if isinstance(primärenergiefaktor_Gesamt, (float, int)):
                # If it's a single value, repeat it for each entry in Wärmemengen
                primärenergiefaktor_Gesamt = [primärenergiefaktor_Gesamt] * len(Wärmemengen)
            elif isinstance(primärenergiefaktor_Gesamt, list):
                # Ensure the list is the correct length
                if len(primärenergiefaktor_Gesamt) != len(Wärmemengen):
                    raise ValueError("Mismatch between lengths of 'primärenergiefaktor_Gesamt' and 'Wärmemengen'.")

            processed_results = {
                "techs": results.get('techs', []),
                "Wärmemengen": [round(w, 2) for w in Wärmemengen],
                "WGK": [round(w, 2) for w in results.get('WGK', [])],
                "Anteile": [round(a * 100, 2) for a in results.get('Anteile', [])],
                "colors": results.get('colors', []),
                "specific_emissions_L": [round(e, 4) for e in results.get('specific_emissions_L', [])],
                "primärenergie_L": [round(pe / w, 4) if w else 0 for pe, w in zip(primärenergiefaktor_Gesamt, Wärmemengen)],
                "Jahreswärmebedarf": round(results.get('Jahreswärmebedarf', 0), 1),
                "Strommenge": round(results.get('Strommenge', 0), 2),
                "Strombedarf": round(results.get('Strombedarf', 0), 2),
                "WGK_Gesamt": round(results.get('WGK_Gesamt', 0), 2),
                "specific_emissions_Gesamt": round(results.get("specific_emissions_Gesamt", 0), 4),
                "primärenergiefaktor_Gesamt": round(results.get("primärenergiefaktor_Gesamt", 0), 4),
            }
            return processed_results
        except Exception as e:
            raise ValueError(f"Error processing results: {e}")
        
    def setupAdditionalResultsTable(self):
        """
        Sets up the additional results table.
        """
        self.additionalResultsTable = QTableWidget()
        self.scrollLayout.addWidget(self.additionalResultsTable)

    def display_data_in_table(self):
        try:
            # Clear previous tables
            for i in reversed(range(self.tableLayout.count())):
                widget_to_remove = self.tableLayout.itemAt(i).widget()
                if widget_to_remove is not None:
                    widget_to_remove.setParent(None)

            headers = ["Metric"] + [os.path.basename(folder_path) for folder_path in self.folder_paths]
            if self.variant_data:
                metrics = list(self.variant_data[0].keys())
                num_rows = sum(len(self.variant_data[0][metric]) if isinstance(self.variant_data[0][metric], list) else 1 
                            for metric in metrics if metric != 'techs')

                table = QTableWidget()
                table.setColumnCount(len(headers))
                table.setHorizontalHeaderLabels(headers)
                table.setRowCount(num_rows)

                row = 0
                for metric in metrics:
                    if metric == 'techs':  # Skip 'techs' since it is used for labels
                        continue
                    values = self.variant_data[0][metric]
                    if isinstance(values, list):
                        for i in range(len(values)):
                            table.setItem(row, 0, QTableWidgetItem(f"{metric} - {self.variant_data[0]['techs'][i]}"))
                            for col, data in enumerate(self.variant_data):
                                try:
                                    value = data[metric][i]
                                    table.setItem(row, col + 1, QTableWidgetItem(str(value)))
                                except IndexError:
                                    QMessageBox.warning(self, "Datenfehler", 
                                        f"Fehler beim Zugriff auf die Daten für {headers[col + 1]}.\n"
                                        f"Der Index {i} ist für den Wert '{metric}' außerhalb des gültigen Bereichs.")
                                    return
                            row += 1
                    else:  # Handle single float/int values
                        table.setItem(row, 0, QTableWidgetItem(metric))
                        for col, data in enumerate(self.variant_data):
                            table.setItem(row, col + 1, QTableWidgetItem(str(values)))
                        row += 1

                table.resizeColumnsToContents()
                self.tableLayout.addWidget(table)
        except Exception as e:
            tb_str = traceback.format_exc()
            QMessageBox.critical(self, "Fehler bei der Anzeige", 
                f"Ein unerwarteter Fehler ist aufgetreten:\n\n{str(e)}\n\nTraceback:\n{tb_str}")

    def display_additional_results(self):
        try:
            # Clear the table first
            self.additionalResultsTable.clear()

            # Define headers dynamically based on the number of datasets
            headers = ["Ergebnis"] + [os.path.basename(path) for path in self.folder_paths]
            self.additionalResultsTable.setColumnCount(len(headers))
            self.additionalResultsTable.setHorizontalHeaderLabels(headers)

            # Prepare a list of results to be displayed
            results_to_display = [
                ("Jahreswärmebedarf (MWh)", "Jahreswärmebedarf"),
                ("Stromerzeugung (MWh)", "Strommenge"),
                ("Strombedarf (MWh)", "Strombedarf"),
                ("Wärmegestehungskosten Erzeugeranlagen (€/MWh)", "WGK_Gesamt"),
                ("Wärmegestehungskosten Netzinfrastruktur (€/MWh)", "WGK_Infra"),
                ("Wärmegestehungskosten dezentrale Wärmepumpen (€/MWh)", "wgk_heat_pump_electricity"),
                ("Wärmegestehungskosten Gesamt (€/MWh)", "WGK_Gesamt"),
                ("spez. CO2-Emissionen Wärme (t_CO2/MWh_th)", "specific_emissions_Gesamt"),
                ("CO2-Emissionen Wärme (t_CO2)", "CO2_Emissionen_Waerme"),
                ("Primärenergiefaktor (-)", "primärenergiefaktor_Gesamt")
            ]

            # Set the number of rows based on the number of results
            self.additionalResultsTable.setRowCount(len(results_to_display))

            # Populate the table with values from each dataset
            for row, (description, key) in enumerate(results_to_display):
                self.additionalResultsTable.setItem(row, 0, QTableWidgetItem(description))
                for col, data in enumerate(self.variant_data):
                    value = data.get(key, "N/A")
                    if isinstance(value, (float, int)):
                        value = f"{value:.2f}"  # Round to 2 decimal places
                    self.additionalResultsTable.setItem(row, col + 1, QTableWidgetItem(str(value)))

            self.additionalResultsTable.resizeColumnsToContents()

        except Exception as e:
            tb_str = traceback.format_exc()
            QMessageBox.critical(self, "Fehler bei der Anzeige der Zusatzdaten", 
                f"Ein unerwarteter Fehler ist aufgetreten:\n\n{str(e)}\n\nTraceback:\n{tb_str}")

    def updatePieCharts(self):
        """
        Updates the pie charts for all loaded variants.
        """
        try:
            # Clear previous pie charts
            for i in reversed(range(self.pieChartLayout.count())):
                widget_to_remove = self.pieChartLayout.itemAt(i).widget()
                if widget_to_remove is not None:
                    widget_to_remove.setParent(None)

            # Create pie charts dynamically based on the loaded variants
            for idx, data in enumerate(self.variant_data):
                pie_chart_widget = self.create_pie_chart_widget(data)
                self.pieChartLayout.addWidget(pie_chart_widget, idx // 2, idx % 2)  # Arrange in 2 columns

        except Exception as e:
            tb_str = traceback.format_exc()
            QMessageBox.critical(self, "Fehler beim Plotten", 
                f"Ein unerwarteter Fehler ist aufgetreten:\n\n{str(e)}\n\nTraceback:\n{tb_str}")

    def create_pie_chart_widget(self, data):
        """
        Creates a QWidget containing a pie chart for the given data.
        """
        pieChartFigure = Figure()
        pieChartCanvas = FigureCanvas(pieChartFigure)

        Anteile = data['Anteile']
        labels = data['techs']
        colors = data['colors']
        summe = sum(Anteile)
        if round(summe, 5) < 100:
            Anteile.append(100 - summe)
            labels.append("ungedeckter Bedarf")
            colors.append("black")

        pieChartFigure.clear()
        ax = pieChartFigure.add_subplot(111)
        wedges, texts, autotexts = ax.pie(
            Anteile, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, pctdistance=0.85
        )

        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_fontsize(10)
            autotext.set_color('black')
            autotext.set_weight('bold')

        # Use a specific, identifiable key from data for comparison
        data_key = data.get('unique_key')  # Replace 'unique_key' with an appropriate key or attribute
        idx = -1

        for i, variant in enumerate(self.variant_data):
            if variant.get('unique_key') == data_key:  # Replace 'unique_key' with the same key used above
                idx = i
                break

        folder_name = os.path.basename(self.folder_paths[idx]) if idx != -1 else "Unknown"

        ax.set_title(f"Anteile Wärmeerzeugung: {folder_name}")

        ax.legend(loc='lower left')
        ax.axis("equal")

        pieChartCanvas.draw()

        # Wrap the canvas in a widget
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(pieChartCanvas)
        widget.setLayout(layout)

        return widget