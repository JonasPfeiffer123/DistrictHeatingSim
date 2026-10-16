"""
Assistant "Neues Projekt" (user test 2026-10-08, report section 6, stage 2).

Creating a project asked for a parent folder and a name only. Location, coordinate system, climate
data and where the buildings come from had to be found in four places, and the defaults belonged
to Görlitz (UT-H9, UT-K2); an existing name ended in "[WinError 183]" (UT-M17). The assistant asks
for all of it on three pages:

1. **Projekt** - name and folder, checked before anything is created.
2. **Standort und Klima** - a town or address; the coordinate system is suggested from it, the
   bundled test reference year is checked against it (DWD link, own TRY file), climate zone and
   persons per household for VDI 4655.
3. **Gebäude** - import a table, take them from OpenStreetMap, or start with an empty list.

The page logic that needs no widgets (name check) is a plain function; the rest is exercised by
``tests/test_new_project_wizard.py`` with the place search replaced.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from districtheatingsim.utilities.crs_utils import COMMON_CRS_OPTIONS, DEFAULT_CRS, suggest_crs_from_location
from districtheatingsim.utilities.project_location import (
    CLIMATE_ZONES,
    DEFAULT_CLIMATE_ZONE,
    DEFAULT_PERSONS_PER_HOUSEHOLD,
    DWD_TRY_URL,
    TRY_DISTANCE_WARNING_KM,
    climate_zone_label,
    distance_km,
    format_location,
    try_location,
)
from districtheatingsim.utilities.utilities import DEFAULT_TRY_RESOURCE, get_resource_path

#: Where the buildings of the new project come from
BUILDINGS_IMPORT = "import"
BUILDINGS_OSM = "osm"
BUILDINGS_MANUAL = "manual"

#: Characters Windows does not allow in a folder name
_FORBIDDEN_CHARACTERS = '\\/:*?"<>|'

_OK_STYLE = "color: #2e7d32;"
_WARNING_STYLE = "color: #c62828; font-weight: bold;"


@dataclass
class NewProjectChoice:
    """Everything the assistant asked for."""

    parent_folder: str
    name: str
    crs: str = DEFAULT_CRS
    location: tuple[float, float] | None = None
    location_name: str = ""
    try_filename: str | None = None  # None = the bundled TRY
    climate_zone: str = DEFAULT_CLIMATE_ZONE
    persons_per_household: int = DEFAULT_PERSONS_PER_HOUSEHOLD
    building_source: str = BUILDINGS_IMPORT

    @property
    def project_path(self) -> str:
        return os.path.join(self.parent_folder, self.name.strip())


def project_name_problem(parent_folder: str, name: str) -> str | None:
    """
    Why a project of this name cannot be created in this folder.

    :return: A German message, or None if the project can be created.
    """
    name = (name or "").strip()
    if not name:
        return "Bitte geben Sie einen Projektnamen ein."
    if any(character in _FORBIDDEN_CHARACTERS for character in name):
        return f"Der Name darf keines dieser Zeichen enthalten: {' '.join(_FORBIDDEN_CHARACTERS)}"
    if name.endswith("."):
        return "Der Name darf nicht mit einem Punkt enden."
    if not parent_folder or not os.path.isdir(parent_folder):
        return "Bitte wählen Sie einen vorhandenen Ordner für das Projekt."
    if os.path.exists(os.path.join(parent_folder, name)):
        return f"Im Ordner gibt es bereits „{name}“. Bitte wählen Sie einen anderen Namen."
    return None


#: What to do next, per building source (shown after the project was created)
NEXT_STEPS = {
    BUILDINGS_IMPORT: "Wählen Sie jetzt die Gebäudetabelle; danach „Geokoordinaten berechnen“.",
    BUILDINGS_OSM: (
        "So geht es weiter:\n"
        "1. Karte → Datei → „OSM Gebäudeabfrage“: den Bereich als Polygon zeichnen und die Gebäude laden.\n"
        "2. Projektdefinition → „CSV aus OSM-GeoJSON“: Adressen und Wärmebedarf werden geschätzt und in die "
        "Gebäudeliste übernommen – bitte danach prüfen."
    ),
    BUILDINGS_MANUAL: (
        "Tragen Sie die Gebäude in die Tabelle ein (Rechtsklick → „Gebäude hinzufügen“), speichern Sie mit "
        "„CSV speichern“ und berechnen Sie die Geokoordinaten."
    ),
}


def new_project_summary(choice: NewProjectChoice) -> str:
    """German summary of a created project and the next step."""
    lines = [f"Projekt „{choice.name}“ angelegt in:\n{os.path.normpath(choice.project_path)}", ""]
    if choice.location is not None:
        lines.append(f"Standort: {choice.location_name} ({format_location(*choice.location)})")
    lines.append(f"Koordinatensystem: {choice.crs}")
    try_path = choice.try_filename or get_resource_path(DEFAULT_TRY_RESOURCE)
    climate = os.path.basename(choice.try_filename) if choice.try_filename else "mitgeliefertes TRY (Oberlausitz)"
    point = try_location(try_path)
    if choice.location is not None and point is not None:
        if distance_km(point, choice.location) > TRY_DISTANCE_WARNING_KM:
            climate += " – passt nicht zum Standort, bitte ein TRY für den Ort festlegen"
    lines.append(f"Klimadaten: {climate}")
    lines.append(f"Klimazone (VDI 4655): {climate_zone_label(choice.climate_zone)}")
    lines += ["", NEXT_STEPS[choice.building_source]]
    return "\n".join(lines)


class PlaceSearchThread(QThread):
    """Looks up the project's place with Nominatim without blocking the assistant."""

    found = pyqtSignal(object)  # (lat, lon, display_name) or None
    failed = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self):
        from districtheatingsim.geocoding.geocoding import find_place
        from districtheatingsim.utilities.web_services import ServiceUnavailableError

        try:
            self.found.emit(find_place(self.query))
        except ServiceUnavailableError as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001 - shown to the user, the assistant stays usable
            self.failed.emit(f"Die Ortssuche ist fehlgeschlagen: {e}")


