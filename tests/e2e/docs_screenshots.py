"""
Documentation screenshots
=========================

Takes the screenshots of the user handbook (``docs/source/benutzerhandbuch.rst``) and the
overview images of the README by walking through "Mein erstes Quartier" in the real main window:
15 buildings of the Zittau old town from ``inputs/zittau_quartier.csv``, from the assistant
"Neues Projekt" to the variant comparison.

Unlike the scenarios it runs on the native platform with the GPU enabled at 100 % scale: the
map, the network plot and the fonts of dialogs without a parent render only there. Windows
appear on the screen while it runs (about 5 minutes).

Live services: Nominatim (place search, geocoding) and Overpass/OSMnx (streets, network). If
one fails, the step takes the files of an earlier ``scenario_p1_zittau.py`` run
(``tests/e2e/_work/projects/Zittau_Altstadt``) and says so in ``events.log``.

Output: ``docs/source/_static/images/handbuch/*.png`` (256 colours), and the five overview
images in ``images/`` and ``docs/source/_static/images/``. Work files go to
``C:/Users/Public/Documents/DistrictHeatingSim-Doku`` on Windows (the project path shows in the
screenshots; a user folder would publish the user name), else ``tests/e2e/_work/docs``, or to
``$DHS_E2E_WORKDIR``.

Run: ``python tests/e2e/docs_screenshots.py`` (all steps) or with step names.

:author: M.Eng. Jonas Pfeiffer
"""

import os
import shutil
import sys

_E2E = os.path.dirname(os.path.abspath(__file__))
_PUBLIC = "C:/Users/Public/Documents"
os.environ.setdefault(
    "DHS_E2E_WORKDIR",
    os.path.join(_PUBLIC, "DistrictHeatingSim-Doku") if os.path.isdir(_PUBLIC) else os.path.join(_E2E, "_work", "docs"),
)

import harness as H  # noqa: E402

# The harness sets up the offscreen platform; the documentation needs the real one (decided when
# the QApplication is created in start_app).
if sys.platform == "win32":
    os.environ["QT_QPA_PLATFORM"] = "windows"
    os.environ.pop("QT_QPA_FONTDIR", None)
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = ""  # WebGL for the network plot's base map


def _display_scale():
    """Windows display scaling (1.25 at 125 %); 1 elsewhere or if unknown."""
    if sys.platform != "win32":
        return 1.0
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop\WindowMetrics") as key:
            return winreg.QueryValueEx(key, "AppliedDPI")[0] / 96
    except OSError:
        return 1.0


# 100 % whatever the display scaling: QT_ENABLE_HIGHDPI_SCALING=0 would keep the fonts at the
# display's DPI and the layout at 96 DPI, so labels get cut off
os.environ["QT_SCALE_FACTOR"] = f"{1 / _display_scale():.4f}"

DOCS_IMAGES = os.path.join(H.REPO_ROOT, "docs", "source", "_static", "images")
HANDBOOK_IMAGES = os.path.join(DOCS_IMAGES, "handbuch")
README_IMAGES = os.path.join(H.REPO_ROOT, "images")

#: Handbook screenshot -> overview image of the README and the Sphinx start page
OVERVIEW = {
    "hb_06_gebaeude": "project_management_tab.png",
    "hb_07_waermebedarf": "building_load_profiles.png",
    "hb_10_karte_netz": "leaflet_map_tab.png",
    "hb_14_netzberechnung": "net_simulation_tab.png",
    "hb_17_erzeuger": "heat_generator_definition.png",
}

NAME = "Zittau_Altstadt"
SOURCE_CSV = os.path.join(H.INPUTS, "zittau_quartier.csv")
#: Files of an earlier scenario run, used when a live service fails
FALLBACK_PROJECT = os.path.join(_E2E, "_work", "projects", NAME)
PRODUCER_WGS84 = "14.8095, 50.8962"
ZITTAU = (50.8963, 14.8072, "Zittau")


def project():
    return H.project_path(NAME)


def variant_file(*parts):
    return os.path.join(project(), "Variante 1", *parts)


WINDOW_SIZE = (1600, 1000)
_window_settled = [False]


