"""
Filename: building_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-09
Description: Contains the BuildingTab for managing building data and displaying results.
"""

import os
import sys
import json
import pandas as pd

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QMessageBox,
                             QMainWindow, QTableWidget, QTableWidgetItem, QComboBox, 
                             QMenuBar, QAction, QLineEdit, QAbstractScrollArea, QHBoxLayout)
from PyQt5.QtCore import pyqtSignal, Qt

from heat_requirement.heat_requirement_calculation_csv import generate_profiles_from_csv
from gui.utilities import CheckableComboBox, convert_to_serializable

import traceback
import logging

# Konfiguriere das Logging
logging.basicConfig(filename='error_log.txt', level=logging.ERROR)

class BuildingModel:
    """
    The BuildingModel class manages the data for the BuildingTab.

    Attributes:
        base_path (str): The base path for saving/loading files.
        data (pd.DataFrame): The data loaded from a CSV file.
        results (dict): The results from heat demand calculations.
    """

    def __init__(self):
        self.base_path = None
        self.data = None
        self.results = None

    def set_base_path(self, base_path):
        """
        Sets the base path for saving/loading files.

        Args:
            base_path (str): The base path.
        """
        self.base_path = base_path

    def get_base_path(self):
        """
        Gets the base path for saving/loading files.

        Returns:
            str: The base path.
        """
        return self.base_path

    def load_csv(self, file_path):
        """
        Loads data from a CSV file into a DataFrame.

        Args:
            file_path (str): The path to the CSV file.

        Raises:
            Exception: If there is an error loading the CSV file.
        """
        try:
            self.data = pd.read_csv(file_path, delimiter=';', dtype={'Subtyp': str})
        except Exception as e:
            raise Exception(f"Fehler beim Laden der CSV-Datei: {e}")

    def save_csv(self, file_path):
        """
        Saves the DataFrame to a CSV file.

        Args:
            file_path (str): The path to the CSV file.

        Raises:
            Exception: If there is an error saving the CSV file.
        """
        if self.data is not None:
            try:
                self.data.to_csv(file_path, index=False, sep=';')
            except Exception as e:
                raise Exception(f"Fehler beim Speichern der CSV-Datei: {e}")

    def load_json(self, file_path):
        """
        Loads results data from a JSON file.

        Args:
            file_path (str): The path to the JSON file.

        Raises:
            Exception: If there is an error loading the JSON file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                self.results = {k: v for k, v in loaded_data.items() if isinstance(v, dict) and 'wärme' in v}
        except Exception as e:
            raise Exception(f"Fehler beim Laden der JSON-Datei: {e}")

    def save_json(self, file_path, combined_data):
        """
        Saves results data to a JSON file.

        Args:
            file_path (str): The path to the JSON file.
            combined_data (dict): The data to save.

        Raises:
            Exception: If there is an error saving the JSON file.
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=4)
        except Exception as e:
            raise Exception(f"Fehler beim Speichern der Ergebnisse: {e}")

    def calculate_heat_demand(self, data, try_filename):
        """
        Calculates heat demand profiles from the data.

        Args:
            data (pd.DataFrame): The input data for the calculation.
            try_filename (str): The TRY (Test Reference Year) filename for climate data.

        Returns:
            tuple: A tuple containing the calculated profiles.
        """
        yearly_time_steps, total_heat_W, heating_heat_W, warmwater_heat_W, max_heat_requirement_W, supply_temperature_curve, return_temperature_curve, hourly_air_temperatures = generate_profiles_from_csv(data=data, TRY=try_filename, calc_method="Datensatz")

        # not sure if thats the best way to return the data in kW, but it works for now
        return yearly_time_steps, total_heat_W/1000, heating_heat_W/1000, warmwater_heat_W/1000, max_heat_requirement_W/1000, supply_temperature_curve, return_temperature_curve, hourly_air_temperatures

    def get_resource_path(self, relative_path):
        """
        Get the absolute path to the resource, works for development and for PyInstaller.

        Args:
            relative_path (str): The relative path to the resource.

        Returns:
            str: The absolute path to the resource.
        """
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_path, relative_path)

