"""Path utility functions for development and frozen builds.

This module provides functions to locate data directories correctly
in both development and PyInstaller frozen builds.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os
import sys


def get_data_path(subfolder=''):
    """
    Get path to data directory for both development and frozen builds.
    
    :param subfolder: Optional subfolder within data directory
    :type subfolder: str
    :return: Absolute path to data directory or subfolder
    :rtype: str
    
    .. note::
        In frozen builds, data folder is located next to the executable
        for user accessibility.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # Data folder is next to exe for user accessibility
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running in development
        # Assuming this file is in src/districtheatingsim/utilities/
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    data_dir = os.path.join(base_dir, 'data')
    
    if subfolder:
        return os.path.join(data_dir, subfolder)
    return data_dir


def get_project_data_path(project_name=''):
    """
    Get path to project_data directory for both development and frozen builds.
    
    :param project_name: Optional name of specific project
    :type project_name: str
    :return: Absolute path to project_data directory or specific project
    :rtype: str
    
    .. note::
        In frozen builds, project_data folder is located next to the executable.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # Project_data folder is next to exe for user accessibility
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running in development
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    project_data_dir = os.path.join(base_dir, 'project_data')
    
    if project_name:
        return os.path.join(project_data_dir, project_name)
    return project_data_dir


def get_internal_data_path(relative_path):
    """
    Get path to data inside _internal folder (not user-accessible).
    
    :param relative_path: Relative path within internal data structure
    :type relative_path: str
    :return: Absolute path to internal data
    :rtype: str
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - use _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # Running in development - use module location
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            relative_path
        )


def is_frozen():
    """
    Check if running as frozen (compiled) application.
    
    :return: True if running as compiled executable, False otherwise
    :rtype: bool
    """
    return getattr(sys, 'frozen', False)


def get_app_root():
    """
    Get application root directory.
    
    :return: Path to executable directory (frozen) or project root (development)
    :rtype: str
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
