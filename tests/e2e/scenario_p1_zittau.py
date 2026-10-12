"""
Scenario P1 – Zittau Altstadt: the core workflow with an address list
======================================================================

15 buildings (BDEW mix GKO/GHA/GBD/GBH/HMF/HEF) from a ready-made address CSV, geocoded with
Nominatim, network along OSM streets (OSMnx), pandapipes initialisation and simplified time
series, four generator configurations, a second variant (static 75 °C) and the comparison tab,
optimisation, Sankey, sensitivity and CSV export.

Reproduces (ANWENDERTEST_2026-10-08.md): K3 (import does not reach the project CSV, geocoding
writes into the source file), K1 (pipe heat losses – see also analysis_net_losses.py), H3
(Overpass failures), H4 (connectivity false alarm), M3 (map zoom/duplicate layers), M9 (export
without file dialog), M10/M11/M15 (results), H10 (variant copy keeps stale results), M7.

Run all steps: ``python tests/e2e/scenario_p1_zittau.py``
Run some steps on an existing project: ``python tests/e2e/scenario_p1_zittau.py energy variant``
"""

import os
import shutil
import time

import harness as H
import pandas as pd

NAME = "Zittau_Altstadt"
SOURCE_CSV = os.path.join(H.INPUTS, "zittau_quartier.csv")
#: Producer east of the quarter (lon, lat)
PRODUCER_WGS84 = "14.8095, 50.8962"


def project():
    return H.project_path(NAME)


def project_csv():
    return os.path.join(project(), "Definition Quartier IST", "Quartier IST.csv")


def ensure_open():
    if H.VIEW.presenter.folder_manager.project_folder != project():
        H.open_project(project(), variant="Variante 1")


def setup():
    """New project, 'CSV importieren' with a file already in the internal schema, geocoding."""
    H.fresh_project_slot(NAME)
    # Work on a copy: before the K3 fix the geocoding wrote into the imported file itself.
    source = os.path.join(H.WORK, "zittau_quartier_input.csv")
    shutil.copy(SOURCE_CSV, source)
    H.new_project(NAME)
    tab = H.VIEW.projectTab
    H.FILE_ANSWERS.append(source)
    tab.presenter.import_csv()
    H.pump(1)
    H.log("STATE", "table", f"{tab.view.csvTable.rowCount()} rows, file={tab.presenter.model.current_file_path}")
    tab.presenter.geocode_current_csv()
    H.wait_until(H.thread_finished(tab.presenter, "geocodingThread"), 300, "geocoding")
    H.pump(1)
    H.log("STATE", "progress label", tab.view.csv_status_label.text())
    H.log("CHECK K3", "source file modified", "UTM_X" in open(source, encoding="utf-8-sig").readline())
    data = pd.read_csv(project_csv(), sep=";", encoding="utf-8-sig")
    H.log("CHECK K3", "project CSV rows / has UTM", f"{len(data)} / {'UTM_X' in data.columns}")
    if "UTM_X" not in data.columns:
        # WORKAROUND K3: the user copies the geocoded file into the project by hand.
        shutil.copy(source, project_csv())
        H.log("WORKAROUND", "K3", "geocoded source copied into the project")
    H.shot(H.VIEW, "p1_setup")


def heat_demand():
    ensure_open()
    tab = H.VIEW.buildingTab
    H.VIEW.tabWidget.setCurrentIndex(1)
    tab.presenter.load_csv(project_csv(), show_dialog=False)
    tab.presenter.calculate_heat_demand()
    H.wait_until(H.thread_finished(tab.presenter, "_calc_thread"), 600, "heat demand")
    H.pump(1)
    H.shot(H.VIEW, "p1_heat_demand")