class BuildingPresenter:
    """
    The BuildingPresenter class handles the interaction between the model and the view.

    Args:
        model (BuildingModel): The data model.
        view (BuildingTabView): The view for the BuildingTab.
        data_manager (object): The data manager for the application.
    """

    def __init__(self, model, view, folder_manager, data_manager, config_manager):
        self.model = model
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        # Connect to the data_manager's signal to update the base path
        self.folder_manager.project_folder_changed.connect(self.update_default_path)

        # Connect UI signals to their respective slots
        self.view.load_csv_signal.connect(self.load_csv)
        self.view.save_csv_signal.connect(self.save_csv)
        self.view.calculate_heat_demand_signal.connect(self.calculate_heat_demand)
        self.view.load_json_signal.connect(self.load_json)
        self.view.update_path_signal.connect(self.update_default_path)

        # Handle combobox changes and plotting
        self.view.data_type_combobox.view().pressed.connect(self.on_combobox_selection_changed)
        self.view.building_combobox.view().pressed.connect(self.on_combobox_selection_changed)

        # Initialize the base path
        self.update_default_path(self.folder_manager.variant_folder)

    def update_default_path(self, path):
        """
        Updates the default path for saving files and updates the view.

        Args:
            path (str): The new default path.
        """
        self.model.set_base_path(path)
        self.view.update_output_path(self.model.get_base_path(), self.config_manager.get_relative_path("building_load_profile_path"))

    def load_csv(self, file_path):
        """
        Loads a CSV file into the model and updates the view.

        Args:
            file_path (str): The path to the CSV file.
        """
        try:
            self.model.load_csv(file_path)
            self.view.populate_table(self.model.data)
        except Exception as e:
            self.view.show_error_message("Fehler", str(e))

    def save_csv(self, file_path):
        """
        Saves the current data in the model to a CSV file.

        Args:
            file_path (str): The path to the CSV file.
        """
        try:
            self.model.save_csv(file_path)
            self.view.show_message("Erfolg", f"CSV-Datei wurde in {file_path} gespeichert.")
        except Exception as e:
            self.view.show_error_message("Fehler", str(e))

    def load_json(self, file_path):
        """
        Loads results data from a JSON file and updates the view.

        Args:
            file_path (str): The path to the JSON file.
        """
        try:
            self.model.load_json(file_path)
            self.view.populate_building_combobox(self.model.results)
            self.view.plot(self.model.results)
        except Exception as e:
            self.view.show_error_message("Fehler", str(e))

    def calculate_heat_demand(self, output_path):
        """
        Calculates heat demand profiles and saves the results to a JSON file.

        Args:
            output_path (str): The path to the output JSON file.
        """
        data = self.view.get_table_data()
        if data.empty:
            self.view.show_error_message("Fehler", "Die Tabelle enthält keine Daten.")
            return

        try:
            try_filename = self.data_manager.get_try_filename()
            results = self.model.calculate_heat_demand(data, try_filename) # returns yearly_time_steps, total_heat_W, heating_heat_W, warmwater_heat_W, max_heat_requirement_W, supply_temperature_curve, return_temperature_curve, hourly_air_temperatures
            self.model.results = self.format_results(results, data)
            combined_data = self.combine_data_with_results(data, self.model.results)
            self.model.save_json(output_path, combined_data)
            self.view.show_message("Erfolg", f"Ergebnisse wurden in {output_path} gespeichert.")
            self.view.populate_building_combobox(self.model.results)
            self.view.plot(self.model.results)
        except Exception as e:
            # Erfasse den vollständigen Traceback
            tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            # Logge den Fehler in eine Datei
            logging.error(f"Ein Fehler ist aufgetreten:\n{tb_str}")
            # Zeige die Fehlermeldung mit dem vollständigen Traceback
            self.view.show_error_message("Fehler", f"Es ist ein Fehler aufgetreten: {str(e)}\n\nDetails:\n{tb_str}")

    def format_results(self, results, data):
        """
        Formats the calculated results for saving to JSON.

        Args:
            results (tuple): The calculated profiles.
            data (pd.DataFrame): The input data.

        Returns:
            dict: The formatted results.
        """
        formatted_results = {}
        for idx in range(len(data)):
            building_id = str(idx)
            formatted_results[building_id] = {
                "zeitschritte": [convert_to_serializable(ts) for ts in results[0]],
                "außentemperatur": results[-1].tolist(),
                "wärme": results[1][idx].tolist(),
                "heizwärme": results[2][idx].tolist(),
                "warmwasserwärme": results[3][idx].tolist(),
                "max_last": results[4].tolist(),
                "vorlauftemperatur": results[5][idx].tolist(),
                "rücklauftemperatur": results[6][idx].tolist(),
            }
            for key, value in data.iloc[idx].items():
                formatted_results[building_id][key] = convert_to_serializable(value)
        return formatted_results

    def combine_data_with_results(self, data, results):
        """
        Combines the input data with the calculated results.

        Args:
            data (pd.DataFrame): The input data.
            results (dict): The calculated results.

        Returns:
            dict: The combined data and results.
        """
        data.reset_index(drop=True, inplace=True)
        data_dict = data.applymap(convert_to_serializable).to_dict(orient='index')
        combined_data = {str(idx): {**data_dict[idx], **results[str(idx)]} for idx in range(len(data))}
        return combined_data

    def on_combobox_selection_changed(self):
        """
        Updates the plot based on the selected combobox items.
        """
        self.view.plot(self.model.results)

