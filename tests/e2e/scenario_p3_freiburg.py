"""
Scenario P3 – Freiburg-Vauban: an Excel export, outside UTM zone 33
====================================================================

12 buildings (VDI 4655 EFH/MFH) delivered the way planners get them: an Excel "CSV
(Trennzeichen-getrennt)" export in Windows-1252 with its own column names, street and house
number in separate columns and decimal commas. The project lies in UTM zone 32.

Reproduces (ANWENDERTEST_2026-10-08.md): H5 (cp1252 → UnicodeDecodeError; decimal comma passes
the import and breaks the heat demand; street + number cannot be combined), K2 (default CRS
25833 → negative easting, CRS change does not reproject, producer geocoding always 25833, OSMnx
export labelled 25833), H6 (duplicate / street-only geocoding not reported), H9 (Görlitz
climate data), H4 (MST networks with unconnected house connections).

Run: ``python tests/e2e/scenario_p3_freiburg.py``
"""

import os

import harness as H
import pandas as pd

NAME = "Freiburg_Vauban"
EXCEL_EXPORT = os.path.join(H.INPUTS, "freiburg_excel_export.csv")
UTF8_EXPORT = os.path.join(H.INPUTS, "freiburg_utf8.csv")
PRODUCER_ADDRESS = "Deutschland,Baden-Württemberg,Freiburg im Breisgau,Vaubanallee 2"
PRODUCER_WGS84 = "7.8296, 47.9787"


def project():
    return H.project_path(NAME)


def project_csv():
    return os.path.join(project(), "Definition Quartier IST", "Quartier IST.csv")


def ensure_open():
    if H.VIEW.presenter.folder_manager.project_folder != project():
        H.open_project(project())


def _map_columns(dialog):
    from districtheatingsim.gui.ProjectTab.csv_import_dialog import TARGET_COLUMNS

    keys = [column[0] for column in TARGET_COLUMNS]
    automatic = {keys[row]: dialog.table.cellWidget(row, dialog._COL_SOURCE).currentText() for row in range(len(keys))}
    H.log("CHECK H5", "automatic mapping", automatic)
    addition = dialog.table.cellWidget(keys.index("Adresse"), dialog._COL_ADDITION).currentText()
    H.log("CHECK H5", "appended to the address", addition)
    # Only the federal state is not in the file.
    dialog.table.cellWidget(keys.index("Bundesland"), dialog._COL_DEFAULT).setText("Baden-Württemberg")
    H.shot(dialog, "p3_mapping")
    dialog._on_import()
    return dialog.result()


def import_excel():
    """New project; import the cp1252 export, then the UTF-8 version through the mapping dialog."""
    H.fresh_project_slot(NAME)
    H.new_project(NAME)
    tab = H.VIEW.projectTab
    H.FILE_ANSWERS.append(EXCEL_EXPORT)
    H.DIALOG_HANDLERS["CsvImportDialog"] = [_map_columns]
    try:
        tab.presenter.import_csv()
    except Exception as e:
        H.log("CHECK H5", "cp1252 import", repr(e)[:200])
    if "Vaubanallee" not in open(project_csv(), encoding="utf-8-sig").read():
        H.FILE_ANSWERS.append(UTF8_EXPORT)
        H.DIALOG_HANDLERS["CsvImportDialog"] = [_map_columns]
        tab.presenter.import_csv()
    H.log(
        "RESULT", "project CSV", pd.read_csv(project_csv(), sep=";", encoding="utf-8-sig", dtype=str).head(3).to_dict()
    )


def geocode_default_crs():
    """Geocoding with the default CRS, then 'Vorschlagen' (K2), then the heat demand (H5 decimal comma)."""
    ensure_open()
    tab = H.VIEW.projectTab
    folder_manager = H.VIEW.presenter.folder_manager
    H.log("STATE", "CRS before geocoding", folder_manager.project_crs)
    tab.presenter.load_csv(project_csv())
    tab.presenter.geocode_current_csv()
    H.wait_until(H.thread_finished(tab.presenter, "geocodingThread"), 300, "geocoding")
    before = pd.read_csv(project_csv(), sep=";", encoding="utf-8-sig")[["Adresse", "UTM_X", "UTM_Y"]]
    H.log("CHECK K2/H6", "coordinates", before.to_dict("records"))
    tab.presenter._suggest_crs()
    after = pd.read_csv(project_csv(), sep=";", encoding="utf-8-sig")[["UTM_X", "UTM_Y"]]
    H.log(
        "CHECK K2",
        "CRS after 'Vorschlagen' / coordinates unchanged",
        (folder_manager.project_crs, after.iloc[0].to_dict()),
    )
    building_tab = H.VIEW.buildingTab
    building_tab.presenter.load_csv(project_csv(), show_dialog=False)
    building_tab.presenter.calculate_heat_demand()
    H.wait_until(lambda: not building_tab.presenter._calc_thread.isRunning(), 300, "heat demand")


