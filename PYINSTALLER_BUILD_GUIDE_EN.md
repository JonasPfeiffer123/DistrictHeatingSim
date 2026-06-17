# PyInstaller Build Guide — DistrictHeatingSim

How to create the standalone Windows executable for DistrictHeatingSim.

DistrictHeatingSim is **not published on PyPI** (two dependencies are pulled from
GitHub). The PyInstaller `--onedir` build is the primary distribution artifact for
end users.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Build Layout](#build-layout)
3. [Build Process](#build-process)
4. [What Gets Bundled](#what-gets-bundled)
5. [Output Structure](#output-structure)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

---

## Prerequisites

- **Python 3.11.9** — required (several scientific dependencies do not yet support 3.12;
  do **not** build from a Conda base environment).
- **PyInstaller 6.5.0+** installed in that Python 3.11 environment.
- **Windows 10/11 (64-bit).**
- All project dependencies installed (`pip install .`), including the two GitHub
  dependencies `pyslpheat` and `thermal-energy-storage-1d` (require `git`).

```powershell
python --version                      # -> Python 3.11.9
python -c "import sys; print(sys.executable)"

pip install .                         # all runtime deps from pyproject.toml
python -m pip install "pyinstaller>=6.5.0"
python -m pip install rtree tbb       # optional: spatial indexing + numba threading
```

- **rtree** — spatial indexing for geopandas/osmnx (OSM-based network generation).
- **tbb** — Intel Threading Building Blocks for numba (performance only; without it
  numba falls back to single-threaded).

---

## Build Layout

The build is driven by four small files at the repository root plus a shared module:

| File | Role |
|------|------|
| `spec_common.py` | **Single source of truth** for `datas` / `hiddenimports` / excludes (imported by both specs) |
| `DistrictHeatingSim.spec` | Debug spec — `console=True`, `debug=True` |
| `DistrictHeatingSim_Release.spec` | Release spec — `console=False`, `debug=False` |
| `build_common.py` | Shared PyInstaller invocation, logging, and post-build steps |
| `build_debug.py` | Thin entry point → builds the debug spec with `--log-level=DEBUG` |
| `build.py` | Thin entry point → builds the release spec |
| `run_debug.bat` | **Runs the already-built exe** with stderr capture + exit code (for diagnosing crashes) |
| `hooks/hook-*.py` | Custom PyInstaller hooks for the geospatial stack (fiona, geopandas, pyproj, shapely) |

The two specs are identical except for the `console`/`debug` flags — everything else
lives in `spec_common.py`, so there is only one `datas`/`hiddenimports` list to maintain.

---

## Build Process

```powershell
# 1. Clean previous output (optional; --clean in the scripts also clears PyInstaller caches)
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

# 2. Debug build (console window + DEBUG logging) — use this to diagnose problems
python build_debug.py

# 3. Release build (no console window) — the distributable
python build.py
```

Both scripts:
- create a timestamped log under `build_logs/` (`pyinstaller_build_*.log` /
  `pyinstaller_release_*.log`),
- reconfigure stdout to UTF-8 so non-ASCII build output never crashes a cp1252 console,
- after a successful build run the post-build steps in `build_common.post_build()`:
  - **`cleanup_device_specific_files()`** — removes `recent_projects.json` (per-machine state),
  - **`move_user_data_outside()`** — lifts `data/`, `project_data/`, `images/`, `leaflet/`
    out of `_internal/` to the dist root so users can find and edit them.

### Running / diagnosing the built exe

```powershell
# Launch the built exe and keep the window open with the exit code (handy for crashes):
run_debug.bat
# or directly:
dist\DistrictHeatingSim\DistrictHeatingSim.exe
```

### --onedir (not --onefile)

We build `--onedir`: faster startup, the bundled example `project_data/` (the ~55 MB
Görlitz project) stays editable, and the structure is transparent. `--onefile` is
unsuitable here (slow startup, temp extraction, awkward with large bundled data).

---

## What Gets Bundled

`spec_common.get_datas()` assembles the `datas` list at build time:

- **App resource folders** (`data`, `images`, `leaflet`, `gui/**`, `styles`,
  `project_data`, …) copied whole — new modules added inside them are picked up
  automatically.
- **`file_paths.json`** in the several locations the app may look for it.
- **pandapipes std-types + properties** resolved dynamically from the installed
  pandapipes (`std_types/library` carries the **ISOPLUS** catalog the 0.14 net model
  needs) — no hardcoded site-packages path.
- **osmnx metadata** via `copy_metadata('osmnx')` (osmnx checks its own version).
- **`pyslpheat` and `thermal_energy_storage_model` data** via `collect_data_files(...)`.
  This is essential: these GitHub dependencies ship non-`.py` data (pyslpheat's BDEW/VDI
  profile CSVs, TRY files, images) that PyInstaller's import-following does **not** collect
  on its own. Without this the frozen exe's heat-demand calculation fails at runtime.

`spec_common.HIDDENIMPORTS` lists imports PyInstaller's static analysis cannot find
(osmnx 2.x submodules, scipy C-extension submodules, rtree, CoolProp, the Qt-Agg
matplotlib backend, …). `EXCLUDES` drops `PyQt5` / `PySide2` / `PySide6` / `tkinter`.

The geospatial stack is further covered by `hooks/hook-{fiona,geopandas,pyproj,shapely}.py`.

---

## Output Structure

```
dist/
└── DistrictHeatingSim/
    ├── DistrictHeatingSim.exe          # entry point
    ├── _internal/                       # Python runtime + libraries + app code
    │   ├── python311.dll, base_library.zip, PyQt6/, pandas/, geopandas/ …
    │   └── districtheatingsim/          # application code + config JSONs
    ├── data/                            # ← moved out of _internal (user-editable)
    ├── project_data/                    # ← moved out (≈55 MB Görlitz example)
    ├── images/                          # ← moved out
    └── leaflet/                         # ← moved out
```

`recent_projects.json` is removed post-build (it holds machine-local paths).

---

## Troubleshooting

**Harmless build warnings:**
- `Hidden import "fiona._shim"/"pyproj._datadir" not found` — internal C extensions,
  handled by the custom hooks.
- `Library not found: tbb12.dll` — only if `tbb` isn't installed; numba falls back to
  single-threaded.

**Runtime: heat-demand calculation fails / missing BDEW/VDI/TRY files** — `pyslpheat`
data was not bundled. Confirm `spec_common.get_datas()` still calls
`collect_data_files('pyslpheat')` and rebuild.

**Runtime: `ModuleNotFoundError: rtree`** — install `rtree` and rebuild (it's in
`HIDDENIMPORTS`, but the package must be present in the build environment).

**`AttributeError: 'COLLECT' object has no attribute 'datas'`** — a pre-6.5 pattern;
the specs already pass all datas into `COLLECT(...)` directly, which is correct for 6.5+.

**Slow startup** — normal for `--onedir` with the bundled ~55 MB example project; remove
`project_data/` from the dist if a leaner package is wanted.

---

## Maintenance

- **Adding a dependency with its own data files** (like pyslpheat): add a
  `collect_data_files('<pkg>')` line in `spec_common.get_datas()`.
- **A dependency PyInstaller can't auto-detect**: add it to `spec_common.HIDDENIMPORTS`.
- **New app resource folder**: add it to `spec_common._APP_DATA_DIRS`. Existing whole-dir
  copies already pick up new *modules* inside bundled packages.
- Keep changes in `spec_common.py` / `build_common.py` — never edit the per-spec or
  per-script files for shared config.

---

**Last updated:** 2026-06-17 · **PyInstaller:** 6.5.0 · **Python:** 3.11.9 ·
**Architecture:** Windows 64-bit, `--onedir` · **pandapipes:** 0.14