def save(widget, name):
    """Screenshot of ``widget`` as a 256-colour PNG in the handbook folder (and as overview image)."""
    from PIL import Image

    if widget is H.VIEW and H.VIEW.main_interface_widget is not None and not _window_settled[0]:
        # Switching from the welcome screen leaves the menu bar folded ("»") until the next resize.
        # Once only: a resize makes the web views redraw, and a screenshot right after is blank.
        H.VIEW.showNormal()
        H.VIEW.resize(WINDOW_SIZE[0] - 1, WINDOW_SIZE[1])
        H.pump(0.3)
        H.VIEW.resize(*WINDOW_SIZE)
        H.pump(1)
        _window_settled[0] = True
    path = H.shot(widget, name)
    image = Image.open(path).convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    os.makedirs(HANDBOOK_IMAGES, exist_ok=True)
    target = os.path.join(HANDBOOK_IMAGES, f"{name}.png")
    image.save(target, optimize=True)
    if name in OVERVIEW:
        for folder in (DOCS_IMAGES, README_IMAGES):
            image.save(os.path.join(folder, OVERVIEW[name]), optimize=True)
    H.log("DOC", name, f"{image.size[0]}x{image.size[1]}, {os.path.getsize(target) // 1024} kB")


def fallback(label, *relative):
    """Copy a file of the earlier scenario run into the project (a live service failed)."""
    source = os.path.join(FALLBACK_PROJECT, *relative)
    target = os.path.join(project(), *relative)
    if not os.path.exists(source):
        H.log("DOC-FALLBACK-MISSING", label, source)
        return False
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copy(source, target)
    H.log("DOC-FALLBACK", label, source)
    return True


def ensure_open():
    if H.VIEW.presenter.folder_manager.project_folder != project():
        H.open_project(project(), variant="Variante 1")


# ── Steps ─────────────────────────────────────────────────────────────────────


def welcome():
    from districtheatingsim.gui.welcome_screen import ElidedLabel

    H.pump(1)
    # The bundled example lives in the developer's checkout; show where an installation keeps it
    for label in H.VIEW.findChildren(ElidedLabel):
        if "project_data" in label.full_text():
            label._full_text = os.path.join("C:\\", "DistrictHeatingSim", "project_data", "Görlitz")
            label.setText(label._full_text)
    save(H.VIEW, "hb_01_willkommen")


def assistant():
    """Assistant 'Neues Projekt' (place search with Nominatim), then the table import."""
    H.fresh_project_slot(NAME)
    source = os.path.join(H.WORK, "zittau_quartier.csv")
    shutil.copy(SOURCE_CSV, source)

    def fill(wizard):
        wizard.resize(760, 640)
        wizard.show()
        wizard.restart()
        wizard.project_page.folder_edit.setText(H.PROJECTS)
        wizard.project_page.name_edit.setText(NAME)
        H.pump(0.5)
        save(wizard, "hb_02_assistent_projekt")
        wizard.next()
        page = wizard.location_page
        page.place_edit.setText("Zittau")
        try:
            page.search_place()
            H.wait_until(lambda: not page._search_thread.isRunning(), 60, "place search")
        except Exception as e:
            H.log("DOC-FALLBACK", "place search", e)
        if "Zittau" not in page.place_label.text():
            page.set_place(*ZITTAU)
        H.pump(1)
        save(wizard, "hb_03_assistent_ort")
        wizard.next()
        wizard.buildings_page.buttons["import"].setChecked(True)
        H.pump(0.5)
        save(wizard, "hb_04_assistent_gebaeude")
        wizard.hide()

    H.DIALOG_HANDLERS["NewProjectWizard"] = [fill]
    H.FILE_ANSWERS.append(source)  # the import that follows the assistant
    H.VIEW.welcome_screen.new_project_clicked()
    H.pump(3)


def import_mapping():
    """The column assignment of a table in another format (the Freiburg Excel export)."""
    from districtheatingsim.gui.ProjectTab.csv_import_dialog import CsvImportDialog

    dialog = CsvImportDialog(os.path.join(H.INPUTS, "freiburg_excel_export.csv"), parent=H.VIEW)
    dialog.resize(1150, 760)
    dialog.show()
    H.pump(1)
    save(dialog, "hb_05_import_zuordnung")
    dialog.close()


def geocoding():
    ensure_open()
    tab = H.VIEW.projectTab
    H.VIEW.tabWidget.setCurrentIndex(0)
    tab.presenter.geocode_current_csv()
    H.wait_until(H.thread_finished(tab.presenter, "geocodingThread"), 300, "geocoding")
    H.pump(1)
    csv = os.path.join(project(), "Definition Quartier IST", "Quartier IST.csv")
    if "UTM_X" not in open(csv, encoding="utf-8-sig").readline():
        fallback("geocoding", "Definition Quartier IST", "Quartier IST.csv")
        tab.presenter.load_csv(csv)
    H.pump(1)
    # The left half needs its width for the buttons; show the table from the address on
    table = tab.view.csvTable
    headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    if "Adresse" in headers:
        table.horizontalScrollBar().setValue(headers.index("Adresse"))
    save(H.VIEW, "hb_06_gebaeude")


