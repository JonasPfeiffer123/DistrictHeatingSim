"""
German texts for Qt's own widgets (user test 2026-10-08, UT-M2).

Without a translation Qt shows its built-in English texts: "OK"/"Cancel"/"Yes"/"No" in every
message box and dialog, "Name"/"Size"/"Type"/"Date Modified" in the project tab's file tree,
"Open"/"Save" in the file dialogs. PyQt6 ships the German translation; it is installed at start.

:author: M.Eng. Jonas Pfeiffer
"""

import logging

from PyQt6.QtCore import QLibraryInfo, QLocale, QTranslator

logger = logging.getLogger(__name__)


def install_german_qt_translation(app) -> bool:
    """
    Install Qt's German translation (``qtbase_de.qm``) in ``app``.

    :return: True if it was found and installed.
    """
    translator = QTranslator(app)
    directory = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if not translator.load(QLocale(QLocale.Language.German, QLocale.Country.Germany), "qtbase", "_", directory):
        logger.warning("Deutsche Qt-Übersetzung nicht gefunden in %s", directory)
        return False
    app.installTranslator(translator)
    app._german_qt_translator = translator  # keep a reference for the lifetime of the application
    return True
