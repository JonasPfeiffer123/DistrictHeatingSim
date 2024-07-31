"""
Filename: project_dialogs.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Contains the Dialogs for the ProjectTab.
"""

import sys
import os

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QDialog, QPushButton, \
    QHBoxLayout, QFileDialog, QProgressBar, QMessageBox, QLabel
from PyQt5.QtGui import QFont

from gui.threads import GeocodingThread

# defines the map path
def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)