def streets():
    """OSM street download in a 150 m buffer around the buildings (retries like a user would)."""
    ensure_open()
    H.VIEW.tabWidget.setCurrentIndex(2)
    H.pump(2)
    presenter = H.VIEW.visTab2.presenter
    target = os.path.join(project(), "Eingangsdaten allgemein", "Straßen.geojson")
    for attempt in range(3):
        presenter.open_osm_data_dialog()
        H.pump(1)
        dialog = H.find_top("DownloadOSMDataDialog")
        H.log(
            "STATE",
            "dialog defaults",
            f"area={dialog.areaTypeComboBox.currentText()} city={dialog.cityLineEdit.text()}",
        )
        dialog.areaTypeComboBox.setCurrentIndex(1)  # Bereich um Gebäude aus CSV
        dialog.bufferLineEdit.setText("150")
        dialog.startQuery()
        H.wait_until(
            lambda d=dialog: not d.isVisible() or not d.download_thread.isRunning(), 600, f"streets #{attempt + 1}"
        )
        H.pump(2)
        if os.path.exists(target):
            break
        dialog.close()
        H.pump(30)


def network():
    """OSMnx network generation with one producer given in WGS84, then the connectivity check."""
    ensure_open()
    H.VIEW.tabWidget.setCurrentIndex(2)
    H.pump(2)
    presenter = H.VIEW.visTab2.presenter
    presenter.open_layer_generation_dialog()
    H.pump(1)
    dialog = H.find_top("LayerGenerationDialog")
    H.log("STATE", "default producer coordinate (M4)", dialog.coordInput.text())
    dialog.coordSystemComboBox.setCurrentText("WGS84")
    dialog.coordInput.setText(PRODUCER_WGS84)
    dialog.addCoordFromInput()
    dialog.generationModeComboBox.setCurrentText("OSMnx")
    dialog.onAccept()
    H.pump(1)
    H.wait_until(H.thread_finished(presenter, "netgenerationThread"), 900, "network generation")
    H.pump(4)
    H.shot(H.VIEW, "p1_network_as_shown")
    H.log("STATE", "map layers (M3)", H.map_layer_names(H.VIEW.visTab2.view.web_view))
    H.map_fit_all(H.VIEW.visTab2.view.web_view)
    H.shot(H.VIEW, "p1_network_fitted")
    presenter.check_network_connectivity_action()
    H.pump(1)


def _accept_net_generation(dialog):
    dialog.generateNetwork()
    return dialog.result()


def _simplified_time_series(dialog):
    dialog.simplifiedCalcRadio.setChecked(True)
    dialog.onAccept()
    return dialog.result()


def hydraulics():
    """pandapipes initialisation with the defaults, simplified yearly time series, save."""
    ensure_open()
    tab = H.VIEW.calcTab
    H.DIALOG_HANDLERS["NetGenerationDialog"] = [_accept_net_generation]
    tab.openNetGenerationDialog()
    H.wait_until(H.thread_finished(tab, "_init_thread"), 900, "net initialisation")
    net = tab.NetworkGenerationData.net
    H.log(
        "RESULT",
        "net",
        f"pipes={len(net.pipe)} consumers={len(net.heat_consumer)} "
        f"lift={net.circ_pump_pressure.plift_bar.iloc[0]:.2f} bar "
        f"pump={net.res_circ_pump_pressure.qext_w.sum() / 1000:.1f} kW "
        f"consumers={net.heat_consumer.qext_w.sum() / 1000:.1f} kW",
    )
    H.DIALOG_HANDLERS["TimeSeriesCalculationDialog"] = [_simplified_time_series]
    tab.opencalculateNetDialog()
    H.wait_until(H.thread_finished(tab, "_calc_thread"), 900, "time series (simplified)")
    tab.saveNet(show_dialog=False)
    H.VIEW.tabWidget.setCurrentIndex(3)
    H.pump(2)
    H.shot(H.VIEW, "p1_hydraulics")


