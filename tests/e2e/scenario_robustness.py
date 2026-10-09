"""
Scenario R – operating errors and edge cases
=============================================

Typical slips of a first-time user, run against the Zittau project of scenario P1 (run that
first), plus the read-only installation folder case.

Reproduces (ANWENDERTEST_2026-10-08.md): M5 (cancel "Projekt öffnen"), H8 (double click on a
sub folder in the project tree), M17 (existing project name), M8 (energy system without a load
profile / invalid input), M6 (save on close), K6 (read-only recent-projects file → projects do
not open, silently).

Run: ``python tests/e2e/scenario_robustness.py``
"""

import json
import os
import stat

import harness as H
from PyQt6.QtGui import QCloseEvent

ZITTAU = H.project_path("Zittau_Altstadt")


def cancel_open():
    """R1: 'Projekt öffnen' and cancel the folder dialog."""
    H.open_project(ZITTAU, variant="Variante 1")
    H.FILE_ANSWERS.append("")
    H.MSGBOX_ANSWERS.append("Ohne Speichern")
    H.VIEW.on_open_existing_project()
    H.log("STATE", "project after cancel", H.VIEW.presenter.folder_manager.project_folder)


def tree_double_click():
    """R2: double click on 'Eingangsdaten allgemein' in the project tree."""
    folder_manager = H.VIEW.presenter.folder_manager
    tab = H.VIEW.projectTab
    H.log("STATE", "before", f"project={folder_manager.project_folder} try={folder_manager.try_filename}")
    index = tab.view.treeView.model().index(os.path.join(ZITTAU, "Eingangsdaten allgemein"))
    tab.presenter.on_tree_view_double_clicked(index)
    H.pump(1)
    H.log("CHECK H8", "after", f"project={folder_manager.project_folder} try={folder_manager.try_filename}")
    H.log("CHECK H8", "recent projects", json.load(open(H.RECENT_FILE[0], encoding="utf-8"))["recent_projects"][:2])


def existing_name():
    """R3: create a project with the name of an existing one."""
    H.MSGBOX_ANSWERS.append("Ohne Speichern")
    H.open_project(ZITTAU, variant="Variante 1")
    H.FILE_ANSWERS.append(H.PROJECTS)
    H.INPUT_ANSWERS.append(("Zittau_Altstadt", True))
    H.MSGBOX_ANSWERS.append("Ohne Speichern")
    H.VIEW.on_create_new_project()


def energy_without_data():
    """R4/R5: calculate without technologies, with a missing load profile and with an invalid scale factor."""
    tab = H.VIEW.energySystemTab
    H.INPUT_ANSWERS.append(("Leer", True))
    tab._new_config_action()
    tab.calculate_energy_system()
    H.DIALOG_HANDLERS["TechInputDialog"] = [H.tech_handler()]
    tab.techTab.addTech("Gaskessel", None)
    tab.techTab.FilenameInput.setText(os.path.join(ZITTAU, "Variante 1", "Lastgang", "gibtsnicht.csv"))
    try:
        tab.calculate_energy_system()
    except Exception as e:
        H.log("CHECK M8", "missing load profile", repr(e)[:200])
    tab.techTab.load_scale_factorInput.setText("abc")
    tab.calculate_energy_system()


def close_with_save():
    """R8: close the application and choose 'Speichern und schließen'."""
    H.MSGBOX_ANSWERS.extend(["Speichern und schließen", None])
    event = QCloseEvent()
    H.VIEW.closeEvent(event)
    H.log("STATE", "close accepted", event.isAccepted())


def save_while_calculating():
    """UT-K4: try to save while a detailed time series runs (one week)."""
    H.MSGBOX_ANSWERS.append("Ohne Speichern")
    H.open_project(ZITTAU, variant="Variante 1")
    tab = H.VIEW.calcTab

    def one_week_detailed(dialog):
        dialog.EndTimeStepInput.setText("168")
        dialog.onAccept()
        return dialog.result()

    H.DIALOG_HANDLERS["TimeSeriesCalculationDialog"] = [one_week_detailed]
    tab.opencalculateNetDialog()
    H.pump(2)
    H.log("STATE", "running calculations", H.VIEW.running_calculations())
    H.log("CHECK K4", "central save during the run", H.VIEW.save_all_project_results())
    tab.saveNet(show_dialog=True)
    H.wait_until(H.thread_finished(tab, "_calc_thread"), 900, "time series (one week)")
    H.log("STATE", "running calculations after the run", H.VIEW.running_calculations())


def read_only_recent_list():
    """K6: the recent-projects file cannot be written (installation under C:\\Program Files)."""
    path = os.path.join(H.WORK, "readonly_recent_projects.json")
    if os.path.exists(path):
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"last_project": "", "recent_projects": []}, f)
    os.chmod(path, stat.S_IREAD)
    H.use_recent_file(path)
    H.VIEW.presenter.folder_manager.config_manager.config_path = path
    H.VIEW.show_welcome_screen()
    H.open_project(ZITTAU, variant="Variante 1")
    H.log("CHECK K6", "folder label", H.VIEW.folderLabel.text() if H.VIEW.folderLabel else None)
    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)


if __name__ == "__main__":
    H.start_app()
    H.run_steps(
        {
            "cancel_open": cancel_open,
            "tree_double_click": tree_double_click,
            "existing_name": existing_name,
            "energy_without_data": energy_without_data,
            "close_with_save": close_with_save,
            "save_while_calculating": save_while_calculating,
            "read_only_recent_list": read_only_recent_list,
        }
    )
