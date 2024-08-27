"""
Filename: lod2_plot.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-27
Description: Contains the LOD2Tab and associated classes for data visualization and comparison.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QVBoxLayout, QFileDialog, QWidget, QMessageBox)
from PyQt5.QtCore import pyqtSignal, QObject

class LOD2PlotModel:
    """
    Model class for managing datasets related to LOD2 heat demand data.
    """

    def __init__(self):
        """Initializes the model with empty data storage."""
        self.loaded_data = []
        self.loaded_filenames = []
        self.base_path = ""

    def add_dataset(self, df, filename):
        """
        Adds a dataset to the model.

        Args:
            df (pd.DataFrame): The dataset to add.
            filename (str): The name of the file associated with the dataset.
        """
        self.loaded_data.append(df)
        self.loaded_filenames.append(filename)

    def remove_last_dataset(self):
        """
        Removes the last added dataset from the model.
        """
        if self.loaded_data:
            self.loaded_data.pop()
            self.loaded_filenames.pop()

    def get_aggregated_data(self):
        """
        Aggregates the loaded datasets for plotting.

        Returns:
            pd.DataFrame: Aggregated data with summed heat demand per address and filename.
        """
        if not self.loaded_data:
            return None

        all_data = pd.concat(self.loaded_data, keys=self.loaded_filenames, names=['Filename', 'Index'])
        all_data_grouped = all_data.groupby(['Adresse', 'Filename'])['Wärmebedarf'].sum().unstack('Filename').fillna(0)
        return all_data_grouped
    
    def set_base_path(self, base_path):
        """
        Sets the base path for file operations.

        Args:
            base_path (str): The base path to be used for file dialogs.
        """
        self.base_path = base_path

    def get_base_path(self):
        """
        Gets the current base path for file operations.

        Returns:
            str: The base path currently set.
        """
        return self.base_path

class PlotPresenter(QObject):
    """
    Presenter class for handling the interaction between the LOD2PlotModel and LOD2PlotTab.
    """

    def __init__(self, model, view, data_manager):
        """
        Initializes the presenter with a model, view, and data manager.

        Args:
            model (LOD2PlotModel): The model containing the datasets.
            view (LOD2PlotTab): The view responsible for rendering the datasets.
            data_manager (DataManager): The data manager handling project-related data.
        """
        super().__init__()
        self.model = model
        self.view = view
        self.data_manager = data_manager

        self.data_manager.project_folder_changed.connect(self.on_project_folder_changed)
        self.on_project_folder_changed(self.data_manager.project_folder)

    def on_project_folder_changed(self, new_base_path):
        """
        Updates the base path in the model when the project folder changes.

        Args:
            new_base_path (str): The new base path.
        """
        self.model.set_base_path(new_base_path)

    def add_dataset(self):
        """
        Adds a dataset for comparison. Opens a file dialog to select a CSV file.
        """
        try:
            path, _ = QFileDialog.getOpenFileName(self.view, "Öffnen", self.model.get_base_path(), "CSV-Dateien (*.csv)")
            if path:
                df = pd.read_csv(path, delimiter=';')
                self.model.add_dataset(df, os.path.basename(path))
                self.view.add_dataset_to_plot(df, os.path.basename(path))
        except Exception as e:
            self.view.show_error_message("Fehler beim Hinzufügen des Datensatzes", f"Es ist ein Fehler aufgetreten: {str(e)}")

    def remove_dataset(self):
        """
        Removes the last added dataset.
        """
        try:
            self.model.remove_last_dataset()
            self.view.remove_last_dataset_from_plot()
        except Exception as e:
            self.view.show_error_message("Fehler beim Entfernen des Datensatzes", f"Es ist ein Fehler aufgetreten: {str(e)}")

class LOD2PlotTab(QWidget):
    """
    View class for displaying the plot of LOD2 data comparisons.
    """

    def __init__(self, parent=None):
        """
        Initializes the plot tab view.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.loaded_data = []
        self.loaded_filenames = []
        self.initUI()

    def initUI(self):
        """
        Initializes the UI components of the LOD2PlotTab.
        """
        layout = QVBoxLayout(self)
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(800, 400)
        layout.addWidget(self.canvas)

    def add_dataset_to_plot(self, df, filename):
        """
        Adds a dataset to the plot.

        Args:
            df (pd.DataFrame): The dataset to be added to the plot.
            filename (str): The name of the file associated with the dataset.
        """
        self.loaded_data.append(df)
        self.loaded_filenames.append(filename)
        self.update_plot()

    def remove_last_dataset_from_plot(self):
        """
        Removes the last dataset from the plot.
        """
        if self.loaded_data:
            self.loaded_data.pop()
            self.loaded_filenames.pop()
            self.update_plot()

    def update_plot(self):
        """
        Updates the plot with the current datasets.
        """
        if not self.loaded_data:
            self.figure.clear()
            self.canvas.draw()
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        all_data = pd.concat(self.loaded_data, keys=self.loaded_filenames, names=['Filename', 'Index'])
        all_data_grouped = all_data.groupby(['Adresse', 'Filename'])['Wärmebedarf'].sum().unstack('Filename').fillna(0)
        
        num_datasets = len(self.loaded_data)
        num_addresses = len(all_data_grouped)
        
        bar_width = 0.8 / num_datasets
        indices = np.arange(num_addresses)
        
        colors = plt.cm.Set1.colors[:num_datasets]

        for i, (filename, color) in enumerate(zip(all_data_grouped.columns, colors)):
            ax.barh(indices + i * bar_width, all_data_grouped[filename], bar_width, label=filename, color=color)

        ax.set_yticks(indices + bar_width * (num_datasets - 1) / 2)
        ax.set_yticklabels(all_data_grouped.index)
        ax.set_ylabel('Adresse')
        ax.set_xlabel('Wärmebedarf in kWh')
        ax.legend()
        
        self.canvas.draw()

    def show_error_message(self, title, message):
        """
        Shows an error message dialog.

        Args:
            title (str): The title of the error dialog.
            message (str): The error message to be displayed.
        """
        QMessageBox.critical(self, title, message)