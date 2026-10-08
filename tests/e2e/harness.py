"""
GUI end-to-end harness
======================

Drives the real DistrictHeatingSim main window headless (Qt ``offscreen``) the way a user
would: the scenario scripts call the same slots the buttons and menus trigger. Every popup
the user would see (QMessageBox, QFileDialog, QInputDialog, custom QDialogs) is recorded in
``events.log`` and answered from scripted queues; screenshots go to ``shots/``.

Written for the user test of 2026-10-08 (``ANWENDERTEST_2026-10-08.md``). The scenarios are
reference runs, not pytest tests: they use the live Nominatim/Overpass/OSMnx services and
take minutes to hours.

Output (projects, screenshots, logs, a private recent-projects list) goes to
``$DHS_E2E_WORKDIR`` or, if unset, ``tests/e2e/_work`` (git-ignored). The user's real
recent-projects list and the bundled example project are never touched.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import json
import os
import shutil
import sys
import time
import traceback

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):
        pass

os.environ["QT_QPA_PLATFORM"] = "offscreen"
if sys.platform == "win32":
    # The offscreen platform has no font database of its own.
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from PyQt6 import QtWebEngineWidgets  # noqa: E402, F401 - must be imported before the QApplication exists
from PyQt6.QtCore import QCoreApplication, QEventLoop, QThread  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QInputDialog, QMessageBox  # noqa: E402

from districtheatingsim.gui.MainTab import main_data_manager  # noqa: E402

E2E_DIR = os.path.dirname(os.path.abspath(__file__))
INPUTS = os.path.join(E2E_DIR, "inputs")
REPO_ROOT = os.path.dirname(os.path.dirname(E2E_DIR))
WORK = os.environ.get("DHS_E2E_WORKDIR") or os.path.join(E2E_DIR, "_work")
PROJECTS = os.path.join(WORK, "projects")
SHOTS = os.path.join(WORK, "shots")
EVENTS_FILE = os.path.join(WORK, "events.log")
for _folder in (WORK, PROJECTS, SHOTS):
    os.makedirs(_folder, exist_ok=True)

#: Private recent-projects list; scenarios may point it elsewhere (see ``use_recent_file``).
RECENT_FILE = [os.path.join(WORK, "recent_projects.json")]
main_data_manager.ProjectConfigManager.get_default_config_path = lambda self: RECENT_FILE[0]


def use_recent_file(path):
    """Use another recent-projects file (call before ``start_app``)."""
    RECENT_FILE[0] = path


# ---------------------------------------------------------------- event log
_phase = ["-"]


def log(kind, title="", text=""):
    """Record one user-visible event (also printed)."""
    line = f"[{_phase[0]}] {kind}: {title} :: {str(text).replace(chr(10), ' | ')}"
    print(line, flush=True)
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def phase(name):
    """Start a named phase; it prefixes all following events."""
    _phase[0] = name
    log("PHASE", name)


# ---------------------------------------------------------------- scripted answers
#: Return values of QFileDialog.* in call order; "" means the user cancelled.
FILE_ANSWERS = []
#: (value, ok) tuples for QInputDialog.*; value None takes the dialog's default.
INPUT_ANSWERS = []
#: Answers for message boxes: a button-text fragment for QMessageBox.exec(), a StandardButton
#: for the static question()/warning(), or None for the default (Yes / the default button).
MSGBOX_ANSWERS = []
#: Class name -> list of handlers ``handler(dialog) -> result code or None (= OK)``, used in
#: call order by QDialog.exec(). Dialogs without a handler are rejected (logged).
DIALOG_HANDLERS = {}


def _pop(queue, default):
    return queue.pop(0) if queue else default


def _file_dialog(kind):
    def answer(*args, **kwargs):
        title = args[1] if len(args) > 1 else kwargs.get("caption", "")
        start = args[2] if len(args) > 2 else kwargs.get("directory", "")
        value = _pop(FILE_ANSWERS, "")
        log("FILEDIALOG", f"{kind} '{title}'", f"start={start} -> {value!r}")
        if kind == "getExistingDirectory":
            return value
        if kind == "getOpenFileNames":
            return ([value] if isinstance(value, str) and value else list(value or []), "")
        return (value, "")

    return staticmethod(answer)


for _kind in ("getExistingDirectory", "getOpenFileName", "getSaveFileName", "getOpenFileNames"):
    setattr(QFileDialog, _kind, _file_dialog(_kind))


def _input_dialog(kind):
    def answer(*args, **kwargs):
        title = args[1] if len(args) > 1 else ""
        label = args[2] if len(args) > 2 else ""
        if kind == "getItem":
            default = list(args[3] if len(args) > 3 else kwargs.get("items", []))
        else:
            default = kwargs.get("text", args[3] if len(args) > 3 else None)
        value, ok = _pop(INPUT_ANSWERS, (None, True))
        if value is None:
            value = (default[0] if default else "") if kind == "getItem" else (default if default is not None else "")
        log("INPUTDIALOG", f"{kind} '{title}'", f"label={label!r} default={default!r} -> {value!r}, ok={ok}")
        return (value, ok)

    return staticmethod(answer)


for _kind in ("getText", "getItem", "getInt", "getDouble"):
    setattr(QInputDialog, _kind, _input_dialog(_kind))


def _static_message_box(kind):
    def answer(parent, title, text, *args, **kwargs):
        log(f"MSGBOX.{kind}", title, text)
        if kind not in ("question", "warning"):
            return QMessageBox.StandardButton.Ok
        wanted = _pop(MSGBOX_ANSWERS, None)
        buttons = args[0] if args else kwargs.get("buttons")
        if kind == "warning" and (buttons is None or not (buttons & QMessageBox.StandardButton.Yes)):
            return QMessageBox.StandardButton.Ok
        return wanted if isinstance(wanted, QMessageBox.StandardButton) else QMessageBox.StandardButton.Yes

    return staticmethod(answer)


for _kind in ("information", "warning", "critical", "question", "about"):
    setattr(QMessageBox, _kind, _static_message_box(_kind))


def _message_box_exec(self):
    wanted = _pop(MSGBOX_ANSWERS, None)
    chosen = None
    if isinstance(wanted, str):
        chosen = next((b for b in self.buttons() if wanted.lower() in b.text().lower()), None)
    chosen = chosen or self.defaultButton() or (self.buttons()[0] if self.buttons() else None)
    log(
        "MSGBOX.exec",
        self.windowTitle(),
        f"{self.text()} {self.informativeText()} buttons={[b.text() for b in self.buttons()]} -> "
        f"{chosen.text() if chosen else None}",
    )
    self._e2e_clicked = chosen
    return 0


QMessageBox.exec = _message_box_exec
QMessageBox.clickedButton = lambda self: getattr(self, "_e2e_clicked", None)
QMessageBox.show = lambda self: log("MSGBOX.show", self.windowTitle(), self.text())


def _dialog_exec(self):
    name = type(self).__name__
    handlers = DIALOG_HANDLERS.get(name) or []
    if not handlers:
        log("DIALOG(no handler -> rejected)", name, self.windowTitle())
        return QDialog.DialogCode.Rejected
    handler = handlers.pop(0)
    log("DIALOG", name, self.windowTitle())
    try:
        result = handler(self)
    except Exception:
        log("HARNESS-ERROR", f"handler {name}", traceback.format_exc())
        return QDialog.DialogCode.Rejected
    if result is None:
        result = QDialog.DialogCode.Accepted
    if result == QDialog.DialogCode.Accepted and self.result() != QDialog.DialogCode.Accepted:
        try:
            self.accept()  # the subclass accept() collects the inputs, like the user's OK click
        except Exception:
            log("HARNESS-ERROR", f"accept {name}", traceback.format_exc())
    return result


QDialog.exec = _dialog_exec


def _excepthook(etype, value, tb):
    log("UNCAUGHT-EXCEPTION", etype.__name__, "".join(traceback.format_exception(etype, value, tb))[-3000:])


sys.excepthook = _excepthook


# ---------------------------------------------------------------- helpers
def pump(seconds=0.2):
    """Process Qt events for ``seconds``."""
    end = time.time() + seconds
    while time.time() < end:
        QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        time.sleep(0.01)


def wait_until(condition, timeout=600, label="", poll=0.1):
    """Process events until ``condition()`` is true; return the elapsed seconds or None on timeout."""
    start = time.time()
    while time.time() - start < timeout:
        QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        try:
            if condition():
                elapsed = time.time() - start
                log("WAIT", label, f"done after {elapsed:.1f}s")
                return elapsed
        except Exception:
            pass
        time.sleep(poll)
    log("WAIT-TIMEOUT", label, f"after {timeout}s")
    return None


def thread_finished(owner, attribute):
    """Condition: the QThread stored in ``owner.<attribute>`` exists and is no longer running."""

    def done():
        thread = getattr(owner, attribute, None)
        return isinstance(thread, QThread) and not thread.isRunning()

    return done


def shot(widget, name):
    """Save a screenshot of ``widget`` as ``shots/<name>.png``."""
    path = os.path.join(SHOTS, f"{name}.png")
    pump(0.3)
    try:
        widget.grab().save(path)
        log("SHOT", name, path)
    except Exception as e:
        log("SHOT-FAIL", name, e)
    return path


def find_top(class_name):
    """Return the visible top-level widget of the given class (the non-modal dialogs)."""
    for widget in QApplication.topLevelWidgets():
        if type(widget).__name__ == class_name and widget.isVisible():
            return widget
    return None


def run_js(web_view, script, timeout=10):
    """Run JavaScript in a web view and return its result."""
    result = {}
    web_view.page().runJavaScript(script, lambda value: result.setdefault("value", value))
    wait_until(lambda: "value" in result, timeout, "javascript")
    return result.get("value")


def map_layer_names(web_view):
    """Names in the map's layer list (one entry per loaded layer)."""
    script = "Array.from(document.querySelectorAll('#layerList li.layer-item .layer-name')).map(e => e.textContent)"
    return run_js(web_view, script) or []