def _calculate_and_save(label):
    tab = H.VIEW.energySystemTab
    tab.calculate_energy_system()
    H.wait_until(H.thread_finished(tab, "calculationThread"), 1800, f"calculation {label}")
    H.pump(1)
    results = tab.energy_system.results
    H.log(
        "RESULT",
        label,
        {
            "WGK": results.get("WGK_Gesamt"),
            "CO2": results.get("specific_emissions_Gesamt"),
            "PEF": results.get("primärenergiefaktor_Gesamt"),
            "Wärmemengen": dict(zip(results.get("techs", []), results.get("Wärmemengen", []), strict=False)),
        },
    )
    for index, name in enumerate(("tech", "cost", "results")):
        tab.tabWidget.setCurrentIndex(index)
        H.pump(1)
        H.shot(H.VIEW, f"p1_energy_{label}_{name}")
    tab.tabWidget.setCurrentIndex(0)
    tab.save_results_JSON(show_dialog=False)


def _configuration(name, technologies):
    tab = H.VIEW.energySystemTab
    if name != "Standard":
        H.INPUT_ANSWERS.append((name, True))
        tab._new_config_action()
    H.DIALOG_HANDLERS["TechInputDialog"] = [H.tech_handler(fields) for _, fields in technologies]
    for tech_type, _ in technologies:
        tab.techTab.addTech(tech_type, None)
    H.pump(0.5)
    _calculate_and_save(name)


def energy():
    """Four generator configurations (first one = 'Standard')."""
    ensure_open()
    H.VIEW.tabWidget.setCurrentIndex(4)
    H.pump(1)
    _configuration("Standard", [("Gaskessel", {"thermal_capacity_kW": 900})])
    _configuration(
        "BHKW_Kessel",
        [("BHKW", {"th_Leistung_kW": 150, "speicher_aktiv": True}), ("Gaskessel", {"thermal_capacity_kW": 900})],
    )
    _configuration(
        "Solar_Bio",
        [
            ("Solarthermie", {"bruttofläche_STA": 400, "vs": 40, "Longitude": "-14.807", "Latitude": "50.897"}),
            ("Biomassekessel", {"thermal_capacity_kW": 250, "speicher_aktiv": True}),
            ("Gaskessel", {"thermal_capacity_kW": 900}),
        ],
    )
    _configuration(
        "WP_Speicher",
        [
            ("Abwärmepumpe", {"Kühlleistung_Abwärme": 120, "Temperatur_Abwärme": 25}),
            ("Power-to-Heat", {"thermal_capacity_kW": 300}),
            ("Thermischer Netzspeicher", {}),
            ("Gaskessel", {"thermal_capacity_kW": 900}),
        ],
    )


def outdated():
    """H10/M14: after everything was computed, save, change a building, recalculate - what is outdated?"""
    ensure_open()
    presenter = H.VIEW.projectTab.presenter
    explorer = H.VIEW.comparisonTab.project_explorer

    def check(label):
        presenter.update_progress_tracker()
        H.log("CHECK H10", f"{label}: tracker", presenter.view.outdated_label.text() or "(nichts veraltet)")
        H.log("CHECK H10", f"{label}: steps", {s["key"]: s.get("outdated") for s in presenter.process_steps})
        explorer.discover_projects()
        variant = explorer.project_tree.topLevelItem(0)
        H.log("CHECK H10", f"{label}: comparison", [variant.child(i).text(0) for i in range(variant.childCount())])

    check("after the calculation")
    H.VIEW.save_all_project_results()  # rewrites every file - must not make anything outdated
    check("after saving the project")

    table = presenter.view.csvTable
    headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    column = headers.index("Wärmebedarf")
    changed = f"{float(table.item(0, column).text()) * 1.1:.0f}"
    table.item(0, column).setText(changed)
    presenter.save_csv(show_dialog=False)
    check("after changing a building")
    H.VIEW.save_all_project_results()
    stored = pd.read_csv(project_csv(), sep=";", encoding="utf-8-sig", dtype=str)["Wärmebedarf"].iloc[0]
    H.log("CHECK M13", "changed building survives a project save", (changed, stored))

    building_tab = H.VIEW.buildingTab
    building_tab.presenter.load_csv(project_csv(), show_dialog=False)
    building_tab.presenter.calculate_heat_demand()
    H.wait_until(H.thread_finished(building_tab.presenter, "_calc_thread"), 600, "heat demand")
    check("after recalculating the load profiles")
    H.VIEW.tabWidget.setCurrentIndex(0)
    H.pump(1)
    H.shot(H.VIEW, "p1_outdated")


