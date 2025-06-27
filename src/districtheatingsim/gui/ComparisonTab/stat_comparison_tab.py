"""
Stat Comparison Tab Module
=========================

Tab widget for comparing network statistics across project variants.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-30
"""

import os
import pandapipes as pp
import csv
import json
import numpy as np
import traceback

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QHBoxLayout, QMessageBox

from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import import_results_csv

class StatComparisonTab(QWidget):
    """
    Widget for comparing network statistics across project variants.
    """
    
    def __init__(self, folder_manager, config_manager, parent=None):
        """
        Initialize statistics comparison tab.

        Parameters
        ----------
        folder_manager : FolderManager
            Project folder manager.
        config_manager : ConfigManager
            Configuration manager.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.config_manager = config_manager
        self.folder_paths = []
        self.variant_data = []

        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.variant_folder)

        self.initUI()

    def updateDefaultPath(self, new_base_path):
        """
        Update base path when project folder changes.

        Parameters
        ----------
        new_base_path : str
            New base path.
        """
        self.base_path = new_base_path

    def initUI(self):
        """Initialize user interface with comparison table and controls."""
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

        # Create a table widget to display the data
        self.tableWidget = QTableWidget()
        self.layout.addWidget(self.tableWidget)

        self.setLayout(self.layout)

    def addData(self):
        """Load project data from selected folder and add to comparison."""
        # Open a file dialog to select the base path for the data
        folder_path = QFileDialog.getExistingDirectory(self, "Ordner auswählen", self.base_path)

        if folder_path:
            self.folder_paths.append(folder_path)
            data = self.load_variant_data(folder_path)
            if data:
                self.variant_data.append(data)
                self.display_data_in_table()

    def removeData(self):
        """Remove last loaded project data from comparison."""
        if self.variant_data:
            self.variant_data.pop()
            self.folder_paths.pop()
            self.display_data_in_table()
        else:
            QMessageBox.warning(self, "Keine Daten", "Keine Daten zum entfernen vorhanden.")

    def load_variant_data(self, folder_path):
        """
        Load and process network data from project folder.

        Parameters
        ----------
        folder_path : str
            Path to project folder.

        Returns
        -------
        dict
            Processed network statistics.
        """
        try:
            # Load network data
            self.loadNet(folder_path)

            if not hasattr(self, 'net'):
                self.result_text = "Netzdaten nicht verfügbar."
                self.results_display.setPlainText(self.result_text)
                return

            Anzahl_Gebäude = len(self.net.heat_consumer) if hasattr(self.net, 'heat_consumer') else None

            if hasattr(self.net, 'circ_pump_pressure'):
                if hasattr(self.net, 'circ_pump_mass'):
                    Anzahl_Heizzentralen = len(self.net.circ_pump_pressure) + len(self.net.circ_pump_mass)
                else:
                    Anzahl_Heizzentralen = len(self.net.circ_pump_pressure)
            else:
                Anzahl_Heizzentralen = None

            Gesamtwärmebedarf_Gebäude_MWh = np.sum(self.waerme_ges_kW) / 1000 if hasattr(self, 'waerme_ges_kW') else None
            Gesamtheizlast_Gebäude_kW = np.max(self.waerme_ges_kW) if hasattr(self, 'waerme_ges_kW') else None

            if hasattr(self.net.pipe, 'length_km'):
                Trassenlänge_m = self.net.pipe.length_km.sum() * 1000 / 2
            else:
                Trassenlänge_m = None

            Wärmebedarfsdichte_MWh_a_m = Gesamtwärmebedarf_Gebäude_MWh / Trassenlänge_m if Gesamtwärmebedarf_Gebäude_MWh is not None and Trassenlänge_m is not None else None
            Anschlussdichte_kW_m = Gesamtheizlast_Gebäude_kW / Trassenlänge_m if Gesamtheizlast_Gebäude_kW is not None and Trassenlänge_m is not None else None

            Jahreswärmeerzeugung_MWh = 0
            Pumpenstrombedarf_MWh = 0
            if hasattr(self, 'pump_results'):
                for pump_type, pumps in self.pump_results.items():
                    for idx, pump_data in pumps.items():
                        Jahreswärmeerzeugung_MWh += np.sum(pump_data['qext_kW']) / 1000
                        Pumpenstrombedarf_MWh += np.sum((pump_data['mass_flow']/1000)*(pump_data['deltap']*100)) / 1000

            Verteilverluste_kW = Jahreswärmeerzeugung_MWh - Gesamtwärmebedarf_Gebäude_MWh if Gesamtwärmebedarf_Gebäude_MWh is not None and Jahreswärmeerzeugung_MWh is not None and Jahreswärmeerzeugung_MWh != 0 else None
            rel_Verteilverluste_percent = (Verteilverluste_kW / Jahreswärmeerzeugung_MWh) * 100 if Verteilverluste_kW is not None and Jahreswärmeerzeugung_MWh is not None and Jahreswärmeerzeugung_MWh != 0 else None
            
            # Process the data as needed
            results = {
                "Anzahl angeschlossene Gebäude": Anzahl_Gebäude,
                "Anzahl Heizzentralen": Anzahl_Heizzentralen,
                "Jahresgesamtwärmebedarf (MWh)": np.round(Gesamtwärmebedarf_Gebäude_MWh, 2),
                "max. Heizlast Gebäude (kW)": np.round(Gesamtheizlast_Gebäude_kW, 2),
                "Trassenlänge Wärmenetz (m)": np.round(Trassenlänge_m, 2),
                "Wärmebedarfsdichte (MWh/(a*m))": np.round(Wärmebedarfsdichte_MWh_a_m, 2),
                "Anschlussdichte (kW/m)": np.round(Anschlussdichte_kW_m, 2),
                "Jahreswärmeerzeugung (MWh)": np.round(Jahreswärmeerzeugung_MWh, 2),
                "Verteilverluste (kW)": np.round(Verteilverluste_kW, 2),
                "Relative Verteilverluste (%)": np.round(rel_Verteilverluste_percent, 2),
                "Pumpenstrombedarf (MWh)": np.round(Pumpenstrombedarf_MWh, 2)
            }

            return results
        
        except Exception as e:
            # Capture the traceback and display it in a message box
            tb_str = traceback.format_exc()
            QMessageBox.critical(self, "Loading Failed", f"Error loading data for {folder_path}:\n\n{str(e)}\n\nTraceback:\n{tb_str}")
            raise e

    def loadNet(self, folder_path):
        """
        Load network from project files.

        Parameters
        ----------
        folder_path : str
            Path to project folder.
        """
        try:
            # Load different components
            self.load_pickle_file(folder_path)
            self.load_csv_file(folder_path)
            self.load_json_file(folder_path)

            # Load additional results
            self.load_net_results(folder_path)

            # Process data
            self.process_loaded_data()

            QMessageBox.information(self, "Laden erfolgreich", 
                                    "Daten erfolgreich geladen aus: {}, {} und {}.".format(
                                        os.path.join(folder_path, self.config_manager.get_relative_path("csv_net_init_file_path")),
                                        os.path.join(folder_path, self.config_manager.get_relative_path("pp_pickle_file_path")),
                                        os.path.join(folder_path, self.config_manager.get_relative_path("json_net_init_file_path"))
                                    ))
        except Exception as e:
            # add the traceback to the error message
            tb_str = traceback.format_exc()
            QMessageBox.critical(self, "Laden fehlgeschlagen", f"Fehler beim Laden der Daten aus {folder_path}:\n\n{str(e)}\n\nTraceback:\n{tb_str}")

    def load_pickle_file(self, folder_path):
        """
        Load network data from pickle file.

        Parameters
        ----------
        folder_path : str
            Path to project folder.
        """
        pickle_file_path = os.path.join(folder_path, self.config_manager.get_relative_path("pp_pickle_file_path"))
        self.net = pp.from_pickle(pickle_file_path)

    def load_csv_file(self, folder_path):
        """
        Load heat and electricity demand data from CSV file.

        Parameters
        ----------
        folder_path : str
            Path to project folder.
        """
        csv_file_path = os.path.join(folder_path, self.config_manager.get_relative_path("csv_net_init_file_path"))

        with open(csv_file_path, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            headers = next(reader)
            num_waerme_cols = len([h for h in headers if h.startswith('waerme_ges_W')])
            num_strom_cols = len([h for h in headers if h.startswith('strombedarf_hast_ges_W')])

            formatted_time_steps = []
            waerme_ges_W_data = []
            strombedarf_hast_ges_W_data = []

            for row in reader:
                formatted_time_steps.append(np.datetime64(row[0]))
                waerme_ges_W_data.append([float(value) for value in row[1:num_waerme_cols + 1]])
                strombedarf_hast_ges_W_data.append([float(value) for value in row[num_waerme_cols + 1:num_waerme_cols + num_strom_cols + 1]])

            self.yearly_time_steps = np.array(formatted_time_steps)
            self.waerme_ges_W = np.array(waerme_ges_W_data).transpose()
            self.strombedarf_hast_ges_W = np.array(strombedarf_hast_ges_W_data).transpose()

    def load_json_file(self, folder_path):
        """
        Load configuration data from JSON file.

        Parameters
        ----------
        folder_path : str
            Path to project folder.
        """
        json_file_path = os.path.join(folder_path, self.config_manager.get_relative_path("json_net_init_file_path"))

        with open(json_file_path, 'r') as json_file:
            additional_data = json.load(json_file)

        self.supply_temperature = np.array(additional_data['supply_temperature'])
        self.supply_temperature_heat_consumer = float(additional_data['supply_temperature_heat_consumers'] if additional_data['supply_temperature_heat_consumers'] is not None else 0.0)
        self.return_temperature_heat_consumer = np.array(additional_data['return_temperature'])
        self.supply_temperature_buildings = np.array(additional_data['supply_temperature_buildings'])
        self.return_temperature_buildings = np.array(additional_data['return_temperature_buildings'])
        self.supply_temperature_buildings_curve = np.array(additional_data['supply_temperature_buildings_curve'])
        self.return_temperature_buildings_curve = np.array(additional_data['return_temperature_buildings_curve'])
        self.netconfiguration = additional_data['netconfiguration']
        self.dT_RL = additional_data['dT_RL']
        self.building_temp_checked = additional_data['building_temp_checked']
        self.max_el_leistung_hast_ges_W = np.array(additional_data['max_el_leistung_hast_ges_W'])
        self.TRY_filename = additional_data['TRY_filename']
        self.COP_filename = additional_data['COP_filename']

    def process_loaded_data(self):
        """Process data after loading, converting units and summing values."""
        self.net_data = (self.net, self.yearly_time_steps, self.waerme_ges_W,
                        self.supply_temperature_heat_consumer, self.supply_temperature, 
                        self.return_temperature_heat_consumer, self.supply_temperature_buildings, 
                        self.return_temperature_buildings, self.supply_temperature_buildings_curve, 
                        self.return_temperature_buildings_curve, self.netconfiguration, 
                        self.dT_RL, self.building_temp_checked, self.strombedarf_hast_ges_W,
                        self.max_el_leistung_hast_ges_W, self.TRY_filename, self.COP_filename)
        
        self.waerme_ges_kW = np.where(self.waerme_ges_W == 0, 0, self.waerme_ges_W / 1000)
        self.strombedarf_hast_ges_kW = np.where(self.strombedarf_hast_ges_W == 0, 0, self.strombedarf_hast_ges_W / 1000)
        
        self.waerme_ges_kW = np.sum(self.waerme_ges_kW, axis=0)
        self.strombedarf_hast_ges_kW = np.sum(self.strombedarf_hast_ges_kW, axis=0)

    def load_net_results(self, folder_path):
        """
        Load network simulation results from CSV file.

        Parameters
        ----------
        folder_path : str
            Path to project folder.
        """
        results_csv_filepath = os.path.join(folder_path, self.config_manager.get_relative_path("load_profile_path"))
        plot_data = import_results_csv(results_csv_filepath)
        self.time_steps, self.waerme_ges_kW, self.strom_wp_kW, self.pump_results = plot_data

    def display_data_in_table(self):
        """Display loaded variant data in comparison table."""
        # Clear the table first
        self.tableWidget.clear()

        # Define the headers
        # split the base path to only show the last folder name
        self.folder_names = [os.path.basename(folder_path) for folder_path in self.folder_paths]
        headers = ["Metric"] + [f"{folder_name}" for folder_name in self.folder_names]

        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setHorizontalHeaderLabels(headers)

        # Collect the ordered metrics based on the first dictionary (assuming all dictionaries have the same structure)
        if self.variant_data:
            ordered_metrics = list(self.variant_data[0].keys())

            # Set the number of rows
            self.tableWidget.setRowCount(len(ordered_metrics))

            # Populate the table
            for row, metric in enumerate(ordered_metrics):
                self.tableWidget.setItem(row, 0, QTableWidgetItem(metric))
                for col, data in enumerate(self.variant_data):
                    value = data.get(metric, "N/A")
                    if isinstance(value, (float, int)):
                        value = f"{value:.2f}"  # np.Round the numbers to 2 decimal places
                    self.tableWidget.setItem(row, col + 1, QTableWidgetItem(str(value)))

            self.tableWidget.resizeColumnsToContents()