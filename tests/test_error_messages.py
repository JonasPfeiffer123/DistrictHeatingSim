"""
German messages for failed calculations and the guards around them (UT-M1, UT-M8, UT-M9).

UT-M1: the worker threads showed raw, often English tracebacks.
UT-M8: the time series could be started after a failed initialisation; a missing load profile in
the generator tab ended in an unhandled FileNotFoundError.
UT-M9: "Ergebnisse als CSV exportieren…" opened no dialog and always wrote
``calculated_heat_generation.csv``, whatever the config.
"""

import logging
import os
from types import SimpleNamespace

import pytest
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from districtheatingsim.utilities.error_messages import describe_error, report_error
from districtheatingsim.utilities.web_services import ServiceUnavailableError


class PipeflowNotConverged(Exception):
    """Stands in for pandapipes' exception of the same name."""


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (FileNotFoundError(2, "No such file", "Lastgang.csv"), "Die Datei gibt es nicht:\nLastgang.csv"),
        (PermissionError(13, "Permission denied", "Quartier IST.csv"), "Excel"),
        (PipeflowNotConverged("The hydraulic calculation did not converge"), "Konnektivität prüfen"),
        (TypeError("unsupported operand type(s) for *: 'float' and 'NoneType'"), "Ein benötigter Wert fehlt"),
        (KeyError("Wärmebedarf"), "Es fehlt der Eintrag 'Wärmebedarf'."),
        (ServiceUnavailableError("Der Adressdienst antwortet nicht."), "Der Adressdienst antwortet nicht."),
        (ValueError("Die Gebäudeliste mischt VDI-4655-Typen"), "Die Gebäudeliste mischt VDI-4655-Typen"),
        (ZeroDivisionError("division by zero"), "ZeroDivisionError: division by zero"),
    ],
)
def test_messages(exc, expected):
    message = describe_error(exc, "Die Netzinitialisierung", log_file="C:/logs/districtheatingsim.log")
    assert message.startswith("Die Netzinitialisierung ist fehlgeschlagen.\n\n")
    assert expected in message
    assert message.endswith("Technische Details stehen in der Logdatei:\nC:/logs/districtheatingsim.log")
    assert "Traceback" not in message


def test_traceback_goes_to_the_log(caplog):
    error = ValueError("kaputt")
    try:
        raise error
    except ValueError as e:
        with caplog.at_level(logging.ERROR, logger="districtheatingsim"):
            message = report_error(e, "Die Berechnung des Erzeugermix")
    assert message.startswith("Die Berechnung des Erzeugermix ist fehlgeschlagen.")
    (record,) = [r for r in caplog.records if r.name == "districtheatingsim.utilities.error_messages"]
    assert record.exc_info and record.exc_info[1] is error and record.exc_info[2] is not None


def test_domain_messages_are_german():
    from districtheatingsim.heat_requirement.heat_requirement_calculation_csv import resolve_calculation_method

    with pytest.raises(ValueError, match="„nan“ = Gebäudetyp nicht ausgefüllt"):
        resolve_calculation_method(["EFH", "nan"], "Datensatz")


class TestTimeSeriesGuard:
    @pytest.mark.parametrize("network_data", [None, SimpleNamespace()])
    def test_no_time_series_without_an_initialised_net(self, qapp, monkeypatch, network_data):
        from districtheatingsim.gui.NetSimulationTab import net_simulation_tab

        shown = []
        monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(a[1])))
        monkeypatch.setattr(net_simulation_tab, "TimeSeriesCalculationDialog", lambda *a: pytest.fail("opened"))
        tab = SimpleNamespace(NetworkGenerationData=network_data, _net_ready=False, base_path="")
        net_simulation_tab.NetSimulationTab.opencalculateNetDialog(tab)
        assert shown == ["Kein initialisiertes Netz"]


