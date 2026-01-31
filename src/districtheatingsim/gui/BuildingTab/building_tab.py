"""
Building data management and heat demand calculation module.

Provides MVP architecture for building heat requirement calculations using
BDEW profiles and Test Reference Year (TRY) climate data.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os
import sys
import json
import pandas as pd

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QMessageBox,
                             QMainWindow, QTableWidget, QTableWidgetItem, QComboBox, 
                             QMenuBar, QLineEdit, QAbstractScrollArea, QHBoxLayout, QSizePolicy, QGroupBox)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import pyqtSignal, Qt

from districtheatingsim.heat_requirement.heat_requirement_calculation_csv import generate_profiles_from_csv
from districtheatingsim.gui.utilities import CheckableComboBox, convert_to_serializable

import traceback

class BuildingModel:
    """
    Data model for building information and heat demand calculations.

    Manages CSV input data, JSON results, and heat profile generation.
    """

    def __init__(self):
        self.base_path = None
        self.csv_path = ""
        self.json_path = ""
        self.data = None
        self.results = None

    def set_base_path(self, base_path):
        """
        Set base path for file operations.

        :param base_path: Base directory path
        :type base_path: str
        """
        self.base_path = base_path

    def get_base_path(self):
        """
        Get base path.

        :return: Current base path
        :rtype: str
        """
        return self.base_path
    
    def set_csv_path(self, csv_path):
        """
        Set CSV file path.

        :param csv_path: Path to CSV file
        :type csv_path: str
        """
        self.csv_path = csv_path

    def get_csv_path(self):
        """
        Get CSV file path.

        :return: Current CSV file path
        :rtype: str
        """
        return self.csv_path

    def set_json_path(self, json_path):
        """
        Set JSON file path.

        :param json_path: Path to JSON file
        :type json_path: str
        """
        self.json_path = json_path

    def get_json_path(self):
        """
        Get JSON file path.

        :return: Current JSON file path
        :rtype: str
        """
        return self.json_path

    def load_csv(self):
        """
        Load CSV data into DataFrame.

        :raises Exception: If CSV loading fails
        """
        try:
            self.data = pd.read_csv(self.get_csv_path(), delimiter=';', dtype={'Subtyp': str})
        except Exception as e:
            raise Exception(f"Fehler beim Laden der CSV-Datei: {e}")

    def save_csv(self):
        """
        Save DataFrame to CSV file.

        :raises Exception: If CSV saving fails
        """
        if self.data is not None:
            try:
                self.data.to_csv(self.get_csv_path(), index=False, sep=';', encoding='utf-8-sig')
            except Exception as e:
                raise Exception(f"Fehler beim Speichern der CSV-Datei: {e}")

    def load_json(self):
        """
        Load results from JSON file.

        :raises Exception: If JSON loading fails
        """
        try:
            with open(self.get_json_path(), 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                self.results = {k: v for k, v in loaded_data.items() if isinstance(v, dict) and 'wärme' in v}
        except Exception as e:
            raise Exception(f"Fehler beim Laden der JSON-Datei: {e}")

    def save_json(self, combined_data):
        """
        Save results to JSON file.

        :param combined_data: Data to save
        :type combined_data: dict
        :raises Exception: If JSON saving fails
        """
        try:
            with open(self.get_json_path(), 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=4)
        except Exception as e:
            raise Exception(f"Fehler beim Speichern der Ergebnisse: {e}")

    def calculate_heat_demand(self, data, try_filename):
        """
        Calculate heat demand profiles from building data.

        :param data: Building input data
        :type data: pd.DataFrame
        :param try_filename: Climate data filename
        :type try_filename: str
        :return: Calculated heat demand profiles in kW
        :rtype: tuple
        """
        yearly_time_steps, total_heat_W, heating_heat_W, warmwater_heat_W, max_heat_requirement_W, supply_temperature_curve, return_temperature_curve, hourly_air_temperatures = generate_profiles_from_csv(data=data, TRY=try_filename, calc_method="Datensatz")

        # Convert from W to kW
        return yearly_time_steps, total_heat_W/1000, heating_heat_W/1000, warmwater_heat_W/1000, max_heat_requirement_W/1000, supply_temperature_curve, return_temperature_curve, hourly_air_temperatures

class BuildingPresenter:
    """
    Presenter managing interaction between BuildingModel and BuildingTabView.

    Coordinates building data operations, heat demand calculations, and UI updates.
    """

    def __init__(self, model, view, folder_manager, data_manager, config_manager):
        """
        Initialize building presenter.

        :param model: Data model
        :type model: BuildingModel
        :param view: View component
        :type view: BuildingTabView
        :param folder_manager: Folder manager
        :type folder_manager: ProjectFolderManager
        :param data_manager: Data manager
        :type data_manager: DataManager
        :param config_manager: Configuration manager
        :type config_manager: ProjectConfigManager
        """
        self.model = model
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        # Connect signals
        self.folder_manager.project_folder_changed.connect(self.standard_path)
        if self.folder_manager.variant_folder:
            self.standard_path(self.folder_manager.variant_folder)

        self.view.load_csv_signal.connect(self.load_csv)
        self.view.save_csv_signal.connect(self.save_csv)
        self.view.load_json_signal.connect(self.load_json)
        self.view.save_json_signal.connect(self.save_json)
        self.view.calculate_heat_demand_signal.connect(self.calculate_heat_demand)

        self.view.data_type_combobox.view().pressed.connect(self.on_combobox_selection_changed)
        self.view.building_combobox.view().pressed.connect(self.on_combobox_selection_changed)

        self.view.plot(self.model.results)  # Initial plot

    def standard_path(self, path):
        """
        Update default file paths.

        :param path: New base path
        :type path: str
        """
        if path:
            self.model.set_base_path(path)
            self.model.set_csv_path(os.path.join(self.model.get_base_path(), self.config_manager.get_relative_path("current_building_data_path")))
            self.model.set_json_path(os.path.join(self.model.get_base_path(), self.config_manager.get_relative_path("building_load_profile_path")))

    def load_csv(self, fname=None, show_dialog=True):
        """
        Load CSV file with file dialog.

        Parameters
        ----------
        fname : str, optional
            Filename to load.
        show_dialog : bool, optional
            Whether to show success/error dialogs. Default is True.
        """
        if fname is None or fname == "":
            fname, _ = QFileDialog.getOpenFileName(self.view, 'Select CSV File', self.model.get_csv_path(), 'CSV Files (*.csv);;All Files (*)')
        if fname:
            try:
                self.model.set_csv_path(fname)
                self.model.load_csv()
                self.view.populate_table(self.model.data)
                if show_dialog:
                    self.view.show_message("Erfolg", f"CSV-Datei {fname} wurde geladen.")
            except Exception as e:
                if show_dialog:
                    self.view.show_error_message("Fehler", str(e))

    def save_csv(self, fname=None, show_dialog=True):
        """
        Save CSV file with file dialog.

        Parameters
        ----------
        fname : str, optional
            Filename to save.
        """
        if fname is None or fname == "":
            if show_dialog:
                fname, _ = QFileDialog.getSaveFileName(self.view, 'Save CSV File', self.model.get_csv_path(), 'CSV Files (*.csv);;All Files (*)')
            else:
                fname = self.model.get_csv_path()
        if fname:
            try:
                self.model.set_csv_path(fname)
                self.model.save_csv()
                if show_dialog:
                    self.view.show_message("Erfolg", f"CSV-Datei wurde in {fname} gespeichert.")
            except Exception as e:
                if show_dialog:
                    self.view.show_error_message("Fehler", str(e))

    def load_json(self, fname=None, show_dialog=True):
        """
        Load JSON results with optional file dialog.

        Parameters
        ----------
        fname : str, optional
            Filename to load.
        show_dialog : bool, optional
            Whether to show file dialog if no filename provided. Default is True.
        """
        if fname is None or fname == "":
            if show_dialog:
                fname, _ = QFileDialog.getOpenFileName(self.view, 'Select JSON File', self.model.get_json_path(), 'JSON Files (*.json);;All Files (*)')
            else:
                return
        if fname:
            try:
                self.model.set_json_path(fname)
                self.model.load_json()
                self.view.populate_building_combobox(self.model.results)
                self.view.plot(self.model.results)
            except Exception as e:
                self.view.show_error_message("Fehler", str(e))

    def save_json(self, fname=None, show_dialog=True):
        """
        Save JSON results with file dialog.

        Parameters
        ----------
        fname : str, optional
            Filename to save.
        """
        if self.combined_data is None:
            self.view.show_error_message("Fehler", "Es sind keine Daten zum Speichern vorhanden.")
            return
        
        if fname is None or fname == "":
            if show_dialog:
                fname, _ = QFileDialog.getSaveFileName(self.view, 'Save JSON File', self.model.get_json_path(), 'JSON Files (*.json);;All Files (*)')
            else:
                fname = self.model.get_json_path()
        if fname:
            try:
                self.model.set_json_path(fname)
                self.model.save_json(self.combined_data)
                if show_dialog:
                    self.view.show_message("Erfolg", f"Ergebnisse wurden in {fname} gespeichert.")
            except Exception as e:
                if show_dialog:
                    self.view.show_error_message("Fehler", str(e))

    def calculate_heat_demand(self, _=None):
        """Calculate heat demand profiles and save results."""
        self.data = self.view.get_table_data()
        if self.data.empty:
            self.view.show_error_message("Fehler", "Die Tabelle enthält keine Daten.")
            return

        try:
            try_filename = self.data_manager.get_try_filename()
            results = self.model.calculate_heat_demand(self.data, try_filename)
            self.model.results = self.format_results(results, self.data)

            self.view.populate_building_combobox(self.model.results)
            self.view.plot(self.model.results)

            self.combined_data = self.combine_data_with_results(self.data, self.model.results)
            self.model.save_json(self.combined_data)

            self.view.show_message("Erfolg", f"Berechnung der Gebäudelastgänge abgeschlossen und in {self.model.get_json_path()} gespeichert.")
        except Exception as e:
            tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            self.view.show_error_message("Fehler", f"Es ist ein Fehler aufgetreten: {str(e)}\n\nDetails:\n{tb_str}")

    def format_results(self, results, data):
        """
        Format calculation results for JSON storage.

        :param results: Raw calculation results
        :type results: tuple
        :param data: Input building data
        :type data: pd.DataFrame
        :return: Formatted results dictionary
        :rtype: dict
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
        Combine input data with calculation results.

        :param data: Input data
        :type data: pd.DataFrame
        :param results: Calculation results
        :type results: dict
        :return: Combined data dictionary
        :rtype: dict
        """
        data.reset_index(drop=True, inplace=True)
        data_dict = data.applymap(convert_to_serializable).to_dict(orient='index')
        combined_data = {str(idx): {**data_dict[idx], **results[str(idx)]} for idx in range(len(data))}
        return combined_data

    def on_combobox_selection_changed(self):
        """Update plot when combobox selection changes."""
        self.view.plot(self.model.results)

class BuildingTabView(QWidget):
    """
    View component for building tab UI.

    Provides table for building data input and interactive plotting
    of heat demand profiles.
    """

    load_csv_signal = pyqtSignal(str)
    save_csv_signal = pyqtSignal(str)
    load_json_signal = pyqtSignal(str)
    save_json_signal = pyqtSignal(str)
    calculate_heat_demand_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        """
        Initialize building tab view.

        :param parent: Parent widget (optional)
        :type parent: QWidget
        """
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """Initialize UI components."""
        self.main_layout = QVBoxLayout(self)
        self.initMenuBar()
        self.initDataTable()
        self.initPlotAndComboboxes()
        self.setLayout(self.main_layout)

    def initMenuBar(self):
        """Initialize menu bar with file operations."""
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        load_csv_action = QAction("Gebäudedaten laden", self)
        load_csv_action.triggered.connect(self.loadCsvFile)
        self.menubar.addAction(load_csv_action)

        save_csv_action = QAction("Gebäudedaten speichern", self)
        save_csv_action.triggered.connect(self.saveCsvFile)
        self.menubar.addAction(save_csv_action)

        calculate_action = QAction("Gebäudelastgänge berechnen", self)
        calculate_action.triggered.connect(self.calculateHeatDemand)
        self.menubar.addAction(calculate_action)

        save_json_action = QAction("Gebäudelastgänge speichern", self)
        save_json_action.triggered.connect(self.saveJsonFile)
        self.menubar.addAction(save_json_action)

        load_json_action = QAction("Gebäudelastgänge laden", self)
        load_json_action.triggered.connect(self.loadJsonFile)
        self.menubar.addAction(load_json_action)

        self.main_layout.setMenuBar(self.menubar)

    def initDataTable(self):
        """Initialize data table widget."""
        self.table_widget = QTableWidget(self)
        self.table_widget.setMinimumSize(1200, 300)
        self.table_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.main_layout.addWidget(self.table_widget)

    def initPlotAndComboboxes(self):
        """Initialize plot area and data selection controls."""
        # Plot area oben
        plot_layout = QVBoxLayout()
        self.figure = Figure(constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(1200, 500)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.toolbar = NavigationToolbar(self.canvas, self)
        plot_layout.addWidget(self.canvas)
        toolbar_layout = QHBoxLayout()
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.toolbar)
        toolbar_layout.addStretch(1)
        plot_layout.addLayout(toolbar_layout)
        self.main_layout.addLayout(plot_layout)

        
        combobox_group = QGroupBox()
        combobox_group.setTitle("Auswahl")
        combobox_group_layout = QHBoxLayout()

        # Daten auswählen
        data_label = QLabel("<b>Daten auswählen:</b>")
        data_label.setStyleSheet("font-size: 15px; margin-right: 10px;")
        self.data_type_combobox = CheckableComboBox(self)
        for data_type in ["Wärmebedarf", "Heizwärmebedarf", "Warmwasserbedarf", "Vorlauftemperatur", "Rücklauftemperatur"]:
            self.data_type_combobox.addItem(data_type)
        self.data_type_combobox.model().item(0).setCheckState(Qt.CheckState.Checked)
        combobox_group_layout.addWidget(data_label)
        combobox_group_layout.addWidget(self.data_type_combobox)

        # Gebäude auswählen
        building_label = QLabel("<b>Gebäude auswählen:</b>")
        building_label.setStyleSheet("font-size: 15px; margin-left: 30px; margin-right: 10px;")
        self.building_combobox = CheckableComboBox(self)
        combobox_group_layout.addWidget(building_label)
        combobox_group_layout.addWidget(self.building_combobox)

        combobox_group.setLayout(combobox_group_layout)
        self.main_layout.addWidget(combobox_group)

    def loadCsvFile(self):
        """Emit signal to load CSV file."""
        self.load_csv_signal.emit(None)
    
    def saveCsvFile(self):
        """Emit signal to save CSV file."""
        self.save_csv_signal.emit(None)

    def loadJsonFile(self):
        """Emit signal to load JSON file."""
        self.load_json_signal.emit(None)
    
    def saveJsonFile(self):
        """Emit signal to save JSON file."""
        self.save_json_signal.emit(None)

    def calculateHeatDemand(self):
        """Emit signal to calculate heat demand."""
        self.calculate_heat_demand_signal.emit(None)

    def populate_table(self, data):
        """
        Populate table with DataFrame data.

        :param data: Data to display in table
        :type data: pd.DataFrame
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
        Extract data from table widget.

        :return: Table data as DataFrame
        :rtype: pd.DataFrame
        """
        rows = self.table_widget.rowCount()
        columns = self.table_widget.columnCount()
        data = []

        for row in range(rows):
            row_data = []
            for column in range(columns):
                widget = self.table_widget.cellWidget(row, column)
                if widget:
                    if isinstance(widget, QComboBox):
                        row_data.append(widget.currentText())
                    elif isinstance(widget, QLineEdit):
                        row_data.append(widget.text())
                else:
                    item = self.table_widget.item(row, column)
                    if item and item.text():
                        row_data.append(item.text())
                    else:
                        row_data.append(None)
            data.append(row_data)

        df = pd.DataFrame(data, columns=[self.table_widget.horizontalHeaderItem(i).text() for i in range(columns)])

        if 'Subtyp' in df.columns:
            df['Subtyp'] = df['Subtyp'].astype(str)

        return df

    def populate_building_combobox(self, results):
        """
        Populate building selection combobox.

        :param results: Results data for building selection
        :type results: dict
        """
        self.building_combobox.clear()
        for key in results.keys():
            self.building_combobox.addItem(f'Gebäude {key}')
            item = self.building_combobox.model().item(self.building_combobox.count() - 1, 0)
            item.setCheckState(Qt.CheckState.Checked)


    def plot(self, results=None):
        """
        Plot heat demand profiles for selected buildings and data types.
        
        :param results: Heat demand calculation results
        :type results: dict
        """
        if results is None:
            return

        # Modernes Theme
        plt.style.use('seaborn-v0_8-darkgrid')

        self.figure.clear()
        
        gs = gridspec.GridSpec(1, 3, width_ratios=[0.18, 0.64, 0.18], figure=self.figure)
        ax_legend_left = self.figure.add_subplot(gs[0, 0])
        ax_main = self.figure.add_subplot(gs[0, 1])
        ax_legend_right = self.figure.add_subplot(gs[0, 2])
        ax2 = ax_main.twinx()

        selected_data_types = self.data_type_combobox.checkedItems()
        selected_buildings = self.building_combobox.checkedItems()

        label_fontsize = 16
        legend_fontsize = 12
        line_width = 2

        color_map = plt.get_cmap('tab10')
        temp_color_map = plt.get_cmap('Set2')
        color_idx = 0
        temp_color_idx = 0

        lines_ax1 = []
        labels_ax1 = []
        lines_ax2 = []
        labels_ax2 = []

        for building in selected_buildings:
            key = building.split()[-1]
            value = results[key]
            x = list(range(len(value["wärme"])))

            if "Wärmebedarf" in selected_data_types:
                line, = ax_main.plot(x, value["wärme"], label=f'Wärmebedarf Gebäude {key}', color=color_map(color_idx % 10), linewidth=line_width)
                lines_ax1.append(line)
                labels_ax1.append(f'Wärmebedarf Gebäude {key}')
                color_idx += 1
            if "Heizwärmebedarf" in selected_data_types:
                line, = ax_main.plot(x, value["heizwärme"], label=f'Heizwärmebedarf Gebäude {key}', color=color_map(color_idx % 10), linestyle='--', linewidth=line_width)
                lines_ax1.append(line)
                labels_ax1.append(f'Heizwärmebedarf Gebäude {key}')
                color_idx += 1
            if "Warmwasserbedarf" in selected_data_types:
                line, = ax_main.plot(x, value["warmwasserwärme"], label=f'Warmwasserbedarf Gebäude {key}', color=color_map(color_idx % 10), linestyle=':', linewidth=line_width)
                lines_ax1.append(line)
                labels_ax1.append(f'Warmwasserbedarf Gebäude {key}')
                color_idx += 1
            if "Vorlauftemperatur" in selected_data_types:
                line, = ax2.plot(x, value["vorlauftemperatur"], label=f'Vorlauftemperatur Gebäude {key}', color=temp_color_map(temp_color_idx % 8), linestyle='-.', linewidth=line_width)
                lines_ax2.append(line)
                labels_ax2.append(f'Vorlauftemperatur Gebäude {key}')
                temp_color_idx += 1
            if "Rücklauftemperatur" in selected_data_types:
                line, = ax2.plot(x, value["rücklauftemperatur"], label=f'Rücklauftemperatur Gebäude {key}', color=temp_color_map(temp_color_idx % 8), linestyle='-.', linewidth=line_width)
                lines_ax2.append(line)
                labels_ax2.append(f'Rücklauftemperatur Gebäude {key}')
                temp_color_idx += 1

        ax_main.set_xlabel('Jahresstunden', fontsize=label_fontsize)
        ax_main.set_ylabel('Wärmebedarf (kW)', fontsize=label_fontsize)
        ax2.set_ylabel('Temperatur (°C)', fontsize=label_fontsize)

        ax_main.tick_params(axis='both', labelsize=14)
        ax2.tick_params(axis='y', labelsize=14)

        # Legenden als eigene Achsen
        ax_legend_left.axis('off')
        ax_legend_right.axis('off')

        # Dynamische Spaltenanzahl für Legenden
        def get_ncol(n):
            if n <= 18:
                return 1
            else:
                return 2

        if lines_ax1:
            ncol_left = get_ncol(len(lines_ax1))
            ax_legend_left.legend(lines_ax1, labels_ax1, loc='center', fontsize=legend_fontsize, frameon=False, ncol=ncol_left)

        if lines_ax2:
            ncol_right = get_ncol(len(lines_ax2))
            ax_legend_right.legend(lines_ax2, labels_ax2, loc='center', fontsize=legend_fontsize, frameon=False, ncol=ncol_right)

        self.figure.suptitle('Gebäude Wärmebedarf & Temperaturen', fontsize=18)
        ax_main.grid(True, alpha=0.3)
        self.canvas.draw()

    def showEvent(self, event):
        """
        Handle widget show event to trigger initial plot.
        
        :param event: Show event
        :type event: QShowEvent
        """
        super().showEvent(event)
        from PyQt6.QtCore import QTimer
        # Initiales Plotten nach Layout-Finish
        if hasattr(self, 'results') and self.results:
            QTimer.singleShot(0, lambda: self.plot(self.results))

    def show_error_message(self, title, message):
        """
        Display error message dialog.

        :param title: Dialog title
        :type title: str
        :param message: Error message
        :type message: str
        """
        QMessageBox.critical(self, title, message)

    def show_message(self, title, message):
        """
        Display information message dialog.

        :param title: Dialog title
        :type title: str
        :param message: Information message
        :type message: str
        """
        QMessageBox.information(self, title, message)

class BuildingTab(QMainWindow):
    """
    Main building tab window integrating MVP components.
    
    Central interface for building data management and heat demand analysis.
    """

    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initialize building tab with MVP architecture.

        :param folder_manager: Folder manager
        :type folder_manager: ProjectFolderManager
        :param data_manager: Data manager
        :type data_manager: DataManager
        :param config_manager: Configuration manager
        :type config_manager: ProjectConfigManager
        :param parent: Parent widget (optional)
        :type parent: QWidget
        """
        super().__init__(parent)
        self.setWindowTitle("Gebäudetab")
        self.setGeometry(100, 100, 800, 600)

        self.model = BuildingModel()
        self.view = BuildingTabView()
        self.presenter = BuildingPresenter(self.model, self.view, folder_manager, data_manager, config_manager)

        self.setCentralWidget(self.view)
        
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = BuildingTabView()
    window.resize(1400, 900)
    window.show()

    # Simuliere das Laden einer JSON wie im Model/Presenter
    json_path = os.path.join(os.path.dirname(__file__), "..", "..", "project_data", "Görlitz", "Variante 1", "Lastgang", "Gebäude Lastgang.json")
    json_path = os.path.abspath(json_path)
    import json
    with open(json_path, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
        # Filter wie im Model: nur dicts mit 'wärme'
        results = {k: v for k, v in loaded_data.items() if isinstance(v, dict) and 'wärme' in v}

    # Simuliere Presenter: populate_building_combobox und plot
    window.populate_building_combobox(results)
    window.plot(results)

    sys.exit(app.exec())