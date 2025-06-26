# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
sys.path.insert(0, os.path.abspath('../../src'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'DistrictHeatingSim'
copyright = '2025, Dipl.-Ing. (FH) Jonas Pfeiffer'
author = 'Dipl.-Ing. (FH) Jonas Pfeiffer'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# HTML theme options
html_theme = 'sphinx_rtd_theme' # or 'alabaster', 'furo', etc.
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False
}

# HTML static path for custom CSS/JS
html_static_path = ['_static']
html_css_files = ['custom.css']

# HTML context for custom variables
html_context = {
    'display_github': True,
    'github_user': 'jonaspfeiffer123',
    'github_repo': 'DistrictHeatingSim',
}
