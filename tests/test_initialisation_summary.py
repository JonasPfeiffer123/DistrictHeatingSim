"""
Pump design after the net initialisation (user test 2026-10-08, UT-M12).

The bad-point controller raised the given pump lift of 1.5 bar to 3.3 bar without a word; the
velocity limit of the diameter sizing applies to the house connections too. The summary says both.
"""

from types import SimpleNamespace

import pandas as pd
import pytest

from districtheatingsim.net_simulation_pandapipes.controllers import BadPointPressureLiftController
from districtheatingsim.net_simulation_pandapipes.utilities import initialisation_summary


def _net(lift=3.3, target=1.0):
    controller = BadPointPressureLiftController.__new__(BadPointPressureLiftController)
    controller.target_dp_min_bar = target
    return SimpleNamespace(
        circ_pump_pressure=pd.DataFrame({"plift_bar": [lift]}),
        controller=pd.DataFrame({"object": [controller]}),
        heat_consumer=pd.DataFrame({"qext_w": [50000.0, 0.0, 20000.0]}),
        res_heat_consumer=pd.DataFrame({"p_from_bar": [5.0, 5.0, 4.6], "p_to_bar": [3.5, 4.9, 3.55]}),
        res_pipe=pd.DataFrame({"v_mean_m_per_s": [0.4, -0.97, 0.2]}),
    )


def test_raised_lift_is_explained():
    assert initialisation_summary(_net(), 1.5, 1.0) == (
        "Pumpe: Förderhöhe 3,30 bar (vorgegeben 1,50 bar).\n"
        "Die Differenzdruckregelung im Schlechtpunkt hat sie angepasst, damit am ungünstigsten Hausanschluss "
        "mindestens 1,0 bar anliegen (jetzt 1,05 bar).\n"
        "Höchste Strömungsgeschwindigkeit: 0,97 m/s (Grenze der Durchmesserauslegung 1,0 m/s, gilt für alle Leitungen)."
    )


def test_unchanged_lift_and_no_sizing():
    text = initialisation_summary(_net(lift=1.5), 1.5, None)
    assert text.splitlines()[0] == "Pumpe: Förderhöhe 1,50 bar."
    assert "hält sie" in text and "Grenze" not in text


def test_net_without_pump():
    net = SimpleNamespace(res_pipe=pd.DataFrame({"v_mean_m_per_s": [0.5]}))
    assert initialisation_summary(net, 1.5) == "Höchste Strömungsgeschwindigkeit: 0,50 m/s."


def test_controller_follows_the_current_worst_point():
    """The worst point is re-determined on every iteration, not kept from before the sizing."""
    from districtheatingsim.net_simulation_pandapipes.controllers import DEFAULT_PUMP_CONTROLLER_GAIN

    net = SimpleNamespace(
        heat_consumer=pd.DataFrame({"qext_w": [30000.0, 25000.0]}),
        res_heat_consumer=pd.DataFrame({"p_from_bar": [5.0, 3.5], "p_to_bar": [3.9, 4.5]}),
        circ_pump_pressure=pd.DataFrame({"plift_bar": [3.2], "p_flow_bar": [5.7]}),
    )
    controller = BadPointPressureLiftController.__new__(BadPointPressureLiftController)
    controller.circ_pump_pressure_idx = 0
    controller.target_dp_min_bar = 1.0
    controller.tolerance = 0.2
    controller.proportional_gain = DEFAULT_PUMP_CONTROLLER_GAIN
    controller.iteration = 0
    controller.heat_consumer_idx = 0  # the worst point before the diameter sizing: 1.1 bar, "converged"

    assert controller.is_converged(net) is False  # station 1 has -1.0 bar
    assert controller.heat_consumer_idx == 1
    controller.control_step(net)
    expected = 3.2 + (1.0 - (-1.0)) * DEFAULT_PUMP_CONTROLLER_GAIN
    assert net.circ_pump_pressure.at[0, "plift_bar"] == pytest.approx(expected)
