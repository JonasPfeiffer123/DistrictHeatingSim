"""
Guards that the GUI-free domain core stays free of PyQt6 (BACKLOG B5).

`energy_system.save_to_json` uses `CustomJSONEncoder`, which used to live in the GUI
package and dragged PyQt6 into the domain core — breaking headless CI at import time
(`libEGL.so.1`). The encoder now lives in `heat_generators/json_encoder.py`.

The import-isolation check runs in a *subprocess* so it is unaffected by other tests
in the session having already imported PyQt6.
"""

import subprocess
import sys

from districtheatingsim.heat_generators.json_encoder import CustomJSONEncoder


def test_encoder_importable_from_domain_core():
    assert CustomJSONEncoder is not None


def test_domain_core_imports_without_pyqt6():
    code = (
        "import sys; "
        "import districtheatingsim.heat_generators.energy_system; "
        "sys.exit(1 if 'PyQt6' in sys.modules else 0)"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, (
        "Importing the domain core pulled in PyQt6 — a GUI dependency leaked back in.\n"
        f"stderr:\n{result.stderr}"
    )
