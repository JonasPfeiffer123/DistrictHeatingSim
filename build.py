"""
Release build script for DistrictHeatingSim (no console window).

Builds DistrictHeatingSim_Release.spec, then runs the shared post-build steps
(drop device-specific files, lift user data out of _internal). See build_common.py.
"""

import sys

from build_common import DIST_ROOT, configure_utf8_stdout, post_build, run_pyinstaller


def main():
    configure_utf8_stdout()

    print("=" * 70)
    print("RELEASE BUILD - No Console Window")
    print("=" * 70)
    print()

    return_code, log_file = run_pyinstaller("DistrictHeatingSim_Release.spec", "pyinstaller_release")

    if return_code == 0:
        exe_path = f"{DIST_ROOT}/DistrictHeatingSim.exe"
        print("\n[OK] Release build successful!")
        print(f"Executable: {exe_path}")
        post_build()
        print("\n" + "=" * 70)
        print("[OK] RELEASE BUILD COMPLETE")
        print("=" * 70)
        print(f"The application is ready for distribution: {DIST_ROOT}/")
    else:
        print(f"\n[FAIL] Build failed with return code {return_code}")
        print(f"Check log file for details: {log_file}")

    return return_code


if __name__ == "__main__":
    sys.exit(main())
