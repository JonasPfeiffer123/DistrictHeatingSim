"""
Analysis K1 – pipe heat losses after the diameter sizing
=========================================================

Loads the initialised net of scenario P1 (``Zittau_Altstadt/Variante 1``), counts the pipes
whose ``outer_diameter_mm`` does not match their std-type and compares the design-state pipe
losses as stored with the losses after setting every outer diameter from the std-type library.
pandapipes computes the loss area with the outer diameter (``alpha * pi * DO``), so a stale
outer diameter scales the losses of every resized pipe.

Before the fix (2026-10-08): 130 of 146 pipes stale, pipe losses 126.2 kW → 53.6 kW.
After the fix both numbers must agree.

Run: ``python tests/e2e/analysis_net_losses.py [variant folder]``
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandapipes as pp  # noqa: E402
import pandas as pd  # noqa: E402

from districtheatingsim.net_simulation_pandapipes.net_io import load_net  # noqa: E402

E2E_DIR = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("DHS_E2E_WORKDIR") or os.path.join(E2E_DIR, "_work")
CP_WATER = 4186.0


def pipe_losses_kw(net):
    """Design-state heat loss of all pipes from the pipe temperatures and mass flows [kW]."""
    pp.pipeflow(net, mode="bidirectional", iter=100)
    res = net.res_pipe
    return float(((res.t_from_k - res.t_to_k) * res.mdot_from_kg_per_s.abs() * CP_WATER).sum()) / 1000


def main(variant_folder):
    net, _ = load_net(os.path.join(variant_folder, "Wärmenetz", "Ergebnisse Netzinitialisierung.json"))
    library = net.std_types["pipe"]
    library = library if isinstance(library, pd.DataFrame) else pd.DataFrame(library).T
    expected = net.pipe.std_type.map(library["outer_diameter_mm"]).astype(float)
    stale = int(((expected - net.pipe.outer_diameter_mm).abs() > 0.01).sum())
    as_stored = pipe_losses_kw(net)
    net.pipe["outer_diameter_mm"] = expected
    corrected = pipe_losses_kw(net)
    print(f"pipes with a stale outer diameter: {stale} of {len(net.pipe)}")
    print(f"pipe losses as stored:  {as_stored:7.1f} kW")
    print(f"pipe losses corrected:  {corrected:7.1f} kW  (factor {as_stored / corrected:.2f})")
    print(f"pipe length: {net.pipe.length_km.sum() * 1000:.0f} m (flow + return)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "projects", "Zittau_Altstadt", "Variante 1"))