def map_fit_all(web_view, osm_tiles=True):
    """Fit the Leaflet map to all layers (optionally on OSM tiles) so a screenshot shows the network."""
    script = """
    (function(){
      if (%s) {
        map.eachLayer(function(l){ if (l instanceof L.TileLayer) map.removeLayer(l); });
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19}).addTo(map);
      }
      var b = window.allLayers.getBounds();
      if (b.isValid()) map.fitBounds(b, {padding: [20, 20]});
      return b.isValid() ? b.toBBoxString() : 'no bounds';
    })();
    """ % ("true" if osm_tiles else "false")
    bounds = run_js(web_view, script)
    pump(6)
    log("MAP", "fit", bounds)
    return bounds


def draw_polygon_on_map(web_view, latlngs):
    """Emulate drawing a capture polygon on the map ([[lat, lon], ...])."""
    script = (
        f"(function(){{var p=L.polygon({json.dumps(latlngs)}); p.addTo(map); "
        "window.capturedPolygonLayer=p; map.fitBounds(p.getBounds()); return 'ok';})();"
    )
    return run_js(web_view, script)


def set_dialog_fields(dialog, fields):
    """Fill the input widgets of a schema-driven technology dialog by field key."""
    for key, value in fields.items():
        widget = None
        for attribute in ("widgets", "inputs", "fields", "_widgets", "input_widgets"):
            mapping = getattr(dialog, attribute, None)
            if isinstance(mapping, dict) and key in mapping:
                widget = mapping[key]
                break
        if widget is None:
            log("HARNESS", "field not found", key)
        elif hasattr(widget, "setText"):
            widget.setText(str(value))
        elif hasattr(widget, "setChecked"):
            widget.setChecked(bool(value))
        elif hasattr(widget, "setCurrentText"):
            widget.setCurrentText(str(value))


