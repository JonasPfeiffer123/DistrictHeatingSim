"""
Filename: pv_mvp.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-03
Description: Contains the PVTab for PV yield calculations.
"""

import sys
import os
import json
import pandas as pd
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import Polygon, MultiPolygon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (
    QVBoxLayout, QComboBox, QFileDialog, QWidget, QTableWidget, QTableWidgetItem, 
    QHeaderView, QDialog, QHBoxLayout, QScrollArea, QMessageBox, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtCore import pyqtSignal, QObject

from lod2.filter_LOD2 import (
    spatial_filter_with_polygon, filter_LOD2_with_coordinates, 
    process_roof, calculate_centroid_and_geocode
)

class PVDataModel:
    """
    A model to manage and process LOD2 data for PV yield calculations.
    """

    def __init__(self):
        """
        Initializes the PVDataModel with default values and loads necessary resources.
        """
        self.building_info = {}
        self.base_path = ""
        self.output_geojson_path = ""

        self.standard_values = {
            'Stockwerke': 4,
            'ww_demand_kWh_per_m2': 12.8,
            'air_change_rate': 0.5,
            'fracture_windows': 0.10,
            'fracture_doors': 0.01,
            'Normaußentemperatur': -15,
            'room_temp': 20,
            'max_air_temp_heating': 15,
            'Typ_Heizflächen': 'HK',
            'VLT_max': 70,
            'Steigung_Heizkurve': 1.5,
            'RLT_max': 55
        }

    def set_base_path(self, base_path):
        """
        Set the base path for file operations.

        Args:
            base_path (str): The base path for file operations.
        """
        self.base_path = base_path

    def get_base_path(self):
        """
        Get the current base path.

        Returns:
            str: The current base path.
        """
        return self.base_path

    def filter_data(self, method, lod_geojson_path, filter_file_path, output_geojson_path):
        """
        Filter the LOD2 data based on the specified method.

        Args:
            method (str): The filtering method to use.
            lod_geojson_path (str): Path to the input GeoJSON file.
            filter_file_path (str): Path to the filter file.
            output_geojson_path (str): Path to save the filtered GeoJSON file.
        
        Raises:
            ValueError: If an unknown filter method is provided.
        """
        if method == "Filter by Polygon":
            spatial_filter_with_polygon(lod_geojson_path, filter_file_path, output_geojson_path)
        elif method == "Filter by Building Data CSV":
            filter_LOD2_with_coordinates(lod_geojson_path, filter_file_path, output_geojson_path)
        else:
            raise ValueError(f"Unknown filter method: {method}")

    def load_data(self, filename):
        """
        Load data from a GeoJSON file and store it in the model.

        Args:
            filename (str): The path to the GeoJSON file to load.

        Raises:
            Exception: If loading the data fails.
        """
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                geojson_data = json.load(file)

            self.building_info = {}
            for feature in geojson_data['features']:
                properties = feature['properties']
                parent_id = properties.get('parent_id')
                self.building_info[parent_id] = properties

            self.output_geojson_path = filename
        except Exception as e:
            raise Exception(f"Failed to load data from {filename}: {str(e)}")

    def process_data(self, output_geojson_path):
        """
        Process the loaded data to extract required building roof parameters.

        Args:
            output_geojson_path (str): The path to the GeoJSON file that will store the processed data.
        """
        self.output_geojson_path = output_geojson_path

        # Zunächst die Dächer verarbeiten
        self.building_info = process_roof(self.output_geojson_path)
        
        # Dann Koordinaten und Adressen berechnen, falls diese fehlen
        address_missing = any(info.get('Adresse') is None for info in self.building_info.values())
        if address_missing:
            self.building_info = calculate_centroid_and_geocode(self.building_info)

    def save_data_as_geojson(self, path, data_from_view):
        """
        Save the collected data to a GeoJSON file.

        Args:
            path (str): The path where the GeoJSON file will be saved.
            data_from_view (list): The data collected from the view to be saved.

        Raises:
            Exception: If saving the data fails.
        """
        try:
            with open(self.output_geojson_path, 'r', encoding='utf-8') as file:
                geojson_data = json.load(file)

            for col, feature_data in enumerate(data_from_view):
                self.update_geojson_properties(geojson_data, feature_data, col)

            with open(path, 'w', encoding='utf-8') as file:
                json.dump(geojson_data, file, ensure_ascii=False, indent=2)

        except Exception as e:
            raise Exception(f"Failed to save data to {path}: {str(e)}")

    def update_geojson_properties(self, geojson_data, feature_data, col):
        """
        Updates the properties of the GeoJSON data with the collected data.

        Args:
            geojson_data (dict): The GeoJSON data structure.
            feature_data (dict): The updated feature data to be merged.
            col (int): The column index corresponding to the feature.
        """
        for feature in geojson_data['features']:
            properties = feature['properties']
            parent_id = properties.get('parent_id')

            if parent_id == list(self.building_info.keys())[col]:
                properties.update(feature_data)

class DataVisualizationPresenter(QObject):
    """
    The presenter class for managing the interaction between the model and the view in the LOD2 data visualization.
    """
    data_loaded = pyqtSignal(dict)

    def __init__(self, model, view, folder_manager, data_manager):
        """
        Initializes the DataVisualizationPresenter with references to the model and view.

        Args:
            model (PVDataModel): The data model.
            view (PVDataVisualizationTab): The view component.
        """
        super().__init__()
        self.model = model
        self.view = view

        self.folder_manager = folder_manager
        self.data_manager = data_manager

        self.connect_signals()

    def connect_signals(self):
        """
        Connects view signals to presenter slots.
        """
        #self.view.data_selected.connect(self.highlight_building_3d)

        self.folder_manager.project_folder_changed.connect(self.on_project_folder_changed)
        self.on_project_folder_changed(self.folder_manager.project_folder)

        self.view.treeWidget.itemSelectionChanged.connect(self.on_tree_item_selected)

    def on_project_folder_changed(self, new_base_path):
        """
        Updates the base path in the model when the project folder changes.

        Args:
            new_base_path (str): The new base path.
        """
        self.model.set_base_path(new_base_path)

    def load_data_from_file(self):
        """
        Loads data from a GeoJSON file and displays it in the Tree View.
        """
        path, _ = QFileDialog.getOpenFileName(self.view, "Öffnen", self.model.get_base_path(), "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                # Process the data (this includes functions like process_lod2)
                self.model.process_data(path)
                
                # Display data in Tree View
                self.view.display_data(self.model.building_info)
                
                # Update the 3D view with the processed data
                self.view.update_3d_view(self.model.building_info)
            
            except Exception as e:
                self.view.show_info_message("Error", f"Failed to load or process data: {str(e)}")

    def on_tree_item_selected(self):
        selected_items = self.view.treeWidget.selectedItems()
        if selected_items:
            self.highlight_building_3d(selected_items[0])

    def highlight_building_3d(self, item):
        """
        Highlights a specific building or roof in the 3D plot based on the selected Tree View item.

        Args:
            item (QTreeWidgetItem): The selected item in the Tree View.
        """
        if isinstance(item, QTreeWidgetItem):
            if item.parent() is None:
                # It's a building
                building_name = item.text(0)
                parent_id = self.find_parent_id(building_name)
                self.view.highlight_building_3d(parent_id)
            else:
                # It's a roof under a building
                parent_item = item.parent()
                building_name = parent_item.text(0)
                roof_index = parent_item.indexOfChild(item)
                parent_id = self.find_parent_id(building_name)
                self.view.highlight_building_3d(parent_id, roof_index)
        else:
            # Wenn es ein String ist (also die parent_id)
            self.view.highlight_building_3d(item)

    def find_parent_id(self, building_name):
        """
        Finds the parent ID associated with a building name.

        Args:
            building_name (str): The name of the building.

        Returns:
            str: The parent ID corresponding to the building.
        """
        for parent_id, info in self.model.building_info.items():
            if info['Adresse'] == building_name:
                return parent_id
        return None

class PVDataVisualizationTab(QWidget):
    """
    The view class for PV data visualization.
    """

    def __init__(self, parent=None):
        """
        Initializes the PVDataVisualizationTab with UI components.

        Args:
            parent (QWidget, optional): The parent widget.
        """
        super().__init__(parent)
        self.initUI()
        self.visualization_3d = PVVisualization3D(self.canvas_3d)  # Initialize the 3D visualization handler

    def initUI(self):
        """
        Initializes the UI components of the PVDataVisualizationTab.
        """
        main_layout = QVBoxLayout(self)
        data_vis_layout = QHBoxLayout()
        main_layout.addLayout(data_vis_layout)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        data_vis_layout.addWidget(scroll_area)

        scroll_content = QWidget(scroll_area)
        scroll_area.setWidget(scroll_content)
        scroll_layout = QVBoxLayout(scroll_content)

        self.treeWidget = QTreeWidget(self)
        self.treeWidget.setHeaderLabels(['Gebäude/Dach', 'Dachfläche (m²)', 'Dachneigung (°)', 'Dachausrichtung (°)', 'Yield (MWh)', 'Max Power (kW)'])
        # Automatically resize columns to fit their content
        self.treeWidget.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        scroll_layout.addWidget(self.treeWidget)

        self.figure_3d = plt.figure()
        self.canvas_3d = FigureCanvas(self.figure_3d)
        self.canvas_3d.setMinimumSize(1000, 1000)
        data_vis_layout.addWidget(self.canvas_3d)

    def add_building(self, adresse, koordinate_x, koordinate_y):
        """Add a building entry to the tree view."""
        building_item = QTreeWidgetItem(self.treeWidget)
        building_item.setText(0, adresse)
        building_item.setText(1, f'UTM_X: {koordinate_x}, UTM_Y: {koordinate_y}')
        return building_item

    def add_roof(self, building_item, roof_area, roof_slope, roof_orientation, yield_MWh, max_power):
        """Add a roof entry under a building in the tree view."""
        roof_item = QTreeWidgetItem(building_item)
        roof_item.setText(0, 'Dach')
        roof_item.setText(1, f'{roof_area:.2f}')
        roof_item.setText(2, f'{roof_slope:.2f}')
        roof_item.setText(3, f'{roof_orientation:.2f}')
        roof_item.setText(4, f'{yield_MWh:.2f}')
        roof_item.setText(5, f'{max_power:.2f}')

    def display_data(self, building_info):
        """
        Display the loaded building data in the Tree View.
        
        Args:
            building_info (dict): A dictionary containing building information.
        """
        self.treeWidget.clear()

        for parent_id, info in building_info.items():
            building_item = self.add_building(info['Adresse'], info['Koordinate_X'], info['Koordinate_Y'])
            if 'Roofs' in info:
                for roof in info['Roofs']:
                    roof_areas = roof['Area'] if isinstance(roof['Area'], list) else [roof['Area']]
                    roof_slopes = roof['Roof_Slope'] if isinstance(roof['Roof_Slope'], list) else [roof['Roof_Slope']]
                    roof_orientations = roof['Roof_Orientation'] if isinstance(roof['Roof_Orientation'], list) else [roof['Roof_Orientation']]

                    for i in range(len(roof_areas)):
                        self.add_roof(building_item, roof_areas[i], roof_slopes[i], roof_orientations[i], 0, 0)  # Initial yield and max power set to 0

    def update_3d_view(self, building_info):
        """
        Delegate the update of the 3D view to the PVVisualization3D class.

        Args:
            building_info (dict): A dictionary containing building information.
        """
        self.visualization_3d.update_3d_view(building_info)

    def highlight_building_3d(self, parent_id, roof_id=None):
        """
        Highlights a building in the 3D plot.

        Args:
            parent_id (str): The ID of the building to highlight.
        """
        self.visualization_3d.highlight_building_3d(parent_id, roof_id)

    def show_info_message(self, title, message):
        """
        Displays an informational message box.

        Args:
            title (str): The title of the message box.
            message (str): The message to be displayed.
        """
        QMessageBox.information(self, title, message)

class PVVisualization3D:
    """
    A class for handling 3D visualization of LOD2 building data.
    """

    def __init__(self, canvas_3d):
        """
        Initialize with the 3D canvas.

        Args:
            canvas_3d (FigureCanvas): The canvas for rendering 3D plots.
        """
        self.figure_3d = canvas_3d.figure
        self.canvas_3d = canvas_3d
        self.building_data = {}  # To keep track of all buildings
        self.highlighted_building_id = None  # To keep track of the highlighted building
        self.highlighted_roof_id = None  # To keep track of the highlighted roof

    def update_3d_view(self, building_info):
        """
        Update the 3D view with new building data.

        Args:
            building_info (dict): A dictionary containing building information.
        """
        self.building_data = building_info  # Store the current building data
        self.figure_3d.clear()
        ax = self.figure_3d.add_subplot(111, projection='3d')

        # Initialize bounds
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

        # Plot each building part and update the bounds
        for parent_id, info in building_info.items():
            min_x, min_y, min_z, max_x, max_y, max_z = self.plot_building_parts(
                ax, info, min_x, min_y, min_z, max_x, max_y, max_z)

        # Set plot limits based on calculated bounds
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        ax.set_zlim(min_z, max_z)

        # Set the aspect ratio for proper scaling
        ax.set_box_aspect([max_x - min_x, max_y - min_y, max_z - min_z])

        ax.set_xlabel('UTM_X')
        ax.set_ylabel('UTM_Y')
        ax.set_zlabel('Höhe')
        ax.set_title('3D-Visualisierung der möglichen Dachflächen für Photovoltaik')

        self.canvas_3d.draw()

    def plot_building_parts(self, ax, info, min_x, min_y, min_z, max_x, max_y, max_z):
        """
        Plots the building parts in the 3D plot and updates the bounds.

        Args:
            ax (Axes3D): The 3D axes object.
            info (dict): A dictionary containing building information.
            min_x (float): The minimum X value for bounding the plot.
            min_y (float): The minimum Y value for bounding the plot.
            min_z (float): The minimum Z value for bounding the plot.
            max_x (float): The maximum X value for bounding the plot.
            max_y (float): The maximum Y value for bounding the plot.
            max_z (float): The maximum Z value for bounding the plot.

        Returns:
            tuple: Updated bounding box values (min_x, min_y, min_z, max_x, max_y, max_z).
        """
        # Plot the Ground and Walls first
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
            ax, info.get('Ground', []), 'blue', min_x, min_y, min_z, max_x, max_y, max_z)
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
            ax, info.get('Wall', []), 'blue', min_x, min_y, min_z, max_x, max_y, max_z)

        # Plotting Roof geometries
        for i, roof in enumerate(info.get('Roofs', [])):
            parent_id = roof.get('parent_id')

            # Check if this is the building and roof to highlight
            if parent_id == self.highlighted_building_id and (self.highlighted_roof_id is None or self.highlighted_roof_id == i):
                color = 'red'
            else:
                color = 'blue'
            
            min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(
                ax, [roof['geometry']], color, min_x, min_y, min_z, max_x, max_y, max_z)

        return min_x, min_y, min_z, max_x, max_y, max_z

    def plot_geometry(self, ax, geoms, color, min_x, min_y, min_z, max_x, max_y, max_z):
        """
        Plots the geometry in the 3D plot and updates the bounds.

        Args:
            ax (Axes3D): The 3D axes object.
            geoms (list or shapely.geometry): A list of geometries or a single geometry.
            color (str): The color to use for the geometry.
            min_x (float): The minimum X value for bounding the plot.
            min_y (float): The minimum Y value for bounding the plot.
            min_z (float): The minimum Z value for bounding the plot.
            max_x (float): The maximum X value for bounding the plot.
            max_y (float): The maximum Y value for bounding the plot.
            max_z (float): The maximum Z value for bounding the plot.

        Returns:
            tuple: Updated bounding box values (min_x, min_y, min_z, max_x, max_y, max_z).
        """
        if isinstance(geoms, (Polygon, MultiPolygon)):
            geoms = [geoms]

        for geom in geoms:
            if geom:
                if geom.geom_type == 'Polygon':
                    x, y, z = zip(*geom.exterior.coords)
                    verts = [list(zip(x, y, z))]
                    poly_collection = Poly3DCollection(verts, facecolors=color, alpha=0.5)
                    ax.add_collection3d(poly_collection)
                elif geom.geom_type == 'MultiPolygon':
                    for poly in geom.geoms:
                        x, y, z = zip(*poly.exterior.coords)
                        verts = [list(zip(x, y, z))]
                        poly_collection = Poly3DCollection(verts, facecolors=color, alpha=0.5)
                        ax.add_collection3d(poly_collection)

                # Update bounds
                min_x, min_y, min_z = min(min_x, min(x)), min(min_y, min(y)), min(min_z, min(z))
                max_x, max_y, max_z = max(max_x, max(x)), max(max_y, max(y)), max(max_z, max(z))

        return min_x, min_y, min_z, max_x, max_y, max_z

    def highlight_building_3d(self, parent_id, roof_id=None):
        """
        Highlights a specific building or roof in the 3D plot.

        Args:
            parent_id (str): The ID of the building to highlight.
            roof_id (int, optional): The index of the roof to highlight within the building. Defaults to None.
        """
        self.highlighted_building_id = parent_id
        self.highlighted_roof_id = roof_id
        self.update_3d_view(self.building_data)