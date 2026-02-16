import os
import sys
sys.path.insert(0, os.path.abspath('../../src'))

# -- Project information -----------------------------------------------------
project = 'DistrictHeatingSim'
copyright = '2025, Dipl.-Ing. (FH) Jonas Pfeiffer'
author = 'Dipl.-Ing. (FH) Jonas Pfeiffer'
release = '1.0.1'
version = '1.0.1'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.githubpages',
    'sphinx_design',
    'sphinx_copybutton',
    'sphinx_tabs.tabs',
    'sphinxcontrib.bibtex'
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Napoleon settings -------------------------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# -- Autodoc settings --------------------------------------------------------
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
    'show-inheritance': True,
}

autosummary_generate = True
autosummary_generate_overwrite = True

# -- HTML output -------------------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# Bessere Sidebar-Konfiguration
html_sidebars = {
    '**': [
        'versions.html',
        'navigation.html',
        'relations.html',
        'searchbox.html',
        'donate.html',
    ]
}

html_static_path = ['_static']
html_css_files = ['custom.css']

html_context = {
    'display_github': True,
    'github_user': 'jonaspfeiffer123',
    'github_repo': 'DistrictHeatingSim',
    'github_version': 'main',
    'conf_py_path': '/docs/source/',
}

html_show_sourcelink = True
html_copy_source = False
html_show_sphinx = False

# -- Intersphinx mapping -----------------------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
}

# -- Todo extension ----------------------------------------------------------
todo_include_todos = True

# -- Copy button configuration -----------------------------------------------
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# Bibtex-Files
# -----------------------------------------------------------------------------
bibtex_bibfiles = ['refs.bib']