def tech_handler(fields=None, screenshot=None):
    """Handler for TechInputDialog: fill ``fields``, optionally screenshot, then OK."""

    def handle(dialog):
        set_dialog_fields(dialog.dialog, fields or {})
        if screenshot:
            shot(dialog, screenshot)

    return handle


def project_path(name):
    """Path of a scenario project in the work folder."""
    return os.path.join(PROJECTS, name)


def fresh_project_slot(name):
    """Delete a previous run's project of this name so the scenario starts from scratch."""
    path = project_path(name)
    if os.path.exists(path):
        shutil.rmtree(path)
    return path


# ---------------------------------------------------------------- application
APP = None
VIEW = None


def start_app(size=(1600, 1000)):
    """Build the main window exactly like ``DistrictHeatingSim.main`` does and show it."""
    global APP, VIEW
    from districtheatingsim.gui.MainTab.main_presenter import HeatSystemPresenter
    from districtheatingsim.gui.MainTab.main_view import HeatSystemDesignGUI
    from districtheatingsim.utilities.logging_setup import configure_logging
    from districtheatingsim.utilities.utilities import get_stylesheet_based_on_time

    configure_logging(log_dir=os.path.join(WORK, "applogs"))
    APP = QApplication.instance() or QApplication(sys.argv)
    APP.setStyle("Fusion")
    start = time.time()
    config_manager = main_data_manager.ProjectConfigManager()
    folder_manager = main_data_manager.ProjectFolderManager(config_manager)
    data_manager = main_data_manager.DataManager()
    VIEW = HeatSystemDesignGUI(folder_manager, data_manager)
    presenter = HeatSystemPresenter(VIEW, folder_manager, data_manager, config_manager)
    VIEW.set_presenter(presenter)
    VIEW.applyTheme(get_stylesheet_based_on_time())
    VIEW.updateTemperatureData()
    VIEW.updateHeatPumpData()
    VIEW.resize(*size)
    VIEW.show()
    pump(0.5)
    log("START", "app started", f"{time.time() - start:.1f}s")
    return VIEW


def new_project(name, parent=PROJECTS):
    """Welcome screen -> 'Neues Projekt erstellen' (parent folder + name dialogs)."""
    FILE_ANSWERS.append(parent)
    INPUT_ANSWERS.append((name, True))
    VIEW.welcome_screen.new_project_clicked()
    pump(2)
    return os.path.join(parent, name)


def open_project(path, variant=None):
    """Welcome screen -> open a project (answers the variant choice if several exist)."""
    if variant:
        INPUT_ANSWERS.append((variant, True))
    VIEW.welcome_screen.projectSelected.emit(path)
    pump(3)


def run_steps(steps, argv=None):
    """
    Run scenario steps in order: all of them, or only those named on the command line.

    :param steps: Ordered ``{name: callable}``; every callable runs inside the one app.
    :param argv: Step names (default ``sys.argv[1:]``).
    """
    names = list(argv if argv is not None else sys.argv[1:]) or list(steps)
    unknown = [n for n in names if n not in steps]
    if unknown:
        raise SystemExit(f"Unknown step(s) {unknown}; available: {list(steps)}")
    for name in names:
        phase(name)
        started = time.time()
        try:
            steps[name]()
        except Exception:
            log("STEP-ERROR", name, traceback.format_exc()[-3000:])
        log("STEP-TIME", name, f"{time.time() - started:.0f}s")
