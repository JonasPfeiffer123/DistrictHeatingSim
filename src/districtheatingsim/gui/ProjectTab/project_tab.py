"""Project Tab Module
==================

Project management tab with MVP architecture for CSV file editing and project tracking.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import csv
import json
import logging
import os

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFileSystemModel
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from districtheatingsim.geocoding.building_csv import centroid_of, geojson_to_building_csv
from districtheatingsim.geocoding.geocoding import format_geocoding_summary
from districtheatingsim.gui.LeafletTab.net_generation_threads import GeocodingThread, GeoJSONToCSVThread
from districtheatingsim.gui.MainTab.project_structure import discover_variants
from districtheatingsim.gui.ProjectTab.csv_import_dialog import CsvImportDialog
from districtheatingsim.gui.ProjectTab.project_progress import evaluate_process_steps
from districtheatingsim.gui.ProjectTab.project_tab_dialogs import OSMImportDialog, ProcessDetailsDialog, RowInputDialog
from districtheatingsim.gui.utilities import any_thread_running
from districtheatingsim.utilities.crs_utils import (
    COMMON_CRS_OPTIONS,
    outside_crs_area,
    read_building_coordinates,
    reproject_building_csv,
    suggest_crs_for_coordinates,
)

logger = logging.getLogger(__name__)


def _same_file(path_a, path_b) -> bool:
    """True if both paths name the same file (case- and ``..``-insensitive)."""
    if not path_a or not path_b:
        return False
    return os.path.normcase(os.path.abspath(str(path_a))) == os.path.normcase(os.path.abspath(str(path_b)))


class ProjectModel:
    """
    Model for managing project data including CSV and GeoJSON file operations.
    """

    def __init__(self):
        self.base_path = None
        self.current_file_path = ""
        self.layers = {}

    def load_csv(self, file_path):
        """
        Load CSV file data.

        :param file_path: Path to CSV file.
        :type file_path: str
        :return: Headers and data lists.
        :rtype: tuple
        """
        # utf-8-sig: the files are written with a BOM. Reading them as plain utf-8 kept the BOM in
        # the first header, and every save added another one (BACKLOG UT-H7); lstrip repairs
        # files that already collected several.
        with open(file_path, encoding="utf-8-sig") as file:
            reader = csv.reader(file, delimiter=";")
            headers = next(reader)
            data = [row for row in reader]
        if headers:
            headers[0] = headers[0].lstrip("\ufeff")
        return headers, data

    def save_csv(self, file_path, headers, data):
        """
        Save data to CSV file.

        :param file_path: Output file path.
        :type file_path: str
        :param headers: Column headers.
        :type headers: list
        :param data: Table data.
        :type data: list of lists
        """
        with open(file_path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(headers)
            writer.writerows(data)

    def create_csv(self, file_path, headers, default_data):
        """
        Create new CSV file with default data.

        :param file_path: Output file path.
        :type file_path: str
        :param headers: Column headers.
        :type headers: list
        :param default_data: Default row data.
        :type default_data: list
        """
        with open(file_path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(headers)
            writer.writerow(default_data)

    def create_csv_from_geojson(self, geojson_file_path, output_file_path, default_values, project_crs="EPSG:25833"):
        """
        Create the building CSV from a GeoJSON (thin wrapper over the GUI-free
        :func:`districtheatingsim.geocoding.building_csv.geojson_to_building_csv`).

        :param geojson_file_path: Input GeoJSON file path.
        :param output_file_path: Output CSV file path.
        :param default_values: Default values for building parameters.
        :param project_crs: CRS of the GeoJSON coordinates.
        :return: Output file path.
        :rtype: str
        """
        return geojson_to_building_csv(geojson_file_path, output_file_path, default_values, project_crs)

    def calculate_centroid(self, coordinates):
        """
        Calculate centroid of a (possibly nested) coordinate array.

        Thin wrapper over the GUI-free :func:`centroid_of`.

        :param coordinates: Coordinate array.
        :type coordinates: list
        :return: Centroid coordinates (x, y).
        :rtype: tuple
        """
        return centroid_of(coordinates)


class ProjectPresenter:
    """
    Presenter managing interaction between ProjectModel and ProjectTabView.
    """

    def __init__(self, model, view, folder_manager, data_manager, config_manager):
        """
        Initialize project presenter.

        :param model: Data model.
        :type model: ProjectModel
        :param view: View component.
        :type view: ProjectTabView
        :param folder_manager: Folder manager.
        :type folder_manager: object
        :param data_manager: Data manager.
        :type data_manager: object
        :param config_manager: Configuration manager.
        :type config_manager: object
        """
        self.model = model
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        # Define process steps for project tracking
        self.process_steps = [
            {
                "name": "Schritt 1: Gebäudedaten Quartier definieren",
                "description": "Erstellen Sie die Gebäude-CSV hier im Tab 'Projektdefinition'. Die CSV kann manuell erstellt, aus GeoJSON importiert oder durch Geocoding mit Koordinaten angereichert werden.",
                "required_files": ["../Definition Quartier IST/Quartier IST.csv"],
                "csv_creation_status": "not_checked",  # Will be updated dynamically
                "geocoding_status": "not_checked",  # Will be updated dynamically
            },
            {
                "name": "Schritt 2: Gebäude-Lastgang generieren",
                "description": "Generieren Sie den Gebäude-Lastgang im Tab 'Wärmebedarf Gebäude' ",
                # Current Parquet file, or the JSON of projects saved before BACKLOG G7
                "required_files": [["Lastgang/Gebäude Lastgang.parquet", "Lastgang/Gebäude Lastgang.json"]],
            },
            {
                "name": "Schritt 3: Straßendaten herunterladen",
                "description": "Führen Sie eine OSM-Straßenabfrage im Tab 'Wärmenetz generieren' durch.",
                "required_files": ["../Eingangsdaten allgemein/Straßen.geojson"],
            },
            {
                "name": "Schritt 3: Wärmenetz Daten erstellen",
                "description": "Generieren Sie das Wärmenetz im Tab 'Wärmenetz generieren'.",
                "required_files": ["Wärmenetz/Wärmenetz.geojson"],
            },
            {
                "name": "Schritt 4: Thermohydraulische Berechnung",
                "description": "Führen Sie die Thermohydraulische Berechnung mit den generierten Netzdaten durch.",
                "required_files": [
                    # Current JSON, or the pickle of projects saved before BACKLOG G7
                    ["Wärmenetz/Ergebnisse Netzinitialisierung.json", "Wärmenetz/Ergebnisse Netzinitialisierung.p"],
                    "Wärmenetz/Ergebnisse Netzinitialisierung.csv",
                    "Wärmenetz/Konfiguration Netzinitialisierung.json",
                    "Lastgang/Lastgang.csv",
                ],
                "check_dimensioned_network": True,  # Special check for dimensioned flag in Wärmenetz.geojson
            },
            {
                "name": "Schritt 5: Erzeugermix auslegen und berechnen",
                "description": "Berechnen sie den Erzeugermix und speichern sie die Ergebnisse.",
                "required_files": [
                    "Ergebnisse/calculated_heat_generation.csv",
                    ["Ergebnisse/Ergebnisse.parquet", "Ergebnisse/Ergebnisse.json"],
                ],
            },
        ]

        # Connect signals and initialize (only after view is set)
        self.folder_manager.project_folder_changed.connect(self.on_variant_folder_changed)

        # Progress update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress_tracker)
        self.timer.start(50000)

    def connect_view_signals(self):
        """
        Connect view signals after view is created.
        """
        if self.view:
            self.view.treeView.doubleClicked.connect(self.on_tree_view_double_clicked)

            # Synchronise CRS selector with current project CRS and listen for changes
            self.view.set_crs(self.folder_manager.project_crs)
            self.view.crs_combo.currentTextChanged.connect(self._on_crs_combo_changed)
            self.folder_manager.crs_changed.connect(self.view.set_crs)
            self.view.suggest_crs_button.clicked.connect(self._suggest_crs)

            # Synchronise calculation year spinbox
            self.view.year_spinbox.setValue(self.folder_manager.calculation_year)
            self.view.year_spinbox.valueChanged.connect(self.folder_manager.set_calculation_year)

            # Initial update after view is available
            if self.folder_manager.variant_folder:
                self.on_variant_folder_changed(self.folder_manager.variant_folder)
            self.update_progress_tracker()

    def on_variant_folder_changed(self, path):
        """
        Handle project folder change.

        :param path: New project folder path.
        :type path: str
        """
        if path:
            self.model.base_path = path
            if self.view:  # Only update if view exists
                self.view.update_tree_view(os.path.dirname(path))
                # Sync year spinbox without triggering save
                self.view.year_spinbox.blockSignals(True)
                self.view.year_spinbox.setValue(self.folder_manager.calculation_year)
                self.view.year_spinbox.blockSignals(False)
        if self.view:  # Only update progress if view exists
            self.update_progress_tracker()

    def on_tree_view_double_clicked(self, index):
        """
        Handle double-click on file tree view.

        :param index: Tree view index.
        :type index: QModelIndex
        """
        file_path = self.view.get_selected_file_path(index)

        if os.path.isdir(file_path):
            # Only a variant folder of the open project switches the variant - through the main
            # window, which asks to save and loads the variant's results. Any other folder just
            # expands; making it the project folder dropped TRY/COP/CRS (UT-H8).
            variant = self._variant_of_folder(file_path)
            if variant:
                self.view.variantRequested.emit(variant)
        elif file_path.endswith(".csv"):
            self.load_csv(file_path)

    def _variant_of_folder(self, folder: str) -> str | None:
        """Name of the variant ``folder`` is, if it is another variant of the open project."""
        project = self.folder_manager.project_folder
        if not project:
            return None
        folder = os.path.normcase(os.path.normpath(folder))
        if os.path.dirname(folder) != os.path.normcase(os.path.normpath(project)):
            return None
        current = self.folder_manager.variant_folder
        if current and folder == os.path.normcase(os.path.normpath(current)):
            return None
        names = {os.path.normcase(name): name for name in discover_variants(project)}
        return names.get(os.path.basename(folder))

    def _building_csv_path(self) -> str:
        """Path of the project's building CSV (``Quartier IST.csv``), normalised."""
        return os.path.normpath(
            os.path.join(
                self.folder_manager.get_variant_folder(),
                self.config_manager.get_relative_path("current_building_data_path"),
            )
        )

    def _on_crs_combo_changed(self, label: str):
        """Change the project CRS when the user selects a different entry in the combo box."""
        # The combo displays labels like "EPSG:25833 – ETRS89 …", extract code prefix
        code = label.split(" ")[0] if label else ""
        if code.upper().startswith("EPSG:"):
            self.change_project_crs(code)

    def change_project_crs(self, new_crs: str, reason: str = "") -> bool:
        """
        Switch the project CRS and convert the building coordinates along with it.

        The building CSV stores bare ``UTM_X``/``UTM_Y`` numbers that are read in the project CRS;
        switching the CRS without converting them moved every building by hundreds of kilometres
        (BACKLOG UT-K2). The user is asked first; "Abbrechen" keeps the old CRS.

        :param new_crs: Target CRS, e.g. ``"EPSG:25832"``.
        :param reason: Optional explanation shown above the question.
        :return: True if the CRS was changed.
        """
        old_crs = self.folder_manager.project_crs
        if not new_crs or new_crs == old_crs:
            return False
        csv_path = self._building_csv_path()
        xs, _ys = read_building_coordinates(csv_path)
        convert = False
        if len(xs):
            reply = QMessageBox.question(
                self.view,
                "Koordinatensystem ändern",
                f"{reason}Die {len(xs)} Gebäudekoordinaten in '{os.path.basename(csv_path)}' liegen in {old_crs}.\n\n"
                f"Sollen sie beim Wechsel nach {new_crs} umgerechnet werden? (empfohlen)\n\n"
                "Bereits erzeugte Straßen-, Gebäude- und Netzdateien behalten ihr Koordinatensystem; "
                "erzeugen Sie diese nach dem Wechsel neu.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                self.view.set_crs(old_crs)
                return False
            convert = reply == QMessageBox.StandardButton.Yes
        if convert:
            reproject_building_csv(csv_path, old_crs, new_crs)
            logger.info("Building coordinates converted %s -> %s (%s)", old_crs, new_crs, csv_path)
        self.folder_manager.set_project_crs(new_crs)
        self.view.set_crs(new_crs)
        if convert and _same_file(self.model.current_file_path, csv_path):
            self.load_csv(csv_path)
        return True

    def _suggest_crs(self):
        """Suggest the CRS that fits the building coordinates and offer to switch to it."""
        xs, ys = read_building_coordinates(self._building_csv_path())
        if not len(xs):
            self.view.show_message(
                "Koordinatensystem vorschlagen",
                "Die Gebäude-CSV enthält noch keine Koordinaten. Berechnen Sie zuerst die Geokoordinaten.",
            )
            return
        current = self.folder_manager.project_crs
        try:
            suggested = suggest_crs_for_coordinates(xs, ys, current)
        except Exception as e:
            logger.warning("CRS-Vorschlag aus den Koordinaten fehlgeschlagen: %s", e)
            return
        if suggested == current:
            self.view.show_message("Koordinatensystem vorschlagen", f"{current} passt bereits zu den Gebäuden.")
        else:
            self.change_project_crs(suggested, reason=f"Für den Ort der Gebäude passt {suggested}.\n\n")

    def _check_coordinates_fit_crs(self):
        """After geocoding: offer a fitting CRS if the coordinates lie outside the project CRS's area."""
        xs, ys = read_building_coordinates(self._building_csv_path())
        if not len(xs):
            return
        current = self.folder_manager.project_crs
        outside = int(outside_crs_area(xs, ys, current).sum())
        if outside:
            suggested = suggest_crs_for_coordinates(xs, ys, current)
            self.change_project_crs(
                suggested,
                reason=f"{outside} von {len(xs)} Gebäuden liegen außerhalb des Gültigkeitsbereichs von {current}. "
                f"Für diesen Ort passt {suggested}.\n\n",
            )

    def import_csv(self):
        """
        Open a CSV file, show the column-mapping dialog, and load the result.

        If the source CSV already uses the internal column schema (all required
        columns present with the expected names) it is loaded directly without
        showing the mapping dialog.  Otherwise the CsvImportDialog is shown so
        the user can assign source columns to target fields and supply default
        values for missing ones.
        """
        target_path = self._building_csv_path()
        fname, _ = QFileDialog.getOpenFileName(
            self.view, "CSV importieren", target_path, "CSV Files (*.csv);;All Files (*)"
        )
        if not fname or not fname.strip():
            return
        if _same_file(fname, target_path):
            self.load_csv(target_path)  # the project's own file: nothing to import
            return

        import pandas as pd

        from districtheatingsim.gui.ProjectTab.csv_import_dialog import TARGET_COLUMNS, _detect_delimiter

        # A file that already uses the internal column schema is taken over as it is; otherwise
        # the mapping dialog assigns the columns.
        df = None
        try:
            delim = _detect_delimiter(fname)
            probe = pd.read_csv(fname, delimiter=delim, encoding="utf-8-sig", nrows=0)
            required_cols = {tc[0] for tc in TARGET_COLUMNS if tc[2]}  # required only
            if required_cols.issubset(set(probe.columns)):
                df = pd.read_csv(fname, delimiter=delim, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        except Exception as e:
            # Best-effort fast path; fall through to the mapping dialog on any error.
            logger.debug("Direktes CSV-Laden nicht möglich, nutze Mapping-Dialog: %s", e)

        if df is None:
            dialog = CsvImportDialog(fname, parent=self.view)
            if dialog.exec() != CsvImportDialog.DialogCode.Accepted:
                return
            df = dialog.get_result()
            if df is None:
                return

        self._store_imported_buildings(df, target_path)

    def _store_imported_buildings(self, df, target_path: str) -> None:
        """
        Write imported buildings to the project's building CSV and show them.

        The import always lands in the project file: the fast path used to load the source file
        itself, so the project file stayed empty and "CSV speichern" / geocoding wrote into the
        user's original outside the project (BACKLOG UT-K3). Existing buildings are only replaced
        after a confirmation.

        :param df: Imported buildings in the internal column schema.
        :param target_path: The project's ``Quartier IST.csv``.
        """
        existing = self._count_buildings(target_path)
        if existing:
            reply = QMessageBox.question(
                self.view,
                "Gebäudeliste ersetzen",
                f"Die Gebäudeliste des Projekts enthält bereits {existing} Gebäude.\n\n"
                f"Sollen sie durch die {len(df)} importierten Gebäude ersetzt werden?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        try:
            df.to_csv(target_path, sep=";", index=False, encoding="utf-8-sig")
            self.load_csv(target_path)
            self.update_progress_tracker()
            QMessageBox.information(
                self.view,
                "Import erfolgreich",
                f"{len(df)} Gebäude importiert und gespeichert unter:\n{target_path}",
            )
        except Exception as e:
            QMessageBox.critical(self.view, "Fehler beim Speichern", str(e))

    def _count_buildings(self, csv_path: str) -> int:
        """Number of non-empty building rows in a building CSV (0 if it does not exist)."""
        if not os.path.exists(csv_path):
            return 0
        try:
            _headers, rows = self.model.load_csv(csv_path)
        except (OSError, UnicodeDecodeError, StopIteration):
            return 0
        return sum(1 for row in rows if any(cell.strip() for cell in row))

    def load_csv(self, file_path):
        """
        Load CSV file into table view.

        :param file_path: Path to CSV file.
        :type file_path: str
        """
        headers, data = self.model.load_csv(file_path)
        self.model.current_file_path = file_path
        self.view.csvTable.setRowCount(0)
        self.view.csvTable.setColumnCount(len(headers))
        self.view.csvTable.setHorizontalHeaderLabels(headers)
        for row_data in data:
            row = self.view.csvTable.rowCount()
            self.view.csvTable.insertRow(row)
            for column, cell_value in enumerate(row_data):
                item = QTableWidgetItem(cell_value)
                self.view.csvTable.setItem(row, column, item)

    def save_csv(self, show_dialog=True):
        """
        Save current table data to CSV file.

        :param show_dialog: Show confirmation dialog if True.
        :type show_dialog: bool
        """
        headers = [self.view.csvTable.horizontalHeaderItem(i).text() for i in range(self.view.csvTable.columnCount())]
        data = [
            [
                self.view.csvTable.item(row, column).text() if self.view.csvTable.item(row, column) else ""
                for column in range(self.view.csvTable.columnCount())
            ]
            for row in range(self.view.csvTable.rowCount())
        ]
        file_path = self.model.current_file_path
        if not file_path:
            # Use default path if no file is open
            file_path = os.path.join(
                self.folder_manager.get_variant_folder(),
                self.config_manager.get_relative_path("current_building_data_path"),
            )
            self.model.current_file_path = file_path
        try:
            self.model.save_csv(file_path, headers, data)
            if show_dialog:
                self.view.show_message("Erfolg", f"CSV-Datei wurde in {file_path} gespeichert.")
        except Exception as e:
            if show_dialog:
                self.view.show_error_message("Fehler", str(e))

    def add_row(self):
        """
        Add new empty row to table.
        """
        self.view.csvTable.insertRow(self.view.csvTable.rowCount())

    def del_row(self):
        """
        Delete selected row from table.
        """
        currentRow = self.view.csvTable.currentRow()
        if currentRow > -1:
            self.view.csvTable.removeRow(currentRow)
        else:
            self.view.show_error_message("Warnung", "Bitte wählen Sie eine Zeile zum Löschen aus.")

    def create_csv(self, fname=None, show_dialog=True):
        """
        Create new CSV file with default building data headers.

        :param fname: Optional file path.
        :type fname: str
        :param show_dialog: Show file dialog if True.
        :type show_dialog: bool
        """
        headers = [
            "Land",
            "Bundesland",
            "Stadt",
            "Adresse",
            "Wärmebedarf",
            "Gebäudetyp",
            "Subtyp",
            "WW_Anteil",
            "Typ_Heizflächen",
            "VLT_max",
            "Steigung_Heizkurve",
            "RLT_max",
            "Normaußentemperatur",
        ]
        default_data = [""] * len(headers)
        if not fname:
            fname = os.path.join(
                self.folder_manager.get_variant_folder(),
                self.config_manager.get_relative_path("current_building_data_path"),
            )
            if show_dialog:
                fname_dialog, _ = QFileDialog.getSaveFileName(
                    self.view, "Gebäude-CSV erstellen", fname, "CSV Files (*.csv);;All Files (*)"
                )
                if fname_dialog and fname_dialog.strip():  # Check for valid file path
                    fname = fname_dialog
                else:
                    return  # User cancelled dialog
        if fname and fname.strip():  # Additional check for valid filename
            self.model.create_csv(fname, headers, default_data)
            self.load_csv(fname)
            if show_dialog:
                self.view.show_message("Erfolg", f"CSV-Datei wurde in {fname} erstellt.")

    def create_csv_from_geojson(self):
        """
        Create CSV from GeoJSON with user-defined building parameters.
        """
        standard_path = os.path.join(
            self.folder_manager.get_variant_folder(), self.config_manager.get_relative_path("OSM_buldings_path")
        )
        geojson_file_path, _ = QFileDialog.getOpenFileName(
            self.view, "geoJSON auswählen", standard_path, "All Files (*)"
        )
        if geojson_file_path and geojson_file_path.strip():  # Check for valid file path
            # Extract sample coordinates from first building for reverse geocoding
            sample_coords = None
            try:
                with open(geojson_file_path) as f:
                    data = json.load(f)
                    if data.get("features") and len(data["features"]) > 0:
                        first_feature = data["features"][0]
                        centroid = self.model.calculate_centroid(first_feature["geometry"]["coordinates"])
                        if centroid[0] is not None and centroid[1] is not None:
                            sample_coords = centroid
            except Exception as e:
                # Best-effort; continue without sample coordinates.
                logger.debug("Konnte Beispielkoordinaten nicht extrahieren: %s", e)

            dialog = OSMImportDialog(
                self.view, sample_utm_coords=sample_coords, project_crs=self.folder_manager.project_crs
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                default_values = dialog.get_input_data()
                standard_output_path = os.path.join(
                    self.folder_manager.get_variant_folder(),
                    self.config_manager.get_relative_path("OSM_building_data_path"),
                )
                output_file_path = standard_output_path

                # Start conversion in thread
                if hasattr(self, "geojson_conversion_thread") and self.geojson_conversion_thread.isRunning():
                    self.geojson_conversion_thread.stop()
                    self.geojson_conversion_thread.wait()

                self.geojson_conversion_thread = GeoJSONToCSVThread(
                    geojson_file_path,
                    output_file_path,
                    default_values,
                    self.model,
                    project_crs=self.folder_manager.project_crs,
                )
                self.geojson_conversion_thread.progress_update.connect(self.on_geojson_conversion_progress)
                self.geojson_conversion_thread.calculation_done.connect(self.on_geojson_conversion_done)
                self.geojson_conversion_thread.calculation_error.connect(self.on_geojson_conversion_error)
                self.geojson_conversion_thread.start()

                # Show progress bar
                self.view.progressBar.setRange(0, 0)  # Indeterminate until we know total
                self.view.statusLabel.setText("Konvertiere GeoJSON zu CSV mit Reverse Geocoding...")

    def on_geojson_conversion_progress(self, current, total, message):
        """
        Handle progress updates from GeoJSON conversion thread.

        :param current: Current building number.
        :type current: int
        :param total: Total number of buildings.
        :type total: int
        :param message: Progress message.
        :type message: str
        """
        if total > 0:
            self.view.progressBar.setRange(0, total)
            self.view.progressBar.setValue(current)
        self.view.statusLabel.setText(message)

    def on_geojson_conversion_done(self, output_file_path):
        """
        Handle completion of GeoJSON conversion.

        :param output_file_path: Path to created CSV file.
        :type output_file_path: str
        """
        self.view.progressBar.setRange(0, 1)
        self.view.progressBar.setValue(1)
        self.view.statusLabel.setText("Konvertierung abgeschlossen")
        self.load_csv(output_file_path)
        self.view.show_message("Erfolg", f"CSV-Datei wurde erfolgreich erstellt:\n{output_file_path}")

    def on_geojson_conversion_error(self, error_message):
        """
        Handle error during GeoJSON conversion.

        :param error_message: Error message.
        :type error_message: str
        """
        self.view.progressBar.setRange(0, 1)
        self.view.progressBar.setValue(0)
        self.view.statusLabel.setText("Fehler bei der Konvertierung")
        self.view.show_error_message("Fehler", error_message)

    def geocode_current_csv(self):
        """
        Geocode the currently loaded CSV file.
        """
        if hasattr(self.model, "current_file_path") and self.model.current_file_path:
            # Save current table data first
            self.save_csv(show_dialog=False)
            # Then geocode the saved file
            self.geocode_addresses(self.model.current_file_path)
        else:
            self.view.show_error_message(
                "Fehler", "Keine CSV-Datei geladen. Bitte laden Sie zuerst eine CSV-Datei oder erstellen Sie eine neue."
            )

    def open_geocode_addresses_dialog(self):
        """
        Open file dialog for geocoding CSV selection.
        """
        standard_path = os.path.join(
            self.folder_manager.get_variant_folder(),
            self.config_manager.get_relative_path("current_building_data_path"),
        )
        fname, _ = QFileDialog.getOpenFileName(
            self.view, "CSV-Koordinaten laden", standard_path, "CSV Files (*.csv);;All Files (*)"
        )
        if fname and fname.strip():  # Check for valid file path
            self.geocode_addresses(fname)

    def geocode_addresses(self, inputfilename):
        """
        Start geocoding thread for address processing.

        :param inputfilename: Path to CSV file for geocoding.
        :type inputfilename: str
        """
        if hasattr(self, "geocodingThread") and self.geocodingThread.isRunning():
            # Cooperative stop (waits for the current run to finish) instead of
            # terminate(), which can kill the thread mid-write and truncate the CSV.
            self.geocodingThread.stop()
        self.geocodingThread = GeocodingThread(inputfilename, project_crs=self.folder_manager.project_crs)
        self.geocodingThread.calculation_done.connect(self.on_geocode_done)
        self.geocodingThread.calculation_error.connect(self.on_geocode_error)
        self.geocodingThread.start()
        self.view.progressBar.setRange(0, 0)

    def on_geocode_done(self, result):
        """
        Handle geocoding completion.

        :param result: Tuple of (filename, summary_dict) emitted by GeocodingThread.
        :type result: tuple
        """
        self.view.progressBar.setRange(0, 1)

        fname, summary = result

        # Automatically reload the updated CSV file to show the new coordinates
        if fname and os.path.exists(fname):
            self.load_csv(fname)
            # Update the progress tracker to refresh CSV status (should now show "mit Koordinaten")
            self.update_progress_tracker()
            all_found, message = format_geocoding_summary(summary)
            if all_found:
                self.view.show_message("Geocoding erfolgreich", message)
            else:
                QMessageBox.warning(self.view, "Geocoding: Einige Adressen nicht gefunden", message)
            if _same_file(fname, self._building_csv_path()):
                self._check_coordinates_fit_crs()

    def on_geocode_error(self, error_message):
        """
        Handle geocoding errors.

        :param error_message: Error message to display.
        :type error_message: str
        """
        self.view.show_error_message("Fehler beim Geocoding", error_message)
        self.view.progressBar.setRange(0, 1)

    def update_progress(self, progress, csv_status=None):
        """
        Update progress bar value and CSV status label.

        :param progress: Progress percentage.
        :type progress: float
        :param csv_status: Status text for Quartier IST.csv.
        :type csv_status: str
        """
        self.projectProgressBar.setValue(int(progress))
        if csv_status is not None:
            self.csv_status_label.setText(f"Quartier IST.csv Status: {csv_status}")

    def update_progress_tracker(self):
        """
        Update project progress and CSV status label based on file existence and content.

        The filesystem evaluation lives in the GUI-free
        :func:`districtheatingsim.gui.ProjectTab.project_progress.evaluate_process_steps`;
        this method just pushes its result into the view.
        """
        if not self.view:  # Skip if view not available yet
            return

        csv_status, overall_progress = evaluate_process_steps(self.model.base_path, self.process_steps)

        self.view.update_progress(overall_progress, csv_status=csv_status)
        self.view.set_process_steps(self.process_steps)


class ProjectTabView(QWidget):
    """
    View component for project tab UI with file browser and CSV editor.
    """

    #: Name of a variant the user double-clicked in the project tree (UT-H8).
    variantRequested = pyqtSignal(str)

    def __init__(self, presenter=None, parent=None):
        """
        Initialize project tab view.

        :param presenter: Presenter instance for signal connections.
        :type presenter: ProjectPresenter
        :param parent: Parent widget.
        :type parent: QWidget
        """
        super().__init__(parent)
        self.presenter = presenter
        self.initUI()

    def initUI(self):
        """
        Initialize user interface components.
        """
        mainLayout = QVBoxLayout()
        splitter = QSplitter()

        # Left area - file browser and progress
        self.leftLayout = QVBoxLayout()
        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.treeView = QTreeView()
        self.treeView.setModel(self.model)
        self.treeView.setMinimumWidth(500)
        self.treeView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Projektfortschritt oben
        self.progressLayout = QHBoxLayout()
        self.progressLabel = QLabel("Projektfortschritt:")
        self.progressLayout.addWidget(self.progressLabel)

        self.projectProgressBar = QProgressBar(self)
        self.progressLayout.addWidget(self.projectProgressBar)

        # Details Button
        self.detailsButton = QPushButton("Details Projektfortschritt anzeigen", self)
        self.detailsButton.setToolTip("Details zu den einzelnen Schritten anzeigen")
        self.detailsButton.clicked.connect(self.showDetailsDialog)
        self.progressLayout.addWidget(self.detailsButton)

        self.leftLayout.addLayout(self.progressLayout)

        # CSV-Status oben
        self.csv_status_label = QLabel("❓ Quartier IST.csv: Status unbekannt")
        self.csv_status_label.setStyleSheet(
            "font-weight: bold; color: #757575; background-color: #f5f5f5; padding: 8px; border-radius: 4px; border-left: 4px solid #757575; margin-bottom: 10px;"
        )
        self.leftLayout.addWidget(self.csv_status_label)

        # CRS selector row
        crs_row = QHBoxLayout()
        crs_row.addWidget(QLabel("Koordinatensystem (CRS):"))
        self.crs_combo = QComboBox()
        self.crs_combo.setMinimumWidth(380)
        for code, label in COMMON_CRS_OPTIONS:
            self.crs_combo.addItem(f"{code} – {label.split('–', 1)[-1].strip()}", userData=code)
        crs_row.addWidget(self.crs_combo)
        self.suggest_crs_button = QPushButton("Vorschlagen")
        self.suggest_crs_button.setToolTip("CRS anhand der ersten Gebäudekoordinaten automatisch vorschlagen")
        crs_row.addWidget(self.suggest_crs_button)
        crs_row.addStretch()
        self.leftLayout.addLayout(crs_row)

        # Calculation year row
        year_row = QHBoxLayout()
        year_row.addWidget(QLabel("Berechnungsjahr (BDEW/VDI 4655):"))
        self.year_spinbox = QSpinBox()
        self.year_spinbox.setRange(2010, 2040)
        self.year_spinbox.setValue(2023)
        self.year_spinbox.setFixedWidth(90)
        self.year_spinbox.setToolTip(
            "Jahr für die Lastprofilberechnung nach BDEW/VDI 4655.\n"
            "Beeinflusst die Lage von Wochenenden, Feiertagen und TRY-Wetterdaten."
        )
        year_row.addWidget(self.year_spinbox)
        year_row.addStretch()
        self.leftLayout.addLayout(year_row)

        # Button-Bar für alle Aktionen
        button_layout = QHBoxLayout()
        self.csv_import_button = QPushButton("CSV importieren")
        self.csv_import_button.setToolTip(
            "CSV in beliebigem Format importieren – Spalten können interaktiv zugeordnet werden"
        )
        button_layout.addWidget(self.csv_import_button)

        self.csv_create_button = QPushButton("CSV erstellen")
        self.csv_create_button.setToolTip("Neue Gebäude-CSV erstellen")
        button_layout.addWidget(self.csv_create_button)

        self.csv_save_button = QPushButton("CSV speichern")
        self.csv_save_button.setToolTip("CSV aus Tabelle speichern")
        button_layout.addWidget(self.csv_save_button)
        self.csv_from_osm_button = QPushButton("CSV aus OSM-GeoJSON")
        self.csv_from_osm_button.setToolTip("Gebäude-CSV aus OSM-GeoJSON generieren")
        button_layout.addWidget(self.csv_from_osm_button)
        self.geocode_button = QPushButton("Geokoordinaten berechnen")
        self.geocode_button.setToolTip("Aktuelle CSV-Datei geocodieren und Koordinaten hinzufügen")
        button_layout.addWidget(self.geocode_button)
        button_frame = QFrame()
        button_frame.setLayout(button_layout)
        button_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.leftLayout.addWidget(button_frame)

        leftWidget = QWidget()
        leftWidget.setLayout(self.leftLayout)
        self.leftLayout.addWidget(self.treeView)

        splitter.addWidget(leftWidget)

        # Right area - CSV editor
        self.rightLayout = QVBoxLayout()
        # Menüleiste entfällt, alle Aktionen sind Buttons
        self.csvTable = QTableWidget()
        self.csvTable.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed)
        self.csvTable.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.csvTable.customContextMenuRequested.connect(self.show_context_menu)

        # Enhanced table formatting
        self.csvTable.setAlternatingRowColors(True)
        self.csvTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.csvTable.setSortingEnabled(True)
        self.csvTable.horizontalHeader().setStretchLastSection(True)

        # Set row height for better visibility
        self.csvTable.verticalHeader().setDefaultSectionSize(35)
        self.csvTable.verticalHeader().setMinimumSectionSize(30)

        self.rightLayout.addWidget(self.csvTable)

        # Status label for operations
        self.statusLabel = QLabel("")
        self.statusLabel.setStyleSheet("padding: 5px; color: #666666;")
        self.rightLayout.addWidget(self.statusLabel)

        self.progressBar = QProgressBar(self)
        self.rightLayout.addWidget(self.progressBar)
        rightWidget = QWidget()
        rightWidget.setLayout(self.rightLayout)
        splitter.addWidget(rightWidget)
        splitter.setStretchFactor(1, 2)

        mainLayout.addWidget(splitter)
        self.setLayout(mainLayout)

        # Button-Signale verbinden
        if self.presenter:
            self.csv_create_button.clicked.connect(self.presenter.create_csv)
            self.csv_import_button.clicked.connect(self.presenter.import_csv)
            self.csv_save_button.clicked.connect(lambda: self.presenter.save_csv(show_dialog=True))
            self.csv_from_osm_button.clicked.connect(self.presenter.create_csv_from_geojson)
            self.geocode_button.clicked.connect(self.presenter.geocode_current_csv)

    def set_crs(self, crs: str):
        """
        Set the CRS combo box to the given EPSG code (blocks signal to avoid loop).

        :param crs: EPSG code string, e.g. ``"EPSG:25833"``
        :type crs: str
        """
        self.crs_combo.blockSignals(True)
        # Try to find by userData first, then by display text prefix
        for i in range(self.crs_combo.count()):
            if self.crs_combo.itemData(i) == crs:
                self.crs_combo.setCurrentIndex(i)
                self.crs_combo.blockSignals(False)
                return
        # CRS not in list: add it as a custom entry
        self.crs_combo.addItem(crs, userData=crs)
        self.crs_combo.setCurrentIndex(self.crs_combo.count() - 1)
        self.crs_combo.blockSignals(False)

    def get_crs(self) -> str:
        """Return the currently selected EPSG code string."""
        data = self.crs_combo.currentData()
        return data if data else self.crs_combo.currentText().split(" ")[0]

    def update_tree_view(self, path):
        """
        Update file tree view root path.

        :param path: New root path.
        :type path: str
        """
        self.treeView.setRootIndex(self.treeView.model().index(path))
        for column in range(self.model.columnCount()):
            self.treeView.resizeColumnToContents(column)

    def show_context_menu(self, position):
        """
        Show table context menu.

        :param position: Menu position.
        :type position: QPoint
        """
        contextMenu = QMenu(self)
        addRowAction = QAction("Gebäude hinzufügen", self)
        deleteRowAction = QAction("Gebäude löschen", self)
        duplicateRowAction = QAction("Gebäude duplizieren", self)

        contextMenu.addAction(addRowAction)
        contextMenu.addAction(deleteRowAction)
        contextMenu.addAction(duplicateRowAction)

        addRowAction.triggered.connect(self.add_row)
        deleteRowAction.triggered.connect(self.delete_row)
        duplicateRowAction.triggered.connect(self.duplicate_row)

        contextMenu.exec(self.csvTable.viewport().mapToGlobal(position))

    def add_row(self):
        """
        Add new table row with input dialog.
        """
        headers = [self.csvTable.horizontalHeaderItem(i).text() for i in range(self.csvTable.columnCount())]
        dialog = RowInputDialog(headers, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            row_data = dialog.get_input_data()
            row = self.csvTable.rowCount()
            self.csvTable.insertRow(row)
            for i, header in enumerate(headers):
                self.csvTable.setItem(row, i, QTableWidgetItem(row_data[header]))

    def delete_row(self):
        """
        Delete selected table row.
        """
        currentRow = self.csvTable.currentRow()
        if currentRow > -1:
            self.csvTable.removeRow(currentRow)
        else:
            self.show_error_message("Warnung", "Bitte wählen Sie ein Gebäude zum Löschen aus.")

    def duplicate_row(self):
        """
        Duplicate selected table row.
        """
        currentRow = self.csvTable.currentRow()
        if currentRow > -1:
            row = self.csvTable.rowCount()
            self.csvTable.insertRow(row)
            for column in range(self.csvTable.columnCount()):
                item = self.csvTable.item(currentRow, column)
                newItem = QTableWidgetItem(item.text() if item else "")
                self.csvTable.setItem(row, column, newItem)
        else:
            self.show_error_message("Warnung", "Bitte wählen Sie ein Gebäude zum Duplizieren aus.")

    def get_selected_file_path(self, index):
        """
        Get selected file path from tree view.

        :param index: Tree view index.
        :type index: QModelIndex
        :return: Selected file path.
        :rtype: str
        """
        return self.model.filePath(index)

    def show_error_message(self, title, message):
        """
        Display error message dialog.

        :param title: Dialog title.
        :type title: str
        :param message: Error message.
        :type message: str
        """
        QMessageBox.critical(self, title, message)

    def update_progress(self, progress, csv_status=None):
        """
        Update progress bar value and CSV status label with color-coded status.

        :param progress: Progress percentage.
        :type progress: float
        :param csv_status: Status text for Quartier IST.csv.
        :type csv_status: str
        """
        self.projectProgressBar.setValue(int(progress))
        if csv_status is not None:
            # Define status with icons and colors
            status_config = {
                "fehlt": {
                    "text": "❌ Quartier IST.csv: Datei fehlt",
                    "style": "font-weight: bold; color: #d32f2f; background-color: #ffebee; padding: 8px; border-radius: 4px; border-left: 4px solid #d32f2f;",
                },
                "ist vorhanden": {
                    "text": "⚠️ Quartier IST.csv: Ist vorhanden (ohne Koordinaten)",
                    "style": "font-weight: bold; color: #f57c00; background-color: #fff3e0; padding: 8px; border-radius: 4px; border-left: 4px solid #f57c00;",
                },
                "mit Koordinaten": {
                    "text": "✅ Quartier IST.csv: Mit Koordinaten (vollständig)",
                    "style": "font-weight: bold; color: #388e3c; background-color: #e8f5e8; padding: 8px; border-radius: 4px; border-left: 4px solid #388e3c;",
                },
                "unbekannt": {
                    "text": "❓ Quartier IST.csv: Status unbekannt",
                    "style": "font-weight: bold; color: #757575; background-color: #f5f5f5; padding: 8px; border-radius: 4px; border-left: 4px solid #757575;",
                },
            }

            config = status_config.get(csv_status, status_config["unbekannt"])
            self.csv_status_label.setText(config["text"])
            self.csv_status_label.setStyleSheet(config["style"])

    def showDetailsDialog(self):
        """
        Show process step details dialog.
        """
        dialog = ProcessDetailsDialog(self.process_steps, self)
        dialog.exec()

    def set_process_steps(self, process_steps):
        """
        Set process steps data for details dialog.

        :param process_steps: List of process step dictionaries.
        :type process_steps: list
        """
        self.process_steps = process_steps

    def show_message(self, title, message):
        """
        Display information message dialog.

        :param title: Dialog title.
        :type title: str
        :param message: Information message.
        :type message: str
        """
        QMessageBox.information(self, title, message)


class ProjectTab(QWidget):
    """
    Main project tab widget integrating MVP components.

    .. note::
       Central interface for project management with file operations and progress tracking functionality.
    """

    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initialize project tab with MVP architecture.

        :param folder_manager: Folder manager.
        :type folder_manager: object
        :param data_manager: Data manager.
        :type data_manager: object
        :param config_manager: Configuration manager.
        :type config_manager: object
        :param parent: Parent widget.
        :type parent: QWidget
        """
        super().__init__(parent)

        self.model = ProjectModel()
        self.presenter = ProjectPresenter(self.model, None, folder_manager, data_manager, config_manager)
        self.view = ProjectTabView(presenter=self.presenter)
        self.presenter.view = self.view
        self.presenter.connect_view_signals()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

    def is_busy(self) -> bool:
        """True while geocoding or the OSM conversion writes the building CSV (UT-K4)."""
        presenter = self.presenter
        return any_thread_running(
            getattr(presenter, "geocodingThread", None), getattr(presenter, "geojson_conversion_thread", None)
        )
