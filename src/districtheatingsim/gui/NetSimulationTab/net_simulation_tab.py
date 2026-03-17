"""
Net Simulation Tab
==================

Orchestrator widget for district heating network simulation.

Wires together :class:`NetworkPlotWidget`, :class:`NetworkInfoPanel`,
:class:`PipeConfigTable`, and :class:`TimeSeriesWidget`.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import logging
import os
import csv
import json
import traceback

import numpy as np
import pandas as pd
import pandapipes as pp
import matplotlib.pyplot as plt

from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QMessageBox, QProgressBar, QMenuBar, QApplication,
)
from PyQt6.QtGui import QAction

from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import (
    save_results_csv, import_results_csv,
)
from districtheatingsim.net_simulation_pandapipes.utilities import export_net_geojson
from districtheatingsim.net_simulation_pandapipes.NetworkDataClass import NetworkGenerationData

from districtheatingsim.gui.NetSimulationTab.timeseries_dialog import TimeSeriesCalculationDialog
from districtheatingsim.gui.NetSimulationTab.net_generation_dialog import NetGenerationDialog
from districtheatingsim.gui.NetSimulationTab.net_calculation_threads import (
    NetInitializationThread, NetCalculationThread,
)
from districtheatingsim.gui.NetSimulationTab.network_plot_widget import NetworkPlotWidget
from districtheatingsim.gui.NetSimulationTab.network_info_panel import NetworkInfoPanel
from districtheatingsim.gui.NetSimulationTab.pipe_config_table import PipeConfigTable
from districtheatingsim.gui.NetSimulationTab.time_series_widget import TimeSeriesWidget


class NetSimulationTab(QWidget):
    """
    Network simulation tab for district heating system calculations.

    Provides interface for network generation, time series simulation, and
    visualization of heating network data using pandapipes.
    """

    data_added = pyqtSignal(object)

    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initialize the net simulation tab.

        :param folder_manager: Project folder manager.
        :param data_manager: Application data manager.
        :param config_manager: Configuration manager.
        :param parent: Parent widget.
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager
        plt.style.use('seaborn-v0_8-darkgrid')

        self.folder_manager.project_folder_changed.connect(self._update_base_path)
        self._update_base_path(self.folder_manager.variant_folder)

        self.NetworkGenerationData = None
        self._init_thread = None
        self._calc_thread = None

        self._init_ui()

    # ------------------------------------------------------------------
    # Path management
    # ------------------------------------------------------------------

    def _update_base_path(self, new_base_path):
        self.base_path = new_base_path

    # kept for backward compatibility (called by external code)
    def updateDefaultPath(self, new_base_path):
        self._update_base_path(new_base_path)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        container = QWidget()
        scroll_area.setWidget(container)
        self._container_layout = QVBoxLayout(container)

        self._init_menu_bar()
        self._init_content_area()

        main = QVBoxLayout(self)
        main.addWidget(scroll_area)
        self.setLayout(main)

    def _init_menu_bar(self):
        menubar = QMenuBar(self)
        menubar.setFixedHeight(30)

        file_menu = menubar.addMenu('Datei')
        net_menu = menubar.addMenu('Wärmenetz generieren')
        calc_menu = menubar.addMenu('Zeitreihenberechnung durchführen')

        save_action = QAction('Pandapipes Netz speichern', self)
        load_action = QAction('Pandapipes Netz laden', self)
        load_results_action = QAction('Ergebnisse Zeitreihenrechnung Laden', self)
        export_action = QAction('Pandapipes Netz als geoJSON exportieren', self)
        file_menu.addAction(save_action)
        file_menu.addAction(load_action)
        file_menu.addAction(load_results_action)
        file_menu.addAction(export_action)

        generate_action = QAction('Netz generieren', self)
        net_menu.addAction(generate_action)

        calc_action = QAction('Zeitreihenberechnung', self)
        calc_menu.addAction(calc_action)

        self._container_layout.addWidget(menubar)

        save_action.triggered.connect(self.saveNet)
        load_action.triggered.connect(self.loadNet)
        load_results_action.triggered.connect(self.load_net_results)
        export_action.triggered.connect(self.exportNetGeoJSON)
        generate_action.triggered.connect(self.openNetGenerationDialog)
        calc_action.triggered.connect(self.opencalculateNetDialog)

    def _init_content_area(self):
        inner_scroll = QScrollArea()
        inner_widget = QWidget()
        inner_scroll.setWidget(inner_widget)
        inner_scroll.setWidgetResizable(True)
        inner_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        inner_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        vbox = QVBoxLayout(inner_widget)

        # ---- Top row: network plot (left) + info panel (right) ----
        top_row = QHBoxLayout()

        self._net_plot = NetworkPlotWidget()
        top_row.addWidget(self._net_plot, 7)

        # Info panel + progress bar in a fixed-height container
        right_container = QWidget()
        right_container.setMinimumHeight(540)
        right_container.setMaximumHeight(540)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(5, 5, 5, 5)

        self._info_panel = NetworkInfoPanel()
        right_layout.addWidget(self._info_panel, 1)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(25)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        right_layout.addWidget(self._progress_bar)

        top_row.addWidget(right_container, 3)
        vbox.addLayout(top_row)

        # ---- Middle: pipe config table ----
        self._pipe_table = PipeConfigTable()
        self._pipe_table._recalc_btn.clicked.connect(self.recalculateNetwork)
        vbox.addWidget(self._pipe_table)

        # ---- Bottom: time series plot ----
        self._ts_widget = TimeSeriesWidget()
        vbox.addWidget(self._ts_widget)

        inner_scroll.setWidget(inner_widget)
        self._container_layout.addWidget(inner_scroll)

        # Wire inter-widget signals
        self._net_plot.pipe_selected.connect(self._pipe_table.select_pipe)
        self._pipe_table.pipe_highlight_requested.connect(self._net_plot.highlight_pipe)

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def openNetGenerationDialog(self):
        """Open network generation dialog."""
        try:
            dialog = NetGenerationDialog(
                self.generateNetworkCallback, self.base_path, self
            )
            dialog.exec()
        except Exception as e:
            logging.error(f"Fehler beim öffnen des Dialogs aufgetreten: {e}")
            QMessageBox.critical(self, "Fehler", f"Fehler beim öffnen des Dialogs aufgetreten: {e}")

    def generateNetworkCallback(self, network_data):
        """
        Handle network generation callback.

        :param network_data: NetworkGenerationData instance.
        """
        self.NetworkGenerationData = network_data
        if self.NetworkGenerationData.import_type == "GeoJSON":
            self._create_and_initialize_net_geojson()

    def opencalculateNetDialog(self):
        """Open time series calculation dialog."""
        dialog = TimeSeriesCalculationDialog(self.base_path, self)
        if dialog.exec():
            inputs = dialog.getValues()
            self.NetworkGenerationData.start_time_step = inputs["start"]
            self.NetworkGenerationData.end_time_step = inputs["end"]
            self.NetworkGenerationData.results_csv_filename = inputs["results_filename"]
            self.NetworkGenerationData.simplified_calculation = inputs["simplified"]
            self._time_series_simulation()

    # ------------------------------------------------------------------
    # Network initialization
    # ------------------------------------------------------------------

    def _create_and_initialize_net_geojson(self):
        self.NetworkGenerationData.COP_filename = self.data_manager.cop_filename
        self.NetworkGenerationData.TRY_filename = self.data_manager.try_filename

        self._init_thread = NetInitializationThread(self.NetworkGenerationData)
        self._init_thread.calculation_done.connect(self._on_initialization_done)
        self._init_thread.calculation_error.connect(self._on_simulation_error)
        self._init_thread.start()
        self._progress_bar.setRange(0, 0)

    def _on_initialization_done(self, network_data):
        self._progress_bar.setRange(0, 1)
        self.NetworkGenerationData = network_data
        self._refresh_all_widgets()

    # ------------------------------------------------------------------
    # Time series simulation
    # ------------------------------------------------------------------

    def _time_series_simulation(self):
        if self.NetworkGenerationData is None:
            QMessageBox.warning(self, "Keine Netzdaten", "Bitte generieren Sie zuerst ein Netz.")
            return

        try:
            simplified = getattr(self.NetworkGenerationData, 'simplified_calculation', False)
            self._calc_thread = NetCalculationThread(self.NetworkGenerationData, simplified=simplified)
            self._calc_thread.calculation_done.connect(self._on_time_series_done)
            self._calc_thread.calculation_error.connect(self._on_simulation_error)
            self._calc_thread.start()
            self._progress_bar.setRange(0, 0)
        except ValueError as e:
            QMessageBox.warning(self, "Ungültige Eingabe", str(e))

    def _on_time_series_done(self, network_data):
        self._progress_bar.setRange(0, 1)
        self.NetworkGenerationData = network_data
        self._refresh_all_widgets()

        save_results_csv(
            self.NetworkGenerationData.yearly_time_steps[
                self.NetworkGenerationData.start_time_step:self.NetworkGenerationData.end_time_step
            ],
            self.NetworkGenerationData.waerme_ges_kW[
                self.NetworkGenerationData.start_time_step:self.NetworkGenerationData.end_time_step
            ],
            self.NetworkGenerationData.strombedarf_ges_kW[
                self.NetworkGenerationData.start_time_step:self.NetworkGenerationData.end_time_step
            ],
            self.NetworkGenerationData.pump_results,
            self.NetworkGenerationData.results_csv_filename,
        )

    def _on_simulation_error(self, error_message):
        QMessageBox.critical(self, "Berechnungsfehler", str(error_message))
        self._progress_bar.setRange(0, 1)

    # ------------------------------------------------------------------
    # Widget refresh
    # ------------------------------------------------------------------

    def _refresh_all_widgets(self):
        """Refresh all sub-widgets from current NetworkGenerationData."""
        nd = self.NetworkGenerationData
        self._net_plot.set_network(nd)
        self._pipe_table.populate(nd)
        nd.prepare_plot_data()
        self._ts_widget.update(nd)
        self._info_panel.update(nd)

    # ------------------------------------------------------------------
    # Recalculate
    # ------------------------------------------------------------------

    def recalculateNetwork(self):
        """Recalculate network with current pipe parameters (pipeflow only)."""
        if not self.NetworkGenerationData or not hasattr(self.NetworkGenerationData, 'net'):
            QMessageBox.warning(
                self,
                "Kein Netz vorhanden",
                "Es muss zuerst ein Netz generiert werden, bevor neu berechnet werden kann.",
            )
            return

        try:
            from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import run_control

            self._pipe_table.apply_changes_to_net()

            self._progress_bar.setVisible(True)
            self._progress_bar.setValue(0)
            self._progress_bar.setFormat("Führe thermohydraulische Berechnung durch...")
            QApplication.processEvents()

            self._progress_bar.setValue(30)
            QApplication.processEvents()
            pp.pipeflow(self.NetworkGenerationData.net, mode="bidirectional", iter=100)

            self._progress_bar.setValue(60)
            QApplication.processEvents()
            run_control(self.NetworkGenerationData.net, mode="bidirectional", iter=100)

            self._progress_bar.setValue(90)
            QApplication.processEvents()

            self._net_plot.set_network(self.NetworkGenerationData)
            self._info_panel.update(self.NetworkGenerationData)

            self._progress_bar.setValue(100)
            self._progress_bar.setFormat("Berechnung abgeschlossen")
            QApplication.processEvents()

            QTimer.singleShot(1000, lambda: self._progress_bar.setVisible(False))

            QMessageBox.information(
                self,
                "Berechnung abgeschlossen",
                "Die thermohydraulische Berechnung wurde erfolgreich durchgeführt.\n\n"
                "Das Netzwerk wurde mit den aktuellen Rohrleitungsparametern neu berechnet.",
            )

        except Exception as e:
            logging.error(f"Error recalculating network: {e}\n{traceback.format_exc()}")
            self._progress_bar.setVisible(False)
            QMessageBox.critical(
                self,
                "Berechnungsfehler",
                f"Fehler bei der Netzberechnung:\n\n{str(e)}\n\n"
                "Überprüfen Sie die Rohrleitungsparameter und Randbedingungen.",
            )

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def saveNet(self, show_dialog=True):
        """
        Save network data to pickle, CSV, and JSON files.

        :param show_dialog: Show success/error dialogs.
        """
        if not self.NetworkGenerationData:
            if show_dialog:
                QMessageBox.warning(self, "Keine Daten", "Kein Pandapipes-Netzwerk zum Speichern vorhanden.")
            return

        try:
            pickle_path = os.path.join(self.base_path, self.config_manager.get_relative_path('pp_pickle_file_path'))
            csv_path = os.path.join(self.base_path, self.config_manager.get_relative_path('csv_net_init_file_path'))
            json_path = os.path.join(self.base_path, self.config_manager.get_relative_path('json_net_init_file_path'))

            nd = self.NetworkGenerationData
            orig_cop = nd.COP_filename
            orig_try = nd.TRY_filename

            if nd.COP_filename and os.path.isabs(nd.COP_filename):
                nd.COP_filename = os.path.relpath(nd.COP_filename, self.base_path)
            if nd.TRY_filename and os.path.isabs(nd.TRY_filename):
                nd.TRY_filename = os.path.relpath(nd.TRY_filename, self.base_path)

            pp.to_pickle(nd.net, pickle_path)

            waerme_data = np.column_stack([nd.waerme_hast_ges_W[i] for i in range(nd.waerme_hast_ges_W.shape[0])])
            waerme_df = pd.DataFrame(
                waerme_data, index=nd.yearly_time_steps,
                columns=[f'waerme_hast_ges_W_{i+1}' for i in range(nd.waerme_hast_ges_W.shape[0])],
            )
            strom_data = np.column_stack([nd.strombedarf_hast_ges_W[i] for i in range(nd.strombedarf_hast_ges_W.shape[0])])
            strom_df = pd.DataFrame(
                strom_data, index=nd.yearly_time_steps,
                columns=[f'strombedarf_hast_ges_W_{i+1}' for i in range(nd.strombedarf_hast_ges_W.shape[0])],
            )
            combined = pd.concat([waerme_df, strom_df], axis=1)
            combined.to_csv(csv_path, sep=';', date_format='%Y-%m-%dT%H:%M:%S', encoding='utf-8-sig')

            meta = nd.to_dict()
            for key in ('net', 'waerme_hast_ges_W', 'strombedarf_hast_ges_W',
                        'waerme_hast_ges_kW', 'strombedarf_hast_ges_kW',
                        'waerme_ges_kW', 'strombedarf_ges_kW',
                        'yearly_time_steps', 'pump_results', 'plot_data'):
                meta.pop(key, None)
            with open(json_path, 'w') as jf:
                json.dump(meta, jf, indent=4, default=str)

            nd.COP_filename = orig_cop
            nd.TRY_filename = orig_try

            if show_dialog:
                QMessageBox.information(
                    self, "Speichern erfolgreich",
                    f"✓ Pandapipes Netz erfolgreich gespeichert!\n\n"
                    f"Dateien:\n"
                    f"  • {os.path.basename(pickle_path)}\n"
                    f"  • {os.path.basename(csv_path)}\n"
                    f"  • {os.path.basename(json_path)}\n\n"
                    f"Pfad: {os.path.dirname(pickle_path)}",
                )
        except Exception as e:
            if show_dialog:
                QMessageBox.critical(self, "Speichern fehlgeschlagen", f"Fehler beim Speichern der Daten:\n\n{str(e)}")

    def loadNet(self, show_dialog=True):
        """
        Load network data from saved files.

        :param show_dialog: Show success/error dialogs.
        """
        try:
            pickle_path = os.path.join(self.base_path, self.config_manager.get_relative_path('pp_pickle_file_path'))
            csv_path = os.path.join(self.base_path, self.config_manager.get_relative_path('csv_net_init_file_path'))
            json_path = os.path.join(self.base_path, self.config_manager.get_relative_path('json_net_init_file_path'))

            net = pp.from_pickle(pickle_path)

            with open(csv_path, newline='') as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                headers = next(reader)
                n_waerme = len([h for h in headers if h.startswith('waerme_hast_ges_W')])
                n_strom = len([h for h in headers if h.startswith('strombedarf_hast_ges_W')])

                time_steps, waerme_rows, strom_rows = [], [], []
                for row in reader:
                    time_steps.append(np.datetime64(row[0]))
                    waerme_rows.append([float(v) for v in row[1:n_waerme + 1]])
                    strom_rows.append([float(v) for v in row[n_waerme + 1:n_waerme + n_strom + 1]])

                yearly_time_steps = np.array(time_steps)
                waerme_hast_ges_W = np.array(waerme_rows).transpose()
                strombedarf_hast_ges_W = np.array(strom_rows).transpose()

            with open(json_path, 'r') as jf:
                meta = json.load(jf)

            nd = NetworkGenerationData.from_dict(meta)

            if nd.COP_filename and not os.path.isabs(nd.COP_filename):
                nd.COP_filename = os.path.normpath(os.path.join(self.base_path, nd.COP_filename))
            if nd.TRY_filename and not os.path.isabs(nd.TRY_filename):
                nd.TRY_filename = os.path.normpath(os.path.join(self.base_path, nd.TRY_filename))

            nd.net = net
            nd.waerme_hast_ges_W = waerme_hast_ges_W
            nd.strombedarf_hast_ges_W = strombedarf_hast_ges_W
            nd.yearly_time_steps = yearly_time_steps
            nd.waerme_hast_ges_kW = np.where(waerme_hast_ges_W == 0, 0, waerme_hast_ges_W / 1000)
            nd.strombedarf_hast_ges_kW = np.where(strombedarf_hast_ges_W == 0, 0, strombedarf_hast_ges_W / 1000)
            nd.waerme_ges_kW = np.sum(nd.waerme_hast_ges_kW, axis=0)
            nd.strombedarf_ges_kW = np.sum(nd.strombedarf_hast_ges_kW, axis=0)

            self.NetworkGenerationData = nd
            self._refresh_all_widgets()

            if show_dialog:
                QMessageBox.information(
                    self, "Laden erfolgreich",
                    f"✓ Netz erfolgreich geladen!\n\n"
                    f"Dateien:\n"
                    f"  • {os.path.basename(pickle_path)}\n"
                    f"  • {os.path.basename(csv_path)}\n"
                    f"  • {os.path.basename(json_path)}\n\n"
                    f"Pfad: {os.path.dirname(pickle_path)}",
                )

        except Exception as e:
            tb = traceback.format_exc()
            if show_dialog:
                QMessageBox.critical(self, "Laden fehlgeschlagen", f"Fehler beim Laden der Daten:\n\n{str(e)}")
            else:
                logging.error(f"Fehler beim Laden der Netzwerk-Daten: {e}\n{tb}")

    def load_net_results(self, show_dialog=True):
        """
        Load network simulation results from CSV file.

        :param show_dialog: Show warning dialogs.
        """
        if self.NetworkGenerationData:
            results_path = os.path.join(
                self.base_path,
                self.config_manager.get_relative_path('load_profile_path'),
            )
            _, self.NetworkGenerationData.waerme_ges_kW, \
                self.NetworkGenerationData.strombedarf_ges_kW, \
                self.NetworkGenerationData.pump_results = import_results_csv(results_path)

            self.NetworkGenerationData.prepare_plot_data()
            self._ts_widget.update(self.NetworkGenerationData)
            self._info_panel.update(self.NetworkGenerationData)
        elif show_dialog:
            QMessageBox.warning(self, "Keine Daten", "Kein Pandapipes-Netzwerk zum Laden vorhanden.")

    def exportNetGeoJSON(self, show_dialog=True):
        """
        Export dimensioned network to unified GeoJSON format.

        :param show_dialog: Show success/error dialogs.
        """
        if not self.NetworkGenerationData or not hasattr(self.NetworkGenerationData, 'net'):
            if show_dialog:
                QMessageBox.warning(
                    self, "Kein Netz vorhanden",
                    "Es muss zuerst ein Netz generiert werden, bevor es exportiert werden kann.",
                )
            return

        try:
            unified_path = os.path.join(
                self.base_path,
                self.config_manager.get_relative_path('dimensioned_net_path'),
            )
            feature_counts = export_net_geojson(self.NetworkGenerationData.net, unified_path)

            if show_dialog:
                total = sum(feature_counts.values())
                QMessageBox.information(
                    self, "Export erfolgreich",
                    f"✓ Wärmenetz erfolgreich exportiert!\n\n"
                    f"Datei: {os.path.basename(unified_path)}\n"
                    f"Pfad: {os.path.dirname(unified_path)}\n\n"
                    f"Exportierte Features:\n"
                    f"  • Vorlauf: {feature_counts['flow']}\n"
                    f"  • Rücklauf: {feature_counts['return']}\n"
                    f"  • Gebäudeanschlüsse: {feature_counts['building']}\n"
                    f"  • Erzeuger: {feature_counts['generator']}\n"
                    f"  • Gesamt: {total} Features",
                )
        except Exception as e:
            if show_dialog:
                QMessageBox.critical(self, "Export fehlgeschlagen",
                                     f"Fehler beim Exportieren des Wärmenetzes:\n\n{str(e)}")
            else:
                logging.error(f"Fehler beim Exportieren des Wärmenetzes: {e}")

    # ------------------------------------------------------------------
    # Helper kept for compatibility (used by data_added consumers)
    # ------------------------------------------------------------------

    def get_data_path(self):
        """Return absolute path to the application data directory."""
        project_base = os.path.dirname(os.path.dirname(self.base_path))
        return os.path.join(project_base, "src", "districtheatingsim", "data")
