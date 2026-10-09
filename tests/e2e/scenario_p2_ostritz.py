"""
Scenario P2 – Ostritz village core: buildings from OpenStreetMap
=================================================================

Draws a ~500 m × 450 m polygon on the map, downloads the OSM buildings, converts them with
"CSV aus OSM-GeoJSON" (reverse geocoding), then runs heat demand, OSMnx network generation,
pandapipes initialisation and the simplified time series for ~240 buildings.

Reproduces (ANWENDERTEST_2026-10-08.md): H3 (Overpass "Server load too high"), K5 (no rate limit
→ Nominatim HTTP 429 → every failed lookup falls back to the pre-filled address; OSM addresses
ignored; identical demand/type for every building incl. church and garages; result not written
to the project CSV), H4 (connectivity false alarm), performance at village size.

Run: ``python tests/e2e/scenario_p2_ostritz.py``  (the conversion step alone takes ~20 min)
"""

import json
import os
import shutil
from collections import Counter

import harness as H
import pandas as pd

NAME = "Ostritz_Dorfkern"
#: Capture polygon (lat, lon) around the market square
POLYGON = [[51.0170, 14.9265], [51.0170, 14.9335], [51.0130, 14.9335], [51.0130, 14.9265]]
PRODUCER_WGS84 = "14.9345, 51.0128"


def project():
    return H.project_path(NAME)


def buildings_geojson():
    return os.path.join(project(), "Variante 1", "Gebäudedaten", "OSM_Gebäude.geojson")


def osm_csv():
    return os.path.join(project(), "Variante 1", "Gebäudedaten", "OSM_building_data.csv")


def project_csv():
    return os.path.join(project(), "Definition Quartier IST", "Quartier IST.csv")


def ensure_open():
    if H.VIEW.presenter.folder_manager.project_folder != project():
        H.open_project(project())


def buildings():
    """New project, OSM building query with a polygon drawn on the map (retries on Overpass errors)."""
    H.fresh_project_slot(NAME)
    H.new_project(NAME)
    H.VIEW.tabWidget.setCurrentIndex(2)
    H.pump(3)
    presenter = H.VIEW.visTab2.presenter
    for attempt in range(4):
        presenter.open_osm_building_query_dialog()
        H.pump(1)
        dialog = H.find_top("OSMBuildingQueryDialog")
        dialog.areaTypeComboBox.setCurrentText("Polygon auf Karte zeichnen")
        H.draw_polygon_on_map(H.VIEW.visTab2.view.web_view, POLYGON)
        dialog.startQuery()
        H.wait_until(
            lambda d=dialog: not d.isVisible() or not d.download_thread.isRunning(), 600, f"buildings #{attempt + 1}"
        )
        H.pump(2)
        if os.path.exists(buildings_geojson()):
            break
        dialog.close()
        H.pump(60)
    data = json.load(open(buildings_geojson(), encoding="utf-8"))
    tags = Counter(f["properties"].get("building") for f in data["features"])
    with_address = sum(1 for f in data["features"] if f["properties"].get("addr:street"))
    H.log(
        "RESULT",
        "OSM buildings",
        f"{len(data['features'])}; building tags={dict(tags)}; with addr:street={with_address}",
    )


def _record_import_defaults(dialog):
    H.log("STATE", "OSM import defaults (K5)", {key: widget.text() for key, widget in dialog.fields.items()})


def convert():
    """'CSV aus OSM-GeoJSON' in the project tab (reverse geocodes every building)."""
    ensure_open()
    H.VIEW.tabWidget.setCurrentIndex(0)
    tab = H.VIEW.projectTab
    H.DIALOG_HANDLERS["OSMImportDialog"] = [_record_import_defaults]
    H.FILE_ANSWERS.append(buildings_geojson())
    tab.presenter.create_csv_from_geojson()
    H.wait_until(H.thread_finished(tab.presenter, "geojson_conversion_thread"), 3600, "OSM -> CSV")
    data = pd.read_csv(osm_csv(), sep=";", encoding="utf-8-sig")
    H.log(
        "CHECK K5",
        "converted CSV",
        f"{len(data)} rows; duplicate addresses={int(data['Adresse'].duplicated().sum())}; "
        f"most common={data['Adresse'].value_counts().head(3).to_dict()}; demand values={data['Wärmebedarf'].unique()[:5]}",
    )
    H.log("CHECK K5", "project CSV after conversion", open(project_csv(), encoding="utf-8-sig").read()[:120])


def heat_and_network():
    """Heat demand, OSMnx network, initialisation and simplified time series for all buildings."""
    ensure_open()
    if not os.path.exists(project_csv()) or "UTM_X" not in open(project_csv(), encoding="utf-8-sig").readline():
        # WORKAROUND K5: no button moves the OSM CSV into the project.
        shutil.copy(osm_csv(), project_csv())
        H.log("WORKAROUND", "K5", "OSM CSV copied into the project")
    view = H.VIEW
    building_tab = view.buildingTab
    view.tabWidget.setCurrentIndex(1)
    building_tab.presenter.load_csv(project_csv(), show_dialog=False)
    building_tab.presenter.calculate_heat_demand()
    H.wait_until(H.thread_finished(building_tab.presenter, "_calc_thread"), 900, "heat demand")

    view.tabWidget.setCurrentIndex(2)
    H.pump(2)
    presenter = view.visTab2.presenter
    presenter.open_layer_generation_dialog()
    H.pump(1)
    dialog = H.find_top("LayerGenerationDialog")
    dialog.coordSystemComboBox.setCurrentText("WGS84")
    dialog.coordInput.setText(PRODUCER_WGS84)
    dialog.addCoordFromInput()
    dialog.generationModeComboBox.setCurrentText("OSMnx")
    dialog.onAccept()
    H.wait_until(H.thread_finished(presenter, "netgenerationThread"), 1800, "network generation")
    H.pump(3)
    H.map_fit_all(view.visTab2.view.web_view)
    H.shot(view, "p2_network")
    presenter.check_network_connectivity_action()

    tab = view.calcTab
    H.DIALOG_HANDLERS["NetGenerationDialog"] = [lambda d: d.generateNetwork() or d.result()]
    tab.openNetGenerationDialog()
    H.wait_until(H.thread_finished(tab, "_init_thread"), 3600, "net initialisation")
    net = tab.NetworkGenerationData.net
    H.log("RESULT", "net", f"pipes={len(net.pipe)} consumers={len(net.heat_consumer)}")
    H.DIALOG_HANDLERS["TimeSeriesCalculationDialog"] = [
        lambda d: d.simplifiedCalcRadio.setChecked(True) or d.onAccept() or d.result()
    ]
    tab.opencalculateNetDialog()
    H.wait_until(H.thread_finished(tab, "_calc_thread"), 900, "time series (simplified)")


if __name__ == "__main__":
    H.start_app()
    H.run_steps({"buildings": buildings, "convert": convert, "heat_and_network": heat_and_network})
