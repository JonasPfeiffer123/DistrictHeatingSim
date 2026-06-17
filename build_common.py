"""
Shared helpers for the PyInstaller build scripts (build.py / build_debug.py).

Keeps the PyInstaller invocation, logging and post-build steps in one place so the two
entry scripts only differ in which spec they build and their console messages.
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DIST_ROOT = os.path.join("dist", "DistrictHeatingSim")
_INTERNAL = os.path.join(DIST_ROOT, "_internal")

# Folders that must be reachable/editable by the user → lifted out of _internal post-build.
USER_DATA_FOLDERS = ["data", "project_data", "images", "leaflet"]

# Device-specific config that must be regenerated per machine, never shipped.
DEVICE_SPECIFIC_FILES = [
    os.path.join(DIST_ROOT, "gui", "MainTab", "recent_projects.json"),
    os.path.join(_INTERNAL, "gui", "MainTab", "recent_projects.json"),
    os.path.join(_INTERNAL, "districtheatingsim", "gui", "MainTab", "recent_projects.json"),
]


def configure_utf8_stdout():
    """Force stdout/stderr to UTF-8 so non-ASCII PyInstaller output can't crash a cp1252 console."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (ValueError, OSError):
                pass


def run_pyinstaller(spec_file, log_prefix, extra_args=()):
    """
    Run PyInstaller on *spec_file*, streaming output to the console and a timestamped log.

    :returns: ``(return_code, log_file_path)``.
    """
    log_dir = Path("build_logs")
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{log_prefix}_{timestamp}.log"

    cmd = ["pyinstaller", "--clean", "--noconfirm", *extra_args, spec_file]

    print(f"Starting PyInstaller build: {spec_file}")
    print(f"Log file: {log_file}")

    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Build started: {datetime.now()}\n")
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write("-" * 80 + "\n\n")

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            for line in process.stdout:
                print(line, end="")
                f.write(line)
            process.wait()

            f.write("\n" + "-" * 80 + "\n")
            f.write(f"Build finished: {datetime.now()}\n")
            f.write(f"Return code: {process.returncode}\n")

        return process.returncode, log_file

    except Exception as e:  # noqa: BLE001 - report any launch failure to the console + log
        print(f"\n[FAIL] Build error: {e}")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n\nFATAL ERROR: {e}\n")
        return 1, log_file


def cleanup_device_specific_files():
    """Remove device-specific configuration files (e.g. recent_projects.json) from the build."""
    removed = 0
    for file_path in DEVICE_SPECIFIC_FILES:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"  [OK] Removed: {file_path}")
                removed += 1
            except OSError as e:
                print(f"  [WARN] Could not remove {file_path}: {e}")
    if removed == 0:
        print("  [INFO] No device-specific files found to remove")
    else:
        print(f"  [OK] Cleaned up {removed} device-specific file(s)")


def move_user_data_outside():
    """Move user-editable folders (data/project_data/images/leaflet) out of _internal to the dist root."""
    moved = 0
    for folder in USER_DATA_FOLDERS:
        possible_sources = [
            os.path.join(_INTERNAL, folder),
            os.path.join(_INTERNAL, "districtheatingsim", folder),
        ]
        target = os.path.join(DIST_ROOT, folder)
        for source in possible_sources:
            if os.path.exists(source):
                try:
                    if os.path.exists(target):
                        shutil.rmtree(target)
                    shutil.move(source, target)
                    print(f"  [OK] Moved: {folder}/ from _internal to root")
                    moved += 1
                    break
                except OSError as e:
                    print(f"  [WARN] Could not move {folder}: {e}")
    if moved == 0:
        print("  [INFO] No user-data folders found to move")
    else:
        print(f"  [OK] Moved {moved} user-data folder(s) to root level")


def post_build():
    """Run both post-build steps: drop device-specific files, lift user data out of _internal."""
    print("\nCleaning up device-specific files...")
    cleanup_device_specific_files()
    print("\nMoving user-accessible data out of _internal...")
    move_user_data_outside()