def corrected_data():
    """What a user does after the errors: CRS 25832 first, house numbers, decimal points, geocode again."""
    ensure_open()
    source = pd.read_csv(UTF8_EXPORT, sep=";", dtype=str)
    data = pd.read_csv(project_csv(), sep=";", encoding="utf-8-sig", dtype=str)
    data["Adresse"] = (source["Straße"] + " " + source["Hausnr."]).values
    data["WW_Anteil"] = data["WW_Anteil"].str.replace(",", ".")
    data = data.drop(columns=[c for c in ("UTM_X", "UTM_Y") if c in data.columns])
    data.to_csv(project_csv(), sep=";", index=False, encoding="utf-8-sig")
    H.VIEW.presenter.folder_manager.set_project_crs("EPSG:25832")
    tab = H.VIEW.projectTab
    tab.presenter.load_csv(project_csv())
    tab.presenter.geocode_current_csv()
    H.wait_until(H.thread_finished(tab.presenter, "geocodingThread"), 300, "geocoding (25832)")
    geocoded = pd.read_csv(project_csv(), sep=";", encoding="utf-8-sig")
    H.log("RESULT", "coordinates 25832", geocoded[["Adresse", "UTM_X", "UTM_Y"]].to_dict("records"))
    building_tab = H.VIEW.buildingTab
    building_tab.presenter.load_csv(project_csv(), show_dialog=False)
    building_tab.presenter.calculate_heat_demand()
    H.wait_until(H.thread_finished(building_tab.presenter, "_calc_thread"), 300, "heat demand")


def producer_geocoding():
    """'Adresse geocodieren' in the network dialog (K2: always EPSG:25833)."""
    ensure_open()
    from districtheatingsim.geocoding.geocoding import get_coordinates

    H.VIEW.tabWidget.setCurrentIndex(2)
    H.pump(2)
    H.VIEW.visTab2.presenter.open_layer_generation_dialog()
    H.pump(1)
    dialog = H.find_top("LayerGenerationDialog")
    dialog.locationModeComboBox.setCurrentIndex(1)
    dialog.addressInput.setText(PRODUCER_ADDRESS)
    dialog.geocodeAndAdd()
    table = [
        (dialog.coordTable.item(r, 0).text(), dialog.coordTable.item(r, 1).text())
        for r in range(dialog.coordTable.rowCount())
    ]
    H.log("CHECK K2", "producer from the dialog", table)
    expected = get_coordinates(
        "Vaubanallee 2, Freiburg im Breisgau, Baden-Württemberg, Deutschland", to_crs="EPSG:25832"
    )
    H.log("CHECK K2", "expected in EPSG:25832", expected)
    dialog.close()


def networks():
    """Street download, then MST / Advanced MST / OSMnx with a WGS84 producer, each with a connectivity check."""
    ensure_open()
    view = H.VIEW
    view.tabWidget.setCurrentIndex(2)
    H.pump(2)
    presenter = view.visTab2.presenter
    streets = os.path.join(project(), "Eingangsdaten allgemein", "Straßen.geojson")
    for attempt in range(3):
        if os.path.exists(streets):
            break
        presenter.open_osm_data_dialog()
        H.pump(1)
        dialog = H.find_top("DownloadOSMDataDialog")
        dialog.areaTypeComboBox.setCurrentIndex(1)
        dialog.bufferLineEdit.setText("150")
        dialog.startQuery()
        H.wait_until(
            lambda d=dialog: not d.isVisible() or not d.download_thread.isRunning(), 600, f"streets #{attempt + 1}"
        )
        H.pump(2)
        if not os.path.exists(streets):
            dialog.close()
            H.pump(30)
    for mode in ("Advanced MST", "MST", "OSMnx"):
        presenter.open_layer_generation_dialog()
        H.pump(1)
        dialog = H.find_top("LayerGenerationDialog")
        dialog.coordSystemComboBox.setCurrentText("WGS84")
        dialog.coordInput.setText(PRODUCER_WGS84)
        dialog.addCoordFromInput()
        dialog.generationModeComboBox.setCurrentText(mode)
        dialog.onAccept()
        H.wait_until(H.thread_finished(presenter, "netgenerationThread"), 900, f"network {mode}")
        H.pump(3)
        network = os.path.join(project(), "Variante 1", "Wärmenetz", "Wärmenetz.geojson")
        import geopandas as gpd

        frame = gpd.read_file(network)
        flow = frame[frame.feature_type == "network_line_flow"]
        H.log("RESULT", f"network {mode}", f"crs={frame.crs} trench={flow.length.sum():.0f} m")
        H.log("CHECK K2", f"map bounds {mode}", H.map_fit_all(view.visTab2.view.web_view))
        H.shot(view, f"p3_network_{mode.replace(' ', '_')}")
        H.MSGBOX_ANSWERS.append(None)  # yes to auto-snap
        presenter.check_network_connectivity_action()
        H.pump(1)


if __name__ == "__main__":
    H.start_app()
    H.run_steps(
        {
            "import_excel": import_excel,
            "geocode_default_crs": geocode_default_crs,
            "corrected_data": corrected_data,
            "producer_geocoding": producer_geocoding,
            "networks": networks,
        }
    )
