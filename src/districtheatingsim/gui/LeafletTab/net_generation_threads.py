"""
Net Generation Threads Module
==============================

This module provides threading classes for network generation, file import,
and geocoding operations to maintain GUI responsiveness.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import traceback

import geopandas as gpd
from PyQt6.QtCore import QThread, pyqtSignal

from districtheatingsim.geocoding.geocoding import process_data
from districtheatingsim.net_generation.import_and_create_layers import generate_and_export_layers
from districtheatingsim.net_generation.osmnx_steiner_network import generate_and_export_osmnx_layers


class NetGenerationThread(QThread):
    """
    Thread for generating district heating networks.
    """

    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, inputs, base_path):
        """
        Initialize network generation thread.

        Sets up the thread with input parameters for generating district heating
        networks using different algorithms.

        :param inputs: Input parameters for network generation
        :type inputs: dict
        :param base_path: Base path for file operations
        :type base_path: str
        """
        super().__init__()
        self.inputs = inputs
        self.base_path = base_path

    def run(self):
        """
        Run network generation process.

        Executes the network generation based on the selected algorithm
        (OSMnx or traditional MST/Steiner) and emits signals on completion or error.
        """
        try:
            project_crs = self.inputs.get("project_crs", "EPSG:25833")
            if self.inputs["generation_mode"] == "OSMnx":
                # Use OSMnx-based network generation
                generate_and_export_osmnx_layers(
                    osm_street_layer_geojson_file_name=self.inputs.get("streetLayer", ""),
                    data_csv_file_name=self.inputs["dataCsv"],
                    coordinates=self.inputs["coordinates"],
                    base_path=self.base_path,
                    algorithm=self.inputs["generation_mode"],
                    custom_filter=self.inputs.get("custom_filter", None),
                    target_crs=project_crs,
                )
            else:
                # Use traditional MST/Steiner algorithms
                generate_and_export_layers(
                    osm_street_layer_geojson_file_name=self.inputs["streetLayer"],
                    data_csv_file_name=self.inputs["dataCsv"],
                    coordinates=self.inputs["coordinates"],
                    base_path=self.base_path,
                    algorithm=self.inputs["generation_mode"],
                    crs=project_crs,
                    dem_path=self.inputs.get("dem_path"),
                )

            self.calculation_done.emit(())
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.calculation_error.emit(error_msg)

    def stop(self):
        """
        Stop thread execution.

        Requests interruption and waits for the thread to finish if it is currently running.
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()


class OSMStreetDownloadThread(QThread):
    """
    Thread for downloading OSM street data.
    """

    download_done = pyqtSignal(str)  # Emits filepath when done
    download_error = pyqtSignal(str)

    def __init__(self, download_func, *args, **kwargs):
        """
        Initialize OSM street download thread.

        Sets up the thread with a download function and its arguments for
        downloading OpenStreetMap street data asynchronously.

        :param download_func: The download function to execute
        :type download_func: callable
        :param args: Positional arguments for download_func
        :type args: tuple
        :param kwargs: Keyword arguments for download_func
        :type kwargs: dict
        """
        super().__init__()
        self.download_func = download_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """
        Run download process.

        Executes the download function and emits the filepath on success
        or an error message on failure.
        """
        try:
            filepath = self.download_func(*self.args, **self.kwargs)
            self.download_done.emit(filepath)
        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Fehler beim Download:\n{str(e)}\n\n{tb}"
            self.download_error.emit(error_message)


class OSMBuildingDownloadThread(QThread):
    """
    Thread for downloading OSM building data.
    """

    download_done = pyqtSignal(str, int)  # Emits filepath and building count when done
    download_error = pyqtSignal(str)

    def __init__(self, download_func, *args, **kwargs):
        """
        Initialize OSM building download thread.

        Sets up the thread with a download function and its arguments for
        downloading OpenStreetMap building data asynchronously.

        :param download_func: The download function to execute
        :type download_func: callable
        :param args: Positional arguments for download_func
        :type args: tuple
        :param kwargs: Keyword arguments for download_func
        :type kwargs: dict
        """
        super().__init__()
        self.download_func = download_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """
        Run download process.

        Executes the download function and emits the filepath and building count
        on success or an error message on failure.
        """
        try:
            filepath, building_count = self.download_func(*self.args, **self.kwargs)
            self.download_done.emit(filepath, building_count)
        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Fehler beim Download:\n{str(e)}\n\n{tb}"
            self.download_error.emit(error_message)


