# -*- mode: python ; coding: utf-8 -*-
#
# RELEASE build spec: no console window, no debug symbols. Driven by build.py.
# Shared Analysis config lives in spec_common.py; this file only sets the debug/console
# EXE flags. The debug spec (DistrictHeatingSim.spec) is identical except for those flags.

import sys

sys.setrecursionlimit(sys.getrecursionlimit() * 5)
sys.path.insert(0, SPECPATH)  # noqa: F821 - SPECPATH is injected by PyInstaller

from spec_common import ENTRY_SCRIPT, EXCLUDES, HIDDENIMPORTS, get_datas

a = Analysis(
    [ENTRY_SCRIPT],
    pathex=[],
    binaries=[],
    datas=get_datas(),
    hiddenimports=HIDDENIMPORTS,
    hookspath=["hooks"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=True,
)
pyz = PYZ(a.pure)

# upx=False on purpose: UPX-packed binaries frequently trigger Windows Defender / AV
# false positives on a distributed exe (and UPX isn't installed in the build env anyway).
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="DistrictHeatingSim",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# onedir COLLECT. Everything lands in _internal/; build_common.move_user_data_outside()
# lifts the user-editable folders (data/project_data/images/leaflet) to the root afterwards.
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DistrictHeatingSim",
)
