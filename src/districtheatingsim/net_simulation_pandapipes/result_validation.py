"""
Validation of pandapipes time-series simulation results (GUI-free, numpy-only).
==============================================================================

A non-convergent or infeasible thermohydraulic run leaves NaN/inf in the result
arrays; without a check those silently propagate into the heat/temperature
post-processing. This module surfaces the failure as a clear ``RuntimeError``
instead (BACKLOG C2). Kept dependency-light (numpy only) so it imports and unit-
tests without pulling in pandapipes.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import numpy as np


def validate_simulation_results(net_results: dict, *, context: str = "") -> None:
    """
    Raise ``RuntimeError`` if the simulation produced no / non-finite results.

    :param net_results: Raw result mapping ``{key: ndarray}`` from the time-series
        output writer (``OutputWriter.np_results``).
    :type net_results: dict
    :param context: Optional label included in the error message (e.g. the run mode).
    :type context: str
    :raises RuntimeError: If ``net_results`` is empty, or any numeric result array
        contains NaN/inf — a sign the solver did not converge or the network is
        disconnected/infeasible.
    """
    prefix = f"{context}: " if context else ""

    if not net_results:
        raise RuntimeError(
            f"{prefix}simulation produced no results (empty result set — the network "
            "may be disconnected or the run did not execute)."
        )

    for key, arr in net_results.items():
        values = np.asarray(arr)
        # Only finiteness-check numeric arrays; skip non-numeric / empty ones.
        if values.size == 0 or not np.issubdtype(values.dtype, np.number):
            continue
        if not np.all(np.isfinite(values)):
            raise RuntimeError(
                f"{prefix}simulation result '{key}' contains NaN/inf — the "
                "thermohydraulic solver did not converge (try more iterations or a "
                "different initial state, or check for a disconnected/infeasible network)."
            )


def validate_net_results(net, *, context: str = "") -> None:
    """
    Raise ``RuntimeError`` if a solved net's steady-state results are missing/non-finite.

    Called at network build time (``create_network``): after the design pipeflow +
    diameter sizing the ``res_junction`` table must exist and be finite. An empty or
    NaN/inf result means the pipeflow did not converge (a disconnected or infeasible
    network — e.g. an unreachable consumer) and would otherwise silently poison the
    downstream time series.

    :param net: A solved pandapipes network (duck-typed: needs ``res_junction``).
    :param context: Optional label included in the error message.
    :raises RuntimeError: If there are no junction results, or any are NaN/inf.
    """
    prefix = f"{context}: " if context else ""
    res_junction = getattr(net, "res_junction", None)
    if res_junction is None or len(res_junction) == 0:
        raise RuntimeError(
            f"{prefix}network has no junction results — the design pipeflow did not run "
            "(disconnected or empty network)."
        )
    if not np.all(np.isfinite(np.asarray(res_junction.values, dtype=float))):
        raise RuntimeError(
            f"{prefix}network design results contain NaN/inf — the pipeflow did not "
            "converge (check for a disconnected or infeasible network, e.g. an "
            "unreachable consumer)."
        )


def validate_design_state(design_results: dict, *, context: str = "") -> None:
    """
    Raise ``RuntimeError`` if the extracted producer design-state contains NaN/inf.

    The simplified time series scales this design state (read from ``net.res_*``
    after the initialization pipeflow) by the building demand. A NaN/inf here means
    the network initialization did not converge, which would otherwise silently
    poison every scaled time step.

    :param design_results: Nested mapping ``{producer_type: {idx: {param: value}}}``.
    :type design_results: dict
    :param context: Optional label included in the error message.
    :type context: str
    :raises RuntimeError: If any design-state value is NaN/inf.
    """
    prefix = f"{context}: " if context else ""
    for producer_type, by_index in design_results.items():
        for idx, params in by_index.items():
            for param, value in params.items():
                if not np.isfinite(value):
                    raise RuntimeError(
                        f"{prefix}design-state result '{producer_type}[{idx}].{param}' is "
                        "NaN/inf — the network initialization (design pipeflow) did not converge."
                    )
