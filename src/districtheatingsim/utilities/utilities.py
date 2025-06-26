"""
Filename: utilities.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-10
Description: Script with utility functions. get_resource_path() is used to get the absolute path to a resource.
"""

import os
import sys
import time

import traceback

from PyQt5.QtWidgets import QMessageBox

def get_resource_path(relative_path):
    """
    Get the absolute path to a resource, works for dev and for PyInstaller.

    This function resolves the correct path to resources (files, images, etc.) 
    whether the application is running in development mode or as a PyInstaller 
    frozen executable. This is essential for accessing bundled resources in 
    compiled applications.

    Parameters
    ----------
    relative_path : str
        The relative path to the resource from the project root directory.
        Use forward slashes or os.path.join() for cross-platform compatibility.

    Returns
    -------
    str
        The absolute path to the resource.

    Notes
    -----
    - In development mode: Returns path relative to the project root
    - In PyInstaller mode: Returns path relative to the temporary extraction folder
    - The function automatically detects the execution environment using sys.frozen
    
    When using PyInstaller, ensure that your resources are included in the bundle
    using the --add-data option or by specifying them in the .spec file.

    Examples
    --------
    >>> get_resource_path('styles/logo.png')
    '/path/to/project/styles/logo.png'
    
    >>> get_resource_path('data/config.json')
    '/path/to/project/data/config.json'
    
    >>> # Cross-platform path handling
    >>> get_resource_path(os.path.join('templates', 'report.html'))
    '/path/to/project/templates/report.html'

    See Also
    --------
    os.path.join : Platform-independent path joining
    sys.frozen : Attribute indicating if running from PyInstaller
    """
    if getattr(sys, 'frozen', False):
        # When the application is frozen, the base path is the temp folder where PyInstaller extracts everything
        base_path = sys._MEIPASS
    else:
        # When the application is not frozen, the base path is the directory of the main file
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

def handle_global_exception(exc_type, exc_value, exc_traceback):
    """
    Global exception handler to display errors in a QMessageBox.
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
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle("Fehler")
    msg_box.setText("Ein unerwarteter Fehler ist aufgetreten:")
    msg_box.setDetailedText(error_message)
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec_()

def get_stylesheet_based_on_time():
    """
    Return the stylesheet path based on the current system time.
    """
    current_hour = time.localtime().tm_hour
    if 6 <= current_hour < 18:  # Wenn es zwischen 6:00 und 18:00 Uhr ist
        return "light_theme_style_path"  # Pfad zum hellen Stylesheet
    else:
        return "dark_theme_style_path"   # Pfad zum dunklen Stylesheet