class ProjectPage(QWizardPage):
    """Page 1: name and folder."""

    def __init__(self, parent_folder: str, parent=None):
        super().__init__(parent)
        self.setTitle("Projekt")
        self.setSubTitle("Wie soll das Projekt heißen, und wo soll es gespeichert werden?")

        layout = QFormLayout(self)
        self.name_edit = QLineEdit("Neues Projekt")
        layout.addRow("Projektname:", self.name_edit)

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(parent_folder or "")
        browse = QPushButton("Durchsuchen…")
        browse.clicked.connect(self._browse)
        folder_row.addWidget(self.folder_edit)
        folder_row.addWidget(browse)
        layout.addRow("Ordner:", folder_row)

        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        layout.addRow("", self.path_label)

        self.name_edit.textChanged.connect(self._check)
        self.folder_edit.textChanged.connect(self._check)
        self._check()

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Ordner für das neue Projekt", self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)

    def problem(self) -> str | None:
        return project_name_problem(self.folder_edit.text().strip(), self.name_edit.text())

    def _check(self):
        problem = self.problem()
        if problem:
            self.path_label.setText(problem)
            self.path_label.setStyleSheet(_WARNING_STYLE)
        else:
            path = os.path.join(self.folder_edit.text().strip(), self.name_edit.text().strip())
            self.path_label.setText(f"Das Projekt wird angelegt in:\n{os.path.normpath(path)}")
            self.path_label.setStyleSheet("")
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self.problem() is None


