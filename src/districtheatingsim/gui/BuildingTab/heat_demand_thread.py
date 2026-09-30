"""
Heat Demand Thread Module
=========================

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

Worker thread for the building heat demand calculation. Generating the profiles, formatting
them and writing the (large) building JSON used to run on the UI thread and froze the window
for the whole calculation (BACKLOG G6). The work itself is in ``compute_and_save_heat_demand``,
which touches no widgets and is unit-testable without a ``QThread``.
"""

import json
import traceback
from collections import namedtuple

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from districtheatingsim.gui.utilities import convert_to_serializable
from districtheatingsim.heat_requirement.heat_requirement_calculation_csv import generate_profiles_from_csv
from districtheatingsim.utilities.schema import add_meta

HeatDemandResult = namedtuple(
    "HeatDemandResult",
    ["time_steps", "total_kw", "heating_kw", "warmwater_kw", "max_kw", "supply_temp", "return_temp", "air_temp"],
)

HeatDemandOutcome = namedtuple("HeatDemandOutcome", ["results", "combined_data", "json_path", "save_error"])


def calculate_heat_demand(data: pd.DataFrame, try_filename: str, year: int = 2023) -> HeatDemandResult:
    """
    Calculate heat demand profiles from building data.

    :param data: Building input data
    :type data: pd.DataFrame
    :param try_filename: Climate data filename
    :type try_filename: str
    :param year: Calculation year for profile generation (BDEW/VDI 4655), defaults to 2023
    :type year: int
    :return: Calculated heat demand profiles in kW
    :rtype: HeatDemandResult
    """
    (
        yearly_time_steps,
        total_heat_W,
        heating_heat_W,
        warmwater_heat_W,
        max_heat_requirement_W,
        supply_temperature_curve,
        return_temperature_curve,
        hourly_air_temperatures,
    ) = generate_profiles_from_csv(data=data, TRY=try_filename, calc_method="Datensatz", year=year)

    # Convert from W to kW
    return HeatDemandResult(
        time_steps=yearly_time_steps,
        total_kw=total_heat_W / 1000,
        heating_kw=heating_heat_W / 1000,
        warmwater_kw=warmwater_heat_W / 1000,
        max_kw=max_heat_requirement_W / 1000,
        supply_temp=supply_temperature_curve,
        return_temp=return_temperature_curve,
        air_temp=hourly_air_temperatures,
    )


def format_heat_demand_results(results: HeatDemandResult, data: pd.DataFrame) -> dict:
    """
    Format calculation results for JSON storage.

    :param results: Raw calculation results
    :type results: HeatDemandResult
    :param data: Input building data
    :type data: pd.DataFrame
    :return: Formatted results, keyed by building index as string
    :rtype: dict
    """
    formatted_results = {}
    for idx in range(len(data)):
        building_id = str(idx)
        formatted_results[building_id] = {
            "zeitschritte": [convert_to_serializable(ts) for ts in results.time_steps],
            "außentemperatur": results.air_temp.tolist(),
            "wärme": results.total_kw[idx].tolist(),
            "heizwärme": results.heating_kw[idx].tolist(),
            "warmwasserwärme": results.warmwater_kw[idx].tolist(),
            "max_last": results.max_kw.tolist(),
            "vorlauftemperatur": results.supply_temp[idx].tolist(),
            "rücklauftemperatur": results.return_temp[idx].tolist(),
        }
        for key, value in data.iloc[idx].items():
            formatted_results[building_id][key] = convert_to_serializable(value)
    return formatted_results


def combine_data_with_results(data: pd.DataFrame, results: dict) -> dict:
    """
    Combine input data with calculation results.

    :param data: Input data (not modified)
    :type data: pd.DataFrame
    :param results: Formatted calculation results
    :type results: dict
    :return: Combined data, keyed by building index as string
    :rtype: dict
    """
    data = data.reset_index(drop=True)
    data_dict = data.map(convert_to_serializable).to_dict(orient="index")
    return {str(idx): {**data_dict[idx], **results[str(idx)]} for idx in range(len(data))}


def write_building_json(path: str, combined_data: dict) -> None:
    """
    Write the building results JSON (with the ``_meta`` schema block).

    :param path: Target file
    :type path: str
    :param combined_data: Data to save
    :type combined_data: dict
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(add_meta(combined_data, "building_data"), f, indent=4)


def compute_and_save_heat_demand(data: pd.DataFrame, try_filename: str, year: int, json_path: str) -> HeatDemandOutcome:
    """
    Run the whole heat demand job: profiles → formatted results → combined data → JSON file.

    A failing JSON write does not discard the computed results (the UI still shows them, as
    before the move to a worker thread); it is reported in ``save_error`` instead.

    :param data: Building input data (not modified)
    :type data: pd.DataFrame
    :param try_filename: Climate data filename
    :type try_filename: str
    :param year: Calculation year
    :type year: int
    :param json_path: Where to write the building results JSON
    :type json_path: str
    :return: Results, combined data, the JSON path and the save error message (or ``None``)
    :rtype: HeatDemandOutcome
    """
    data = data.reset_index(drop=True)
    results = format_heat_demand_results(calculate_heat_demand(data, try_filename, year), data)
    combined_data = combine_data_with_results(data, results)
    try:
        write_building_json(json_path, combined_data)
        save_error = None
    except Exception as e:
        save_error = f"Fehler beim Speichern der Ergebnisse: {e}"
    return HeatDemandOutcome(results, combined_data, json_path, save_error)


class HeatDemandThread(QThread):
    """
    Thread for the building heat demand calculation.

    :signal calculation_done: Emitted with a ``HeatDemandOutcome`` when the calculation is done.
    :signal calculation_error: Emitted with the formatted message when the calculation fails.
    """

    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, data: pd.DataFrame, try_filename: str, year: int, json_path: str):
        """
        Initialize the HeatDemandThread.

        :param data: Building input data (copied, so the UI can keep editing its table)
        :type data: pd.DataFrame
        :param try_filename: Climate data filename
        :type try_filename: str
        :param year: Calculation year
        :type year: int
        :param json_path: Where to write the building results JSON
        :type json_path: str
        """
        super().__init__()
        self.data = data.copy()
        self.try_filename = try_filename
        self.year = year
        self.json_path = json_path

    def run(self):
        """Run the heat demand calculation."""
        try:
            outcome = compute_and_save_heat_demand(self.data, self.try_filename, self.year, self.json_path)
            self.calculation_done.emit(outcome)
        except Exception as e:
            tb = traceback.format_exc()
            self.calculation_error.emit(f"Es ist ein Fehler aufgetreten: {e}\n\nDetails:\n{tb}")

    def stop(self):
        """
        Request the thread to stop and block until it has finished.

        The profile generation is not cooperatively interruptible, so this waits for the
        current run (consistent with the other worker threads).
        """
        if self.isRunning():
            self.requestInterruption()
            self.wait()