def _static_75(dialog):
    config = dialog.network_config_tab
    config.supplyTemperatureControlInput.setCurrentText("Statisch")
    H.pump(0.3)
    config.parameter_rows_net[0].itemAt(1).widget().setText("75")
    dialog.generateNetwork()
    return dialog.result()


def variant():
    """Variant copy with static 75 °C supply, recalculated, then the comparison tab."""
    ensure_open()
    view = H.VIEW
    view.tabWidget.setCurrentIndex(5)
    H.pump(2)
    H.shot(view, "p1_comparison_initial")
    H.MSGBOX_ANSWERS.append("Ohne Speichern")
    view.on_create_project_variant_copy()
    H.pump(3)
    tab = view.calcTab
    H.DIALOG_HANDLERS["NetGenerationDialog"] = [_static_75]
    tab.openNetGenerationDialog()
    H.wait_until(H.thread_finished(tab, "_init_thread"), 900, "net initialisation (variant 2)")
    H.DIALOG_HANDLERS["TimeSeriesCalculationDialog"] = [_simplified_time_series]
    tab.opencalculateNetDialog()
    H.wait_until(H.thread_finished(tab, "_calc_thread"), 900, "time series (variant 2)")
    tab.saveNet(show_dialog=False)
    energy_tab = view.energySystemTab
    H.log("STATE", "configs copied into variant 2 (H10)", [energy_tab.configCombo.itemText(i) for i in range(4)])
    _calculate_and_save("Variante2_Standard")
    view.tabWidget.setCurrentIndex(5)
    view.comparisonTab.project_explorer.discover_projects()
    H.pump(2)
    H.log("RESULT", "comparison", [(d["name"], d.get("WGK_Gesamt")) for d in view.comparisonTab.variant_data])
    H.shot(view, "p1_comparison")


def optimize():
    """Optimisation of 'Solar_Bio', Sankey, sensitivity and CSV export."""
    ensure_open()
    tab = H.VIEW.energySystemTab
    H.VIEW.tabWidget.setCurrentIndex(4)
    tab.configCombo.setCurrentText("Solar_Bio")
    H.pump(2)
    H.DIALOG_HANDLERS["WeightDialog"] = [lambda dialog: None]
    started = time.time()
    tab.start_optimization()
    H.wait_until(H.thread_finished(tab, "calculationThread"), 3600, "optimisation")
    H.pump(1)
    H.log("RESULT", "optimised", f"{time.time() - started:.0f}s WGK={tab.energy_system.results.get('WGK_Gesamt')}")
    H.log("RESULT", "optimised technologies", [t.get_display_text() for t in tab.energy_system.technologies])
    H.DIALOG_HANDLERS["SankeyDialog"] = [lambda dialog: H.shot(dialog, "p1_sankey") and None]
    tab.show_sankey()
    tab.tabWidget.setCurrentIndex(3)
    tab.sensitivityTab.start_sensitivity_analysis()
    H.pump(30)
    H.shot(H.VIEW, "p1_sensitivity")
    H.FILE_ANSWERS.append(os.path.join(H.WORK, "p1_export.csv"))
    tab.save_heat_generation_results_to_csv()
    H.log("CHECK M9", "export at the chosen path", os.path.exists(os.path.join(H.WORK, "p1_export.csv")))


if __name__ == "__main__":
    H.start_app()
    H.run_steps(
        {
            "setup": setup,
            "heat_demand": heat_demand,
            "streets": streets,
            "network": network,
            "hydraulics": hydraulics,
            "energy": energy,
            "outdated": outdated,
            "variant": variant,
            "optimize": optimize,
        }
    )
