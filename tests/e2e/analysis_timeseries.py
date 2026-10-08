"""
Analysis H1 – runtime and heat balance of the yearly time series
=================================================================

Loads the net of scenario P1 through the GUI (like a user reopening the project) and runs the
time series functions directly, so no QThread hides the runtime:

- detailed, 1 process, 24 h and 168 h → extrapolated minutes per year,
- detailed, 4 processes, 672 h,
- simplified, 8760 h,

and reports feed-in vs. building heat (network losses) for a winter and a summer window.

Measured 2026-10-08 (15 buildings, 146 pipes): 86–170 min/year sequential, 34 min/year with
4 processes, simplified 0.2 s; losses 22 % (winter) / 57 % (summer) detailed, 49 % per year
simplified – inflated by K1.

Run: ``python tests/e2e/analysis_timeseries.py``
"""

import copy
import multiprocessing
import time

import numpy as np


def run(network_data, start, end, simplified=False, workers=1):
    from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import (
        simplified_time_series_net,
        thermohydraulic_time_series_net,
        time_series_preprocessing,
    )

    data = copy.deepcopy(network_data)
    data.start_time_step, data.end_time_step = start, end
    started = time.time()
    data = time_series_preprocessing(data)
    if simplified:
        data = simplified_time_series_net(data)
    else:
        data = thermohydraulic_time_series_net(data, workers=workers)
    seconds = time.time() - started
    feed_in = sum(np.asarray(p["qext_kW"]) for pumps in data.pump_results.values() for p in pumps.values())
    buildings = np.asarray(data.waerme_ges_kW)[start:end]
    if len(feed_in) > len(buildings):
        feed_in = feed_in[start:end]
    loss = (feed_in.sum() - buildings.sum()) / max(feed_in.sum(), 1e-9) * 100
    return seconds, seconds / (end - start) * 8760 / 60, loss


def main():
    import harness as H

    H.start_app()
    H.open_project(H.project_path("Zittau_Altstadt"), variant="Variante 1")
    network_data = H.VIEW.calcTab.NetworkGenerationData
    cases = [
        ("detailed 1 process, winter", 0, 24, False, 1),
        ("detailed 1 process, week", 0, 168, False, 1),
        ("detailed 1 process, summer", 4300, 4372, False, 1),
        ("detailed 4 processes", 0, 672, False, 4),
        ("simplified, year", 0, 8760, True, 1),
    ]
    for label, start, end, simplified, workers in cases:
        try:
            seconds, per_year, loss = run(network_data, start, end, simplified, workers)
            H.log("BENCH", label, f"{seconds:.1f}s -> {per_year:.1f} min/year; network losses {loss:.1f} %")
        except Exception as e:
            H.log("BENCH-ERROR", label, repr(e)[:300])


if __name__ == "__main__":
    multiprocessing.freeze_support()  # the parallel time series spawns worker processes
    main()
