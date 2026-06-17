"""
Debug build script for DistrictHeatingSim (console window + DEBUG logging).

Builds DistrictHeatingSim.spec with --log-level=DEBUG, then runs the shared post-build
steps (drop device-specific files, lift user data out of _internal). See build_common.py.
"""

import sys

from build_common import DIST_ROOT, configure_utf8_stdout, post_build, run_pyinstaller


def main():
    configure_utf8_stdout()

    return_code, log_file = run_pyinstaller(
        "DistrictHeatingSim.spec", "pyinstaller_build", extra_args=["--log-level=DEBUG"]
    )

    if return_code == 0:
        print("\n[OK] Build successful!")
        print(f"Executable: {DIST_ROOT}/DistrictHeatingSim.exe")
        post_build()
    else:
        print(f"\n[FAIL] Build failed with return code {return_code}")
        print(f"Check log file for details: {log_file}")

    return return_code


if __name__ == "__main__":
    sys.exit(main())
