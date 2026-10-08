"""
Scenario P0 – first contact with the bundled Görlitz example
=============================================================

Opens a *copy* of the bundled example (the bundled folder itself is never touched) and takes a
screenshot of every main tab, as a first-time user would look around.

Reproduces (ANWENDERTEST_2026-10-08.md): K6 (example offered from the installation folder),
H2 (CARTO tiles "API KEY REQUIRED"), M3 (network layers loaded three times), M7 (comparison
dashboard empty until "Projekte aktualisieren").

Run: ``python tests/e2e/scenario_p0_example.py``
"""

import os
import shutil

import harness as H

EXAMPLE = os.path.join(H.REPO_ROOT, "src", "districtheatingsim", "project_data", "Görlitz")


def welcome():
    H.shot(H.VIEW, "p0_welcome")
    H.log("STATE", "bundled example offered", H.VIEW.welcome_screen.get_bundled_example_project())


def open_example():
    target = H.fresh_project_slot("Görlitz_Beispiel")
    shutil.copytree(EXAMPLE, target)
    H.open_project(target)
    H.wait_until(lambda: True, 1, "autoload")
    view = H.VIEW
    for index in range(view.tabWidget.count()):
        view.tabWidget.setCurrentIndex(index)
        H.pump(1.5)
        H.shot(view, f"p0_tab{index}")
    H.log("STATE", "map layer list", H.map_layer_names(view.visTab2.view.web_view))


if __name__ == "__main__":
    H.start_app()
    H.run_steps({"welcome": welcome, "open_example": open_example})