class LocationPage(QWizardPage):
    """Page 2: place, coordinate system, climate data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Standort und Klima")
        self.setSubTitle(
            "Wo liegt das Quartier? Daraus werden das Koordinatensystem vorgeschlagen und die Klimadaten "
            "geprüft. Sie können diese Seite auch überspringen und alles später im Projekt ändern."
        )
        self.location: tuple[float, float] | None = None
        self.location_name = ""
        self.try_filename: str | None = None
        self._search_thread: PlaceSearchThread | None = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        place_row = QHBoxLayout()
        self.place_edit = QLineEdit()
        self.place_edit.setPlaceholderText("Ort oder Adresse, z. B. „Freiburg im Breisgau“")
        self.place_edit.returnPressed.connect(self.search_place)
        self.search_button = QPushButton("Suchen")
        self.search_button.clicked.connect(self.search_place)
        place_row.addWidget(self.place_edit)
        place_row.addWidget(self.search_button)
        form.addRow("Ort:", place_row)

        self.place_label = QLabel("Noch kein Ort gewählt.")
        self.place_label.setWordWrap(True)
        form.addRow("", self.place_label)

        self.crs_combo = QComboBox()
        for code, label in COMMON_CRS_OPTIONS:
            self.crs_combo.addItem(label, userData=code)
        self._select_crs(DEFAULT_CRS)
        form.addRow("Koordinatensystem:", self.crs_combo)
        layout.addLayout(form)

        # Climate data: the hint gets the full width (it carries the DWD link)
        layout.addWidget(QLabel("<b>Klimadaten (Testreferenzjahr)</b>"))
        self.try_label = QLabel()
        self.try_label.setWordWrap(True)
        self.try_label.setOpenExternalLinks(True)
        layout.addWidget(self.try_label)
        try_row = QHBoxLayout()
        self.try_button = QPushButton("TRY-Datei wählen…")
        self.try_button.clicked.connect(self._choose_try)
        try_row.addWidget(self.try_button)
        try_row.addStretch()
        layout.addLayout(try_row)

        form = QFormLayout()
        self.climate_zone_combo = QComboBox()
        for zone in CLIMATE_ZONES:
            self.climate_zone_combo.addItem(climate_zone_label(zone), userData=zone)
        self.climate_zone_combo.setCurrentIndex(self.climate_zone_combo.findData(DEFAULT_CLIMATE_ZONE))
        self.climate_zone_combo.setToolTip(
            "TRY-Region des Deutschen Wetterdienstes, in der das Quartier liegt.\n"
            "Wirkt auf die Lastprofile der Wohngebäude nach VDI 4655 (EFH/MFH)."
        )
        form.addRow("Klimazone (VDI 4655):", self.climate_zone_combo)

        self.persons_spinbox = QSpinBox()
        self.persons_spinbox.setRange(1, 10)
        self.persons_spinbox.setValue(DEFAULT_PERSONS_PER_HOUSEHOLD)
        form.addRow("Personen je Haushalt (VDI 4655):", self.persons_spinbox)

        layout.addLayout(form)
        layout.addStretch()
        self._show_climate_data()

    # ---------------------------------------------------------------- place
    def search_place(self):
        """Look up the entered place in the background."""
        query = self.place_edit.text().strip()
        if not query or (self._search_thread is not None and self._search_thread.isRunning()):
            return
        self.search_button.setEnabled(False)
        self.place_label.setText("Suche …")
        self.place_label.setStyleSheet("")
        self._search_thread = PlaceSearchThread(query)
        self._search_thread.found.connect(self._on_found)
        self._search_thread.failed.connect(self._on_failed)
        self._search_thread.finished.connect(lambda: self.search_button.setEnabled(True))
        self._search_thread.start()

    def _on_found(self, result):
        if result is None:
            self.place_label.setText("Dieser Ort wurde nicht gefunden. Bitte Schreibweise prüfen.")
            self.place_label.setStyleSheet(_WARNING_STYLE)
            return
        lat, lon, display_name = result
        self.set_place(lat, lon, self.place_edit.text().strip(), display_name)

    def _on_failed(self, message):
        self.place_label.setText(message)
        self.place_label.setStyleSheet(_WARNING_STYLE)

    def set_place(self, lat: float, lon: float, name: str, display_name: str = ""):
        """Take a found place: suggest the coordinate system and check the climate data."""
        self.location = (lat, lon)
        self.location_name = name
        self.place_label.setText(f"{display_name or name}\n{format_location(lat, lon)}")
        self.place_label.setStyleSheet(_OK_STYLE)
        self._select_crs(suggest_crs_from_location(lon, lat))
        self._show_climate_data()

    def _select_crs(self, code: str):
        index = self.crs_combo.findData(code)
        if index < 0:
            self.crs_combo.addItem(code, userData=code)
            index = self.crs_combo.count() - 1
        self.crs_combo.setCurrentIndex(index)

    # ---------------------------------------------------------------- climate data
    def _choose_try(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Testreferenzjahr (TRY) wählen", "", "TRY-Dateien (*.dat);;Alle Dateien (*)"
        )
        if path:
            self.try_filename = path
            self._show_climate_data()

    def _show_climate_data(self):
        path = self.try_filename or get_resource_path(DEFAULT_TRY_RESOURCE)
        name = os.path.basename(path) if self.try_filename else "mitgeliefertes TRY (Oberlausitz)"
        point = try_location(path)
        if point is None:
            self.try_label.setText(f"{name} – Standort der Datei unbekannt.")
            self.try_label.setStyleSheet("")
            return
        if self.location is None:
            self.try_label.setText(f"{name}, {format_location(*point)}. Geben Sie einen Ort an, um es zu prüfen.")
            self.try_label.setStyleSheet("")
            return
        distance = distance_km(point, self.location)
        if distance <= TRY_DISTANCE_WARNING_KM:
            self.try_label.setText(f"{name} – {distance:.0f} km vom Ort entfernt, passt.")
            self.try_label.setStyleSheet(_OK_STYLE)
        else:
            self.try_label.setText(
                f"{name} liegt {distance:.0f} km vom Ort entfernt und passt nicht. Testreferenzjahre für jeden "
                f"Ort erhalten Sie kostenlos beim <a href='{DWD_TRY_URL}'>Deutschen Wetterdienst</a> "
                "(Registrierung nötig). Wählen Sie die Datei hier oder später unter „Datenbasis → Klimadaten "
                "(TRY) festlegen“."
            )
            self.try_label.setStyleSheet(_WARNING_STYLE)

    def cleanupPage(self):
        if self._search_thread is not None:
            self._search_thread.wait()


class BuildingsPage(QWizardPage):
    """Page 3: where the buildings come from."""

    OPTIONS = [
        (
            BUILDINGS_IMPORT,
            "Gebäudetabelle importieren",
            "Eine CSV-Datei, auch ein Excel-Export. Die Spalten ordnen Sie im nächsten Schritt zu; danach werden "
            "die Adressen geocodiert.",
        ),
        (
            BUILDINGS_OSM,
            "Gebäude aus OpenStreetMap übernehmen",
            "Den Bereich zeichnen Sie auf der Karte. Adressen und Wärmebedarf werden aus OpenStreetMap "
            "geschätzt und sollten danach geprüft werden.",
        ),
        (
            BUILDINGS_MANUAL,
            "Gebäudeliste von Hand anlegen",
            "Eine leere Gebäudetabelle im Tab „Projektdefinition“.",
        ),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Gebäude")
        self.setSubTitle("Woher kommen die Gebäude des Quartiers?")
        layout = QVBoxLayout(self)
        self.group = QButtonGroup(self)
        self.buttons: dict[str, QRadioButton] = {}
        for key, label, description in self.OPTIONS:
            button = QRadioButton(label)
            self.group.addButton(button)
            self.buttons[key] = button
            hint = QLabel(description)
            hint.setWordWrap(True)
            hint.setStyleSheet("color: #666666; margin-left: 22px; margin-bottom: 8px;")
            layout.addWidget(button)
            layout.addWidget(hint)
        self.buttons[BUILDINGS_IMPORT].setChecked(True)
        layout.addStretch()

    def source(self) -> str:
        return next(key for key, button in self.buttons.items() if button.isChecked())


class NewProjectWizard(QWizard):
    """The assistant; :meth:`choice` returns the answers after ``exec()`` was accepted."""

    def __init__(self, parent_folder: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neues Projekt")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setButtonText(QWizard.WizardButton.NextButton, "Weiter >")
        self.setButtonText(QWizard.WizardButton.BackButton, "< Zurück")
        self.setButtonText(QWizard.WizardButton.FinishButton, "Projekt anlegen")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Abbrechen")
        self.resize(720, 560)
        self.project_page = ProjectPage(parent_folder)
        self.location_page = LocationPage()
        self.buildings_page = BuildingsPage()
        for page in (self.project_page, self.location_page, self.buildings_page):
            self.addPage(page)

    def choice(self) -> NewProjectChoice:
        location_page = self.location_page
        return NewProjectChoice(
            parent_folder=self.project_page.folder_edit.text().strip(),
            name=self.project_page.name_edit.text().strip(),
            crs=location_page.crs_combo.currentData(),
            location=location_page.location,
            location_name=location_page.location_name,
            try_filename=location_page.try_filename,
            climate_zone=location_page.climate_zone_combo.currentData(),
            persons_per_household=location_page.persons_spinbox.value(),
            building_source=self.buildings_page.source(),
        )