class FileImportThread(QThread):
    """
    Thread for importing geospatial files.
    """

    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, m, filenames, color):
        """
        Initialize file import thread.

        Sets up the thread with map object, filenames, and styling color
        for importing geospatial files asynchronously.

        :param m: Map object for visualization
        :type m: object
        :param filenames: List of filenames to import
        :type filenames: list
        :param color: Color for visualization styling
        :type color: str
        """
        super().__init__()
        self.m = m
        self.filenames = filenames
        self.color = color

    def run(self):
        """
        Run file import process.

        Reads geospatial files using geopandas and emits the results with
        styling information for visualization on success or an error message on failure.
        """
        try:
            results = {}
            for filename in self.filenames:
                gdf = gpd.read_file(filename)
                results[filename] = {
                    "gdf": gdf,
                    "name": filename,
                    "style": {
                        "fillColor": self.color,
                        "color": self.color,
                        "weight": 1.5,
                        "fillOpacity": 0.5,
                    },
                }
            self.calculation_done.emit(results)
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        """
        Stop thread execution.

        Requests interruption and waits for the thread to finish if it is currently running.
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()


class GeocodingThread(QThread):
    """
    Thread for geocoding address data.
    """

    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, inputfilename, project_crs: str = "EPSG:25833"):
        """
        Initialize geocoding thread.

        Sets up the thread with an input filename for processing
        geocoding operations asynchronously.

        :param inputfilename: Input filename for geocoding data
        :type inputfilename: str
        :param project_crs: Target projected CRS for coordinate output
        :type project_crs: str
        """
        super().__init__()
        self.inputfilename = inputfilename
        self.project_crs = project_crs

    def run(self):
        """
        Run geocoding process.

        Processes the geocoding data from the input file and emits a tuple of
        (filename, result_summary) on success or an error message on failure.
        The result_summary dict contains keys: total, success, failed, failed_addresses.
        """
        try:
            result = process_data(self.inputfilename, crs=self.project_crs)
            self.calculation_done.emit((self.inputfilename, result))
        except Exception as e:
            tb = traceback.format_exc()
            error_message = f"Ein Fehler ist aufgetreten: {e}\n{tb}"
            self.calculation_error.emit(error_message)

    def stop(self):
        """
        Stop thread execution.

        Requests interruption and waits for the thread to finish if it is currently running.
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()


class GeoJSONToCSVThread(QThread):
    """
    Thread for converting GeoJSON to CSV with reverse geocoding.
    """

    progress_update = pyqtSignal(int, int, str)  # current, total, message
    calculation_done = pyqtSignal(str)  # output_file_path
    calculation_error = pyqtSignal(str)

    def __init__(self, geojson_file_path, output_file_path, default_values, model, project_crs: str = "EPSG:25833"):
        """
        Initialize GeoJSON to CSV conversion thread.

        Sets up the thread with file paths, default values, and model instance
        for converting GeoJSON building data to CSV with reverse geocoding.

        :param geojson_file_path: Input GeoJSON file path
        :type geojson_file_path: str
        :param output_file_path: Output CSV file path
        :type output_file_path: str
        :param default_values: Default values for building parameters
        :type default_values: dict
        :param model: Model instance with calculate_centroid method
        :type model: ProjectModel
        :param project_crs: Projected CRS of the input coordinates
        :type project_crs: str
        """
        super().__init__()
        self.geojson_file_path = geojson_file_path
        self.output_file_path = output_file_path
        self.default_values = default_values
        self.model = model
        self.project_crs = project_crs

    def run(self):
        """
        Run GeoJSON to CSV conversion with reverse geocoding (off the UI thread).

        Delegates to the GUI-free ``geojson_to_building_csv``, wiring progress updates and
        cooperative cancellation through to the Qt signals.
        """
        from districtheatingsim.geocoding.building_csv import geojson_to_building_csv

        try:
            geojson_to_building_csv(
                self.geojson_file_path,
                self.output_file_path,
                self.default_values,
                self.project_crs,
                progress=lambda done, total, message: self.progress_update.emit(done, total, message),
                should_stop=self.isInterruptionRequested,
            )
            self.calculation_done.emit(self.output_file_path)
        except InterruptedError:
            self.calculation_error.emit("Konvertierung abgebrochen")
        except Exception as e:
            tb = traceback.format_exc()
            self.calculation_error.emit(f"{e}\n\n{tb}")

    def stop(self):
        """
        Stop thread execution.

        Requests interruption and waits for the thread to finish if it is currently running.
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()
