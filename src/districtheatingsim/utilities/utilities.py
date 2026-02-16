"""Utility functions for the DistrictHeatingSim application.

This module provides helper functions for resource path resolution,
global exception handling, and theme management.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os
import sys
import time

import traceback

from PyQt6.QtWidgets import QMessageBox

def get_resource_path(relative_path):
    """
    Resolve the absolute path to a resource file for development, PyInstaller, or pip-installed package.

    :param relative_path: Relative path to the resource from the package root
    :type relative_path: str
    :return: Absolute path to the resource file
    :rtype: str

    Notes:
        - In development, returns the path relative to the source tree.
        - In PyInstaller builds, handles data folders outside _internal.
        - In pip installations, uses importlib.resources for package data.
    """
    # 1. PyInstaller build: handle frozen state and data folders outside _internal
    if getattr(sys, 'frozen', False):
        # When the application is frozen, the base path needs special handling
        # PyInstaller extracts files to sys._MEIPASS (_internal folder)
        # but we configure some data folders to be in the parent directory
        # Check if the relative_path starts with known data folders that are outside _internal
        data_folders_outside = ['data', 'project_data', 'images', 'leaflet']
        
        # Check if this is a path that should be outside _internal
        first_component = relative_path.split(os.sep)[0].split('/')[0]
        if first_component in data_folders_outside:
            # These folders are in the application directory (parent of _internal)
            base_path = os.path.dirname(sys._MEIPASS)
        else:
            # Other resources are in the _internal folder
            base_path = sys._MEIPASS
        return os.path.join(base_path, relative_path)

    # 2. Development mode: use path relative to source tree
    dev_base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dev_path = os.path.join(dev_base_path, relative_path)
    if os.path.exists(dev_path):
        return dev_path

    # 3. pip-installed package: use importlib.resources for package data
    import importlib.resources
    parts = relative_path.replace('\\', '/').split('/')
    if not parts:
        raise FileNotFoundError(f"Empty resource path: {relative_path}")
    resource_package = f"districtheatingsim.{parts[0]}"
    resource_path = '/'.join(parts[1:])
    try:
        return str(importlib.resources.files(resource_package).joinpath(resource_path))
    except Exception as e:
        raise FileNotFoundError(f"Resource not found via importlib.resources: {relative_path}\n{e}")

def handle_global_exception(exc_type, exc_value, exc_traceback):
    """
    Global exception handler that displays errors in a QMessageBox dialog.
    
    :param exc_type: Exception type
    :type exc_type: type
    :param exc_value: Exception instance
    :type exc_value: BaseException
    :param exc_traceback: Traceback object
    :type exc_traceback: types.TracebackType
    
    .. note::
        KeyboardInterrupt exceptions are handled by the default system handler.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Standardverhalten für KeyboardInterrupt beibehalten
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Erstelle die Fehlermeldung
    error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(error_message)  # Optional: Logge die Fehlermeldung in die Konsole

    # Zeige die Fehlermeldung in einem Dialogfenster
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle("Fehler")
    msg_box.setText("Ein unerwarteter Fehler ist aufgetreten:")
    msg_box.setDetailedText(error_message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()

def get_stylesheet_based_on_time():
    """
    Get stylesheet identifier based on current system time.
    
    :return: 'light_theme_style_path' if between 6:00-18:00, otherwise 'dark_theme_style_path'
    :rtype: str
    
    .. note::
        Light theme is applied during daytime (6 AM - 6 PM),
        dark theme during evening/night hours.
    """
    current_hour = time.localtime().tm_hour
    if 6 <= current_hour < 18:  # Wenn es zwischen 6:00 und 18:00 Uhr ist
        return "light_theme_style_path"  # Pfad zum hellen Stylesheet
    else:
        return "dark_theme_style_path"   # Pfad zum dunklen Stylesheet