def heat_demand():
    ensure_open()
    tab = H.VIEW.buildingTab
    H.VIEW.tabWidget.setCurrentIndex(1)
    tab.presenter.load_csv(os.path.join(project(), "Definition Quartier IST", "Quartier IST.csv"), show_dialog=False)
    tab.presenter.calculate_heat_demand()
    H.wait_until(H.thread_finished(tab.presenter, "_calc_thread"), 600, "heat demand")
    H.pump(2)
    save(H.VIEW, "hb_07_waermebedarf")


def streets():
    """OSM streets in a 150 m buffer around the buildings."""
    ensure_open()
    H.VIEW.tabWidget.setCurrentIndex(2)
    H.pump(3)
    presenter = H.VIEW.visTab2.presenter
    target = os.path.join(project(), "Eingangsdaten allgemein", "Straßen.geojson")
    presenter.open_osm_data_dialog()
    H.pump(1)
    dialog = H.find_top("DownloadOSMDataDialog")
    dialog.areaTypeComboBox.setCurrentIndex(1)  # Bereich um Gebäude aus CSV
    dialog.bufferLineEdit.setText("150")
    H.pump(0.5)
    save(dialog, "hb_08_strassen")
    dialog.startQuery()
    H.wait_until(lambda: not dialog.isVisible() or not dialog.download_thread.isRunning(), 600, "streets")
    H.pump(2)
    if dialog.isVisible():
        dialog.close()
    if not os.path.exists(target):
        fallback("streets", "Eingangsdaten allgemein", "Straßen.geojson")


def network():
    """OSMnx network along the streets with one producer east of the quarter."""
    ensure_open()
    H.VIEW.tabWidget.setCurrentIndex(2)
    H.pump(2)
    presenter = H.VIEW.visTab2.presenter
    presenter.open_layer_generation_dialog()
    H.pump(1)
    dialog = H.find_top("LayerGenerationDialog")
    dialog.coordSystemComboBox.setCurrentText("WGS84")
    dialog.coordInput.setText(PRODUCER_WGS84)
    dialog.addCoordFromInput()
    dialog.generationModeComboBox.setCurrentText("OSMnx")
    dialog.resize(900, 760)
    H.pump(0.5)
    save(dialog, "hb_09_netz_erzeugen")
    dialog.onAccept()
    H.pump(1)
    H.wait_until(H.thread_finished(presenter, "netgenerationThread"), 900, "network generation")
    H.pump(4)
    if not os.path.exists(variant_file("Wärmenetz", "Wärmenetz.geojson")):
        fallback("network", "Variante 1", "Wärmenetz", "Wärmenetz.geojson")
        H.open_project(project(), variant="Variante 1")
        H.VIEW.tabWidget.setCurrentIndex(2)
        H.pump(6)
    web_view = H.VIEW.visTab2.view.web_view
    # The downloaded streets would cover the network; hide them like a user unticking the layer
    H.run_js(
        web_view,
        """document.querySelectorAll('#layerList li.layer-item').forEach(function (li) {
             var name = li.querySelector('.layer-name');
             var box = li.querySelector('.layer-visibility');
             if (name && box && name.textContent.trim() === 'Straßen' && box.checked) { box.click(); }
           }); true""",
    )
    H.map_fit_all(web_view)
    H.pump(5)
    save(H.VIEW, "hb_10_karte_netz")


def hydraulics():
    """pandapipes initialisation (dialog tabs), simplified yearly time series, the traffic light."""
    from districtheatingsim.gui.NetSimulationTab.network_info_panel import NetworkInfoPanel

    ensure_open()
    tab = H.VIEW.calcTab

    def initialise(dialog):
        dialog.resize(920, 820)
        dialog.show()
        dialog.tabs.setCurrentWidget(dialog.network_config_tab)
        H.pump(1)
        save(dialog, "hb_11_netzinitialisierung")
        dialog.tabs.setCurrentWidget(dialog.diameter_optimization_tab)
        H.pump(0.5)
        save(dialog, "hb_12_durchmesser")
        dialog.generateNetwork()
        return dialog.result()

    def time_series(dialog):
        dialog.show()
        dialog.simplifiedCalcRadio.setChecked(True)
        H.pump(0.5)
        save(dialog, "hb_13_zeitreihe")
        dialog.onAccept()
        return dialog.result()

    H.DIALOG_HANDLERS["NetGenerationDialog"] = [initialise]
    tab.openNetGenerationDialog()
    H.wait_until(H.thread_finished(tab, "_init_thread"), 900, "net initialisation")
    H.DIALOG_HANDLERS["TimeSeriesCalculationDialog"] = [time_series]
    tab.opencalculateNetDialog()
    H.wait_until(H.thread_finished(tab, "_calc_thread"), 900, "time series")
    tab.saveNet(show_dialog=False)
    H.VIEW.tabWidget.setCurrentIndex(3)
    H.pump(15)  # plotly and its base map
    save(H.VIEW, "hb_14_netzberechnung")
    panel = H.VIEW.findChildren(NetworkInfoPanel)[0]
    bar = panel._scroll.verticalScrollBar()
    bar.setValue(bar.maximum())
    H.pump(1)
    save(panel, "hb_15_ampel_netz")


def _technology(tech_type, fields, screenshot=None):
    def handle(dialog):
        H.set_dialog_fields(dialog.dialog, fields)
        if screenshot:
            dialog.resize(760, 900)
            dialog.show()
            H.pump(1)
            save(dialog, screenshot)

    return tech_type, handle


def generators():
    """Solar thermal + biomass + gas boiler, results with the traffic light; a gas-only configuration."""
    from districtheatingsim.gui.EnergySystemTab._02_energy_system_dialogs import WeightDialog

    ensure_open()
    H.VIEW.tabWidget.setCurrentIndex(4)
    H.pump(2)
    tab = H.VIEW.energySystemTab
    technologies = [
        _technology(
            "Solarthermie",
            {"bruttofläche_STA": 400, "vs": 40, "Longitude": "-14.807", "Latitude": "50.897"},
            "hb_16_erzeuger_dialog",
        ),
        _technology("Biomassekessel", {"thermal_capacity_kW": 250, "speicher_aktiv": True}),
        _technology("Gaskessel", {"thermal_capacity_kW": 900}),
    ]
    H.DIALOG_HANDLERS["TechInputDialog"] = [handler for _, handler in technologies]
    for tech_type, _ in technologies:
        tab.techTab.addTech(tech_type, None)
    H.pump(1)
    tab.tabWidget.setCurrentIndex(0)
    tab.techTab.loadFileAndPlot()  # the load profile was written by the time series after the tab was built
    H.pump(1)
    save(H.VIEW, "hb_17_erzeuger")
    tab.calculate_energy_system()
    H.wait_until(H.thread_finished(tab, "calculationThread"), 1800, "calculation")
    H.pump(1)
    tab.tabWidget.setCurrentIndex(1)
    H.pump(1)
    save(H.VIEW, "hb_18_kosten")
    tab.tabWidget.setCurrentIndex(2)
    H.pump(2)
    save(H.VIEW, "hb_19_ergebnisse")
    results = tab.resultTab
    results.scrollArea.ensureWidgetVisible(results.table3_section)
    H.pump(1)
    save(H.VIEW, "hb_20_ampel_erzeuger")
    tab.tabWidget.setCurrentIndex(0)
    tab.save_results_JSON(show_dialog=False)

    weights = WeightDialog()
    weights.resize(560, 330)
    weights.show()
    H.pump(0.5)
    save(weights, "hb_21_gewichte")
    weights.close()

    # A second configuration for the comparison
    H.INPUT_ANSWERS.append(("Nur_Gaskessel", True))
    tab._new_config_action()
    H.DIALOG_HANDLERS["TechInputDialog"] = [_technology("Gaskessel", {"thermal_capacity_kW": 900})[1]]
    tab.techTab.addTech("Gaskessel", None)
    tab.calculate_energy_system()
    H.wait_until(H.thread_finished(tab, "calculationThread"), 1800, "calculation (gas only)")
    tab.save_results_JSON(show_dialog=False)


def comparison():
    ensure_open()
    H.VIEW.tabWidget.setCurrentIndex(5)
    H.VIEW.comparisonTab.project_explorer.discover_projects()
    H.pump(3)
    save(H.VIEW, "hb_22_vergleich")


if __name__ == "__main__":
    if os.path.exists(H.RECENT_FILE[0]):
        os.remove(H.RECENT_FILE[0])  # the welcome screen shows no work projects
    # The app picks the theme by the time of day (dark from 18:00); the documentation is light
    import districtheatingsim.utilities.utilities as app_utilities

    app_utilities.get_stylesheet_based_on_time = lambda: "light_theme_style_path"
    H.start_app(size=WINDOW_SIZE)
    H.VIEW.applyTheme("light_theme_style_path")
    H.VIEW.sync_theme_toggle_state()
    H.run_steps(
        {
            "welcome": welcome,
            "assistant": assistant,
            "import_mapping": import_mapping,
            "geocoding": geocoding,
            "heat_demand": heat_demand,
            "streets": streets,
            "network": network,
            "hydraulics": hydraulics,
            "generators": generators,
            "comparison": comparison,
        }
    )