class BuildingTabView(QWidget):
    """
    The BuildingTabView class manages the UI components for the BuildingTab.

    Signals:
        load_csv_signal (str): Emitted when a CSV file is loaded.
        save_csv_signal (str): Emitted when a CSV file is saved.
        calculate_heat_demand_signal (str): Emitted when heat demand calculation is requested.
        load_json_signal (str): Emitted when a JSON file is loaded.
        update_path_signal (str): Emitted when the output path is updated.
    """

    load_csv_signal = pyqtSignal(str)
    save_csv_signal = pyqtSignal(str)
    calculate_heat_demand_signal = pyqtSignal(str)
    load_json_signal = pyqtSignal(str)
    update_path_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """
        Initializes the optimized UI components with improved layout and functionality.
        """
        self.main_layout = QVBoxLayout(self)
        self.initMenuBar()

        # Data table area
        self.table_widget = QTableWidget(self)
        self.table_widget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.main_layout.addWidget(self.table_widget)

        # Output path layout (more compact with better labels)
        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(QLabel("Output JSON File:"))
        self.output_path_edit = QLineEdit("")
        output_path_layout.addWidget(self.output_path_edit)
        self.output_path_button = QPushButton("Browse")
        self.output_path_button.clicked.connect(self.browseOutputFile)
        output_path_layout.addWidget(self.output_path_button)
        self.main_layout.addLayout(output_path_layout)

        # Plot area (with toolbar and interaction improvements)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.main_layout.addWidget(self.canvas)
        self.main_layout.addWidget(self.toolbar)

        # Data selection comboboxes (streamlined with clearer labels)
        self.data_type_combobox = CheckableComboBox(self)
        for data_type in ["Heat Demand", "Heating Demand", "Warmwater Demand", "Supply Temperature", "Return Temperature"]:
            self.data_type_combobox.addItem(data_type)
        self.main_layout.addWidget(QLabel("Select Data Types:"))
        self.main_layout.addWidget(self.data_type_combobox)

        self.building_combobox = CheckableComboBox(self)
        self.main_layout.addWidget(QLabel("Select Buildings:"))
        self.main_layout.addWidget(self.building_combobox)

        self.setLayout(self.main_layout)

        # Initialize the data type comboboxes for the first time with the first item checked (heat demand)
        self.data_type_combobox.model().item(0).setCheckState(Qt.Checked)

        # Initialize the building combobox for the first time with the first item checked (Building 0)
        #self.building_combobox.model().item(0).setCheckState(Qt.Checked)

    def initMenuBar(self):
        """
        Initializes a cleaner menu bar with distinct separation from the rest of the layout.
        """
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        load_csv_action = QAction("CSV laden", self)
        load_csv_action.triggered.connect(self.loadCsvFile)
        self.menubar.addAction(load_csv_action)

        save_csv_action = QAction("CSV speichern", self)
        save_csv_action.triggered.connect(self.saveCsvFile)
        self.menubar.addAction(save_csv_action)

        calculate_action = QAction("Gebäudelastgänge berechnen", self)
        calculate_action.triggered.connect(self.calculateHeatDemand)
        self.menubar.addAction(calculate_action)

        load_json_action = QAction("Gebäudelastgänge laden", self)
        load_json_action.triggered.connect(self.loadJsonFile)
        self.menubar.addAction(load_json_action)

        self.main_layout.setMenuBar(self.menubar)

    def browseOutputFile(self):
        """
        Opens a file dialog to select the output JSON file.
        """
        fname, _ = QFileDialog.getSaveFileName(self, 'Save JSON File As', self.output_path_edit.text(), 'JSON Files (*.json);;All Files (*)')
        if fname:
            self.output_path_edit.setText(fname)

    def loadCsvFile(self):
        """
        Opens a file dialog to load a CSV file.
        """
        fname, _ = QFileDialog.getOpenFileName(self, 'Select CSV File', f"{self.base_path}/Gebäudedaten", 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.load_csv_signal.emit(fname)

    def saveCsvFile(self):
        """
        Opens a file dialog to save the CSV file.
        """
        fname, _ = QFileDialog.getSaveFileName(self, 'Save CSV File As', f"{self.base_path}/Gebäudedaten", 'CSV Files (*.csv);;All Files (*)')
        if fname:
            self.save_csv_signal.emit(fname)

    def loadJsonFile(self):
        """
        Opens a file dialog to load a JSON file.
        """
        fname, _ = QFileDialog.getOpenFileName(self, 'Select JSON File', self.output_path_edit.text(), 'JSON Files (*.json);;All Files (*)')
        if fname:
            self.load_json_signal.emit(fname)

    def calculateHeatDemand(self):
        """
        Emits a signal to calculate heat demand.
        """
        output_path = self.output_path_edit.text()
        self.calculate_heat_demand_signal.emit(output_path)

    def populate_table(self, data):
        """
        Populates the table widget with data.

        Args:
            data (pd.DataFrame): The data to populate the table with.
        """
        self.table_widget.setColumnCount(len(data.columns))
        self.table_widget.setRowCount(len(data.index))
        self.table_widget.setHorizontalHeaderLabels(data.columns)

        for i in range(len(data.index)):
            for j in range(len(data.columns)):
                item = QTableWidgetItem(str(data.iat[i, j]))
                self.table_widget.setItem(i, j, item)

        self.table_widget.resizeColumnsToContents()

    def get_table_data(self):
        """
        Retrieves the data from the table widget.

        Returns:
            pd.DataFrame: The data from the table widget.
        """
        rows = self.table_widget.rowCount()
        columns = self.table_widget.columnCount()
        data = []

        for row in range(rows):
            row_data = []
            for column in range(columns):
                widget = self.table_widget.cellWidget(row, column)
                if widget:
                    # Check if the widget is a QComboBox (for example) or QLineEdit and handle accordingly
                    if isinstance(widget, QComboBox):
                        row_data.append(widget.currentText())
                    elif isinstance(widget, QLineEdit):
                        row_data.append(widget.text())
                else:
                    # If no widget, get the text from the item directly
                    item = self.table_widget.item(row, column)
                    if item and item.text():
                        row_data.append(item.text())
                    else:
                        row_data.append(None)
            data.append(row_data)

        df = pd.DataFrame(data, columns=[self.table_widget.horizontalHeaderItem(i).text() for i in range(columns)])

        # Spezifische Spalten in Strings konvertieren, wenn nötig
        if 'Subtyp' in df.columns:
            df['Subtyp'] = df['Subtyp'].astype(str)

        return df

    def populate_building_combobox(self, results):
        """
        Populates the building combobox with the results data.

        Args:
            results (dict): The results data to populate the combobox with.
        """
        self.building_combobox.clear()
        for key in results.keys():
            self.building_combobox.addItem(f'Building {key}')
            item = self.building_combobox.model().item(self.building_combobox.count() - 1, 0)
            item.setCheckState(Qt.Checked)

    def plot(self, results=None):
        """
        Plots the selected data types for the selected buildings, adjusting the figure size for the legend outside.
        
        Args:
            results (dict, optional): The results data to plot. Defaults to None.
        """
        if results is None:
            return

        self.figure.clear()
        ax1 = self.figure.add_subplot(111)
        ax2 = ax1.twinx()

        selected_data_types = self.data_type_combobox.checkedItems()
        selected_buildings = self.building_combobox.checkedItems()

        for building in selected_buildings:
            key = building.split()[-1]
            value = results[key]

            if "Heat Demand" in selected_data_types:
                ax1.plot(value["wärme"], label=f'Building {key} Heat Demand')
            if "Heating Demand" in selected_data_types:
                ax1.plot(value["heizwärme"], label=f'Building {key} Heating Demand', linestyle='--')
            if "Warmwater Demand" in selected_data_types:
                ax1.plot(value["warmwasserwärme"], label=f'Building {key} Warmwater Demand', linestyle=':')
            if "Supply Temperature" in selected_data_types:
                ax2.plot(value["vorlauftemperatur"], label=f'Building {key} Supply Temp', linestyle='-.')
            if "Return Temperature" in selected_data_types:
                ax2.plot(value["rücklauftemperatur"], label=f'Building {key} Return Temp', linestyle='-.')

        ax1.set_xlabel('Time (hours)')
        ax1.set_ylabel('Heat Demand (kW)')
        ax2.set_ylabel('Temperature (°C)')

        # Legend for ax1 on the left
        ax1.legend(loc='center right', bbox_to_anchor=(-0.2, 0.5))  # Left of the plot
        # Legend for ax2 on the right
        ax2.legend(loc='center left', bbox_to_anchor=(1.2, 0.5))  # Right of the plot

        # Adjust layout to ensure the legends do not overlap the plot
        self.figure.subplots_adjust(left=0.25, right=0.75, top=0.9, bottom=0.1)

        ax1.grid()

        self.canvas.draw()

    def show_error_message(self, title, message):
        """
        Displays an error message in a message box.

        Args:
            title (str): The title of the message box.
            message (str): The message content.
        """
        QMessageBox.critical(self, title, message)

    def show_message(self, title, message):
        """
        Displays an information message in a message box.

        Args:
            title (str): The title of the message box.
            message (str): The message content.
        """
        QMessageBox.information(self, title, message)

    def update_output_path(self, base_path, json_path):
        """
        Updates the output path in the view.
        
        Args:
            path (str): The new output path.
        """
        self.base_path = base_path  # Update the base path
        self.output_path_edit.setText(os.path.join(self.base_path, json_path))

class BuildingTab(QMainWindow):
    """
    The BuildingTab class is the main window for the BuildingTab UI.

    Args:
        data_manager (object): The data manager for the application.
        parent (QWidget, optional): The parent widget. Defaults to None.
    """

    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Building Tab Example")
        self.setGeometry(100, 100, 800, 600)

        self.model = BuildingModel()
        self.view = BuildingTabView()
        self.presenter = BuildingPresenter(self.model, self.view, folder_manager, data_manager, config_manager)

        self.setCentralWidget(self.view)