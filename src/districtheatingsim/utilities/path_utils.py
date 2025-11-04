"""
Utility module for finding data directories in both development and frozen builds.
"""

import os
import sys


def get_data_path(subfolder=''):
    """
    Get path to data directory, works in both development and frozen builds.
    
    In frozen builds, data folders (data, project_data) are located next to the
    executable for user accessibility.
    
    Parameters
    ----------
    subfolder : str, optional
        Subfolder within data directory (default: '')
        
    Returns
    -------
    str
        Absolute path to data directory or subfolder
        
    Examples
    --------
    >>> # Get path to TRY data files
    >>> try_path = get_data_path('TRY')
    
    >>> # Get path to COP files
    >>> cop_path = get_data_path('COP')
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
    Get path to project_data directory, works in both development and frozen builds.
    
    In frozen builds, project_data folder is located next to the executable
    for user accessibility.
    
    Parameters
    ----------
    project_name : str, optional
        Name of specific project (default: '')
        
    Returns
    -------
    str
        Absolute path to project_data directory or specific project
        
    Examples
    --------
    >>> # Get path to Görlitz project
    >>> goerlitz_path = get_project_data_path('Görlitz')
    
    >>> # Get path to all projects
    >>> all_projects = get_project_data_path()
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
    Get path to data inside _internal folder (Python modules, etc.).
    
    This is for data that should NOT be user-accessible.
    
    Parameters
    ----------
    relative_path : str
        Relative path within the internal data structure
        
    Returns
    -------
    str
        Absolute path to internal data
        
    Examples
    --------
    >>> # Get path to pandapipes standard types
    >>> pp_std = get_internal_data_path('pandapipes/std_types/library')
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
    
    Returns
    -------
    bool
        True if running as compiled executable, False if in development
    """
    return getattr(sys, 'frozen', False)


def get_app_root():
    """
    Get application root directory.
    
    Returns
    -------
    str
        Path to application root (where exe is located in frozen build,
        or project root in development)
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