class TestEnergySystem:
    def _tab(self, tmp_path, error):
        def preprocess():
            raise error

        return SimpleNamespace(
            optimize=False,
            calculationThread=None,
            validateInputs=lambda: True,
            techTab=SimpleNamespace(
                tech_objects=["Gaskessel"], FilenameInput=SimpleNamespace(text=lambda: str(tmp_path / "Lastgang.csv"))
            ),
            preprocessData=preprocess,
        )

    def test_missing_load_profile(self, qapp, tmp_path, monkeypatch):
        from districtheatingsim.gui.EnergySystemTab._01_energy_system_main_tab import EnergySystemTab

        shown = []
        monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: shown.append(a[1:])))
        missing = FileNotFoundError(2, "No such file", str(tmp_path / "Lastgang.csv"))
        EnergySystemTab.calculate_energy_system(self._tab(tmp_path, missing))
        ((title, text),) = shown
        assert title == "Lastgang fehlt" and "Zeitreihe" in text

    def test_other_errors_are_reported(self, qapp, tmp_path, monkeypatch):
        from districtheatingsim.gui.EnergySystemTab._01_energy_system_main_tab import EnergySystemTab

        shown = []
        monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: shown.append(a[2])))
        EnergySystemTab.calculate_energy_system(self._tab(tmp_path, ZeroDivisionError("division by zero")))
        assert shown and shown[0].startswith("Das Vorbereiten der Berechnung ist fehlgeschlagen.")

    @pytest.mark.parametrize(
        ("config", "default_name"),
        [("Standard", "calculated_heat_generation.csv"), ("Solar/Bio", "calculated_heat_generation_Solar-Bio.csv")],
    )
    def test_csv_export_asks_where(self, qapp, tmp_path, monkeypatch, config, default_name):
        from districtheatingsim.gui.EnergySystemTab._01_energy_system_main_tab import EnergySystemTab

        offered, written = [], []
        target = str(tmp_path / "Export" / "meine.csv")
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: offered.append(a[2]) or (target, ""))
        )
        monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
        tab = SimpleNamespace(
            energy_system=SimpleNamespace(results={"x": 1}, save_to_csv=written.append),
            base_path=str(tmp_path),
            config_manager=SimpleNamespace(
                get_relative_path=lambda key: os.path.join("Ergebnisse", "calculated_heat_generation.csv")
            ),
            _active_config_name=config,
        )
        EnergySystemTab.save_heat_generation_results_to_csv(tab)
        assert os.path.basename(offered[0]) == default_name
        assert written == [target]

    def test_cancelled_export_writes_nothing(self, qapp, tmp_path, monkeypatch):
        from districtheatingsim.gui.EnergySystemTab._01_energy_system_main_tab import EnergySystemTab

        written = []
        monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))
        tab = SimpleNamespace(
            energy_system=SimpleNamespace(results={"x": 1}, save_to_csv=written.append),
            base_path=str(tmp_path),
            config_manager=SimpleNamespace(get_relative_path=lambda key: "Ergebnisse/calculated_heat_generation.csv"),
            _active_config_name="Standard",
        )
        EnergySystemTab.save_heat_generation_results_to_csv(tab)
        assert written == []


@pytest.mark.parametrize(("text", "valid", "stored"), [("abc", False, "abc"), ("0", False, "0"), ("1,1", True, "1.1")])
def test_scale_factor_message(qapp, monkeypatch, text, valid, stored):
    from PyQt6.QtWidgets import QLineEdit

    from districtheatingsim.gui.EnergySystemTab._01_energy_system_main_tab import EnergySystemTab

    shown = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: shown.append(a[2])))
    field = QLineEdit(text)
    tab = SimpleNamespace(techTab=SimpleNamespace(load_scale_factorInput=field))
    assert EnergySystemTab.validateInputs(tab) is valid
    assert field.text() == stored
    if not valid:
        assert shown == [f"Der Lastgang-Skalierungsfaktor „{text}“ ist keine Zahl größer als 0 (z. B. 1 oder 1,1)."]
