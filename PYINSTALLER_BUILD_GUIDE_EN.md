# PyInstaller Build Guide - DistrictHeatingSim

Complete guide for creating a standalone Windows executable for DistrictHeatingSim.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Python Environment](#python-environment)
3. [Build Process](#build-process)
4. [Build Configuration](#build-configuration)
5. [Automation](#automation)
6. [Troubleshooting](#troubleshooting)
7. [Distribution](#distribution)
8. [Maintenance & Updates](#maintenance--updates)

---

## Prerequisites

### Software Requirements

- **Python 3.11.9** (IMPORTANT: Not Python 3.12 or Conda base environment!)
- **PyInstaller 6.5.0+** (installed in Python 3.11.9 environment)
- **Windows 10/11** (64-bit)
- **All project dependencies** from `requirements.txt`

### Why Python 3.11.9?

Various libraries currently only work with Python 3.11.

---

## Python Environment

### 1. Check Correct Python Version

```powershell
# Display Python version
python --version
# Should output: Python 3.11.9

# Display Python path
python -c "import sys; print(sys.executable)"
# Should be similar to: C:\Users\<user>\AppData\Local\Programs\Python\Python311\python.exe
```

### 2. Deactivate Conda (if active)

```powershell
# Activate target environment with conda
```

### 3. Install Dependencies

```powershell
# Install all project dependencies
python -m pip install -r requirements.txt

# Install PyInstaller (if not already installed)
python -m pip install pyinstaller>=6.5.0

# Install additional optional dependencies (recommended)
python -m pip install rtree tbb
```

**Optional Dependencies:**
- **rtree** - Enables spatial indexing for geopandas/osmnx operations (required for OSM-based network generation)
- **tbb** - Intel Threading Building Blocks for numba parallel processing (improves performance)

---

## Build Process

### 1. Remove Old Build

```powershell
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
```

### 2. Create Debug Build (with Console)

```powershell
python build_debug.py
```

**What happens during debug build:**
- Uses `DistrictHeatingSim.spec` configuration
- Creates --onedir build (EXE + data folder)
- Enables console window for debugging
- Creates timestamped log file in `build_logs/pyinstaller_build_YYYYMMDD_HHMMSS.log`
- Runs with `--log-level=DEBUG` for detailed output
- Executes post-build cleanup and optimization

### 3. Create Release Build (no Console)

```powershell
python build.py
```

**What happens during release build:**
- Uses `DistrictHeatingSim_Release.spec` configuration
- Creates --onedir build without console window
- Creates timestamped log file in `build_logs/pyinstaller_release_YYYYMMDD_HHMMSS.log`
- Executes post-build cleanup and optimization
- Production-ready executable

### Build Structure (--onedir)

```
dist/
└── DistrictHeatingSim/
    ├── DistrictHeatingSim.exe          # Main program (Entry Point)
    ├── _internal/                       # Python runtime environment (protected)
    │   ├── python311.dll               # Python interpreter
    │   ├── base_library.zip            # Python standard library
    │   ├── geopandas/                  # Geospatial libraries
    │   ├── pandas/                     # Data processing
    │   ├── PyQt6/                      # GUI framework
    │   └── districtheatingsim/         # Application code
    │       ├── gui/                    # GUI modules
    │       │   ├── MainTab/
    │       │   │   ├── file_paths.json         # ✅ Included
    │       │   │   └── recent_projects.json    # ❌ Removed by cleanup
    │       │   └── NetSimulationTab/
    │       │       └── dialog_config.json      # ✅ Included
    │       └── [other modules]
    ├── data/                            # ✅ Moved to root by post-build
    │   ├── TRY files                   # User-editable climate data
    │   └── COP files                   # Heat pump performance data
    ├── project_data/                   # ✅ Moved to root by post-build
    │   └── Görlitz/                    # Example project (188 MB)
    │       ├── Variante 1/
    │       └── Variante 2/
    ├── images/                         # Application images
    ├── leaflet/                        # Leaflet map resources
    ├── gui/                            # GUI configurations
    ├── styles/                         # Stylesheet data
    └── utilities/                      # Utility files
```

**Post-Build Optimization:**
Both build scripts automatically move `data/` and `project_data/` from `_internal/` to the root level, making them easily accessible and editable by users.

### Important Build Parameters

#### --onedir vs --onefile

| Parameter | Advantages | Disadvantages | Recommended for |
|-----------|------------|---------------|-----------------|
| `--onedir` | ✅ Faster startup<br>✅ Large data packages possible<br>✅ Editable files<br>✅ Transparent structure | ❌ Many files<br>❌ Larger folder | **Production** (188 MB project_data) |
| `--onefile` | ✅ Single EXE file<br>✅ Simple distribution | ❌ Slower startup<br>❌ Size limit ~100 MB<br>❌ Temporary extraction | Small tools |

**Our choice: --onedir** due to the 188 MB Görlitz example project.

#### Custom Hooks for Geospatial Stack

```python
# hooks/hook-geopandas.py
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_dynamic_libs

datas, binaries, hiddenimports = collect_all('geopandas')
hiddenimports += collect_submodules('geopandas')
hiddenimports += ['fiona', 'fiona.crs', 'pyproj', 'shapely', 'pandas', 'numpy']
binaries += collect_dynamic_libs('geopandas')
```

Similar hooks exist for:
- `hook-fiona.py` - GDAL/OGR wrapper
- `hook-shapely.py` - GEOS geometry engine
- `hook-pyproj.py` - PROJ coordinate transformation

### Hidden Imports Management

The .spec files include extensive `hiddenimports` lists for dependencies that PyInstaller cannot auto-detect:

**Key hidden imports:**
- **osmnx** - Requires explicit module listing (osmnx 2.x changed structure)
  - ✅ Include: `osmnx.graph`, `osmnx.plot`, `osmnx.utils`, `osmnx.routing`, etc.
  - ❌ Exclude: `osmnx.utils_graph`, `osmnx.speed`, `osmnx.folium` (deprecated in osmnx 2.x)
- **rtree** - Spatial indexing: `rtree`, `rtree.index`
- **scipy** - Scientific computing: Extensive submodule list required
- **pandapipes** - Heat network simulation: `pandapipes.timeseries`

**Expected harmless warnings during build:**
- `WARNING: Hidden import "fiona._shim" not found` - Internal C extension, handled by custom hook
- `WARNING: Hidden import "pyproj._datadir" not found` - Internal C extension, handled by custom hook
- `WARNING: Library not found: tbb12.dll` - Only if `tbb` not installed (numba falls back to single-threaded)

These warnings don't affect functionality as the custom hooks properly bundle the required components.

### Data Bundling

#### Included Data

```python
# Main directories (editable by users)
'--add-data', 'src/districtheatingsim/data;data',
'--add-data', 'src/districtheatingsim/project_data;project_data',
'--add-data', 'src/districtheatingsim/styles;styles',
'--add-data', 'src/districtheatingsim/utilities;utilities',

# GUI configurations (with all subdirectories)
'--add-data', 'src/districtheatingsim/gui;gui',
'--add-data', 'src/districtheatingsim/gui/MainTab;gui/MainTab',
'--add-data', 'src/districtheatingsim/gui/NetSimulationTab;gui/NetSimulationTab',
# ... additional GUI tabs
```

#### Excluded Data (device-specific)

The post-build cleanup function removes:
- `recent_projects.json` - Contains local file paths
- Other device-specific configurations

```python
def cleanup_device_specific_files():
    files_to_remove = [
        'dist/DistrictHeatingSim/gui/MainTab/recent_projects.json',
        'dist/DistrictHeatingSim/_internal/gui/MainTab/recent_projects.json',
        'dist/DistrictHeatingSim/_internal/districtheatingsim/gui/MainTab/recent_projects.json',
    ]
    # ... removal logic
```

---

## Automation

### Batch Files

#### `run_debug.bat` - Debug Build

```batch
@echo off
echo ========================================
echo DistrictHeatingSim - Debug Build
echo ========================================
echo.

REM Deactivate Conda
echo Deactivating Conda environment...
call conda deactivate 2>nul

REM Check Python version
echo.
echo Checking Python version...
python --version
echo.

REM Remove old build
echo Removing old build...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM Start build
echo.
echo Starting PyInstaller debug build...
python build_debug.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Build completed successfully!
    echo ========================================
    echo.
    echo EXE file: dist\DistrictHeatingSim\DistrictHeatingSim.exe
    echo.
) else (
    echo.
    echo ========================================
    echo Build failed! See log file.
    echo ========================================
    echo.
)

pause
```

### Python Build Scripts

#### `build_debug.py` - Debug Build with Console

```python
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def build_with_debug():
    """Build DistrictHeatingSim with full debug logging."""
    
    # Create logs directory
    log_dir = Path('build_logs')
    log_dir.mkdir(exist_ok=True)
    
    # Generate timestamp for log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'pyinstaller_build_{timestamp}.log'
    
    print(f"Starting PyInstaller build with debug logging...")
    print(f"Log file: {log_file}")
    
    # PyInstaller command using .spec file
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        '--log-level=DEBUG',
        'DistrictHeatingSim.spec'  # Debug spec with console
    ]
    
    # Run build process with logging
    # ... (subprocess execution)
    
    return process.returncode

if __name__ == '__main__':
    exit_code = build_with_debug()
    
    if exit_code == 0:
        # Post-build optimization
        cleanup_device_specific_files()  # Remove recent_projects.json
        move_user_data_outside()         # Move data/ and project_data/ to root
    
    sys.exit(exit_code)
```

#### `build.py` - Release Build without Console

```python
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def build_release():
    """Build DistrictHeatingSim for release without console window."""
    
    # Create logs directory
    log_dir = Path('build_logs')
    log_dir.mkdir(exist_ok=True)
    
    # Generate timestamp for log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'pyinstaller_release_{timestamp}.log'
    
    # PyInstaller command using release spec
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'DistrictHeatingSim_Release.spec'  # Release spec without console
    ]
    script (with console) | Root |
| `build.py` | Release build script (no console) | Root |
| `run_debug.bat` | Debug build launcher | Root |
| `DistrictHeatingSim.spec` | Debug build configuration (with console) | Root |
| `DistrictHeatingSim_Release.spec` | Release build configuration (no console) | Root |
| `hooks/hook-*.py` | Custom PyInstaller hooks | `hooks/` |
| `requirements.txt` | Python dependencies | Root |
| `build_logs/` | Timestamped build logs | Auto-created

if __name__ == '__main__':
    exit_code = build_release()
    
    if exit_code == 0:
        # Post-build optimization
        cleanup_device_specific_files()  # Remove recent_projects.json
        move_user_data_outside()         # Move data/ and project_data/ to root
    
    sys.exit(exit_code)
```

#### Post-Build Functions

**1. cleanup_device_specific_files()**
```python
def cleanup_device_specific_files():
    """Remove device-specific configuration files from the build."""
    files_to_remove = [
        'dist/DistrictHeatingSim/gui/MainTab/recent_projects.json',
        'dist/DistrictHeatingSim/_internal/gui/MainTab/recent_projects.json',
        'dist/DistrictHeatingSim/_internal/districtheatingsim/gui/MainTab/recent_projects.json',
    ]
    # Removes files that should be created fresh on each user's machine
```

**2. move_user_data_outside()**
```python
def move_user_data_outside():
    """Move data and project_data folders outside _internal for user accessibility."""
    folders_to_move = [
        'data',           # TRY, COP data files
        'project_data'    # Example projects (Görlitz, etc.)
    ]
    # Moves folders from _internal/ to dist/DistrictHeatingSim/ root
    # Makes them easily accessible and editable by users
```
---

## Troubleshooting

### Common Build Warnings (Harmless)

During the build process, you may see several warnings that can be safely ignored:

#### 1. Missing Hidden Imports
```
WARNING: Hidden import "fiona._shim" not found!
WARNING: Hidden import "pyproj._datadir" not found!
```
**Cause:** These are internal C extensions that don't exist as importable Python modules.  
**Solution:** No action needed - custom hooks handle these correctly.

#### 2. Missing DLL
```
WARNING: Library not found: could not resolve 'tbb12.dll'
```
**Cause:** Intel Threading Building Blocks library not installed.  
**Impact:** Numba falls back to single-threaded mode (slightly slower).  
**Solution:** `pip install tbb` (optional performance improvement)

#### 3. Deprecated osmnx Modules (osmnx 2.x)
```
ERROR: Hidden import 'osmnx.utils_graph' not found
ERROR: Hidden import 'osmnx.speed' not found
ERROR: Hidden import 'osmnx.folium' not found
```
**Cause:** These modules were renamed/removed in osmnx 2.x.  
**Solution:** Already handled - these have been removed from hiddenimports in .spec files.

### Build Failures

#### PyInstaller 6.5.0+ COLLECT Error
```
AttributeError: 'COLLECT' object has no attribute 'datas'
```
**Cause:** PyInstaller 6.5.0+ changed the COLLECT API.  
**Solution:** Already fixed in .spec files - data arrays are combined before COLLECT creation:
```python
# Correct approach (PyInstaller 6.5.0+)
all_datas = datas_inside_internal + datas_outside_internal
coll = COLLECT(exe, a.binaries, all_datas, ...)

# Old approach (PyInstaller <6.5.0) - no longer works
coll = COLLECT(exe, a.binaries, datas_inside_internal, ...)
for item in datas_outside_internal:
    coll.datas.append(item)  # ❌ AttributeError
```

#### Missing rtree Error at Runtime
```
ModuleNotFoundError: No module named 'rtree'
```
**Cause:** rtree not installed or not included in hiddenimports.  
**Solution:** 
1. Install: `pip install rtree`
2. Verify .spec includes: `'rtree', 'rtree.index'` in hiddenimports
3. Rebuild application

### Performance Issues

#### Slow Startup
- **Cause:** Large project_data folder (188 MB Görlitz example)
- **Solution:** Normal for --onedir builds with large data; consider removing example projects for distribution

#### Missing Spatial Operations
- **Symptom:** OSM network generation fails
- **Cause:** rtree not installed
- **Solution:** `pip install rtree` and rebuild

---

## Appendix

### Important Files

| File | Purpose | Location |
|------|---------|----------|
| `build_debug.py` | Debug build configuration | Root |
| `run_debug.bat` | Debug build launcher | Root |
| `hooks/hook-*.py` | Custom PyInstaller hooks | `hooks/` |
| `requirements.txt` | Python dependencies | Root |
| `DistrictHeatingSim.spec` | Generated PyInstaller spec | Root (auto) |

### Useful Links

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [PyInstaller Hooks](https://github.com/pyinstaller/pyinstaller-hooks-contrib)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [osmnx 2.x Migration Guide](https://github.com/gboeing/osmnx)
- [rtree Spatial Indexing](https://github.com/Toblerity/rtree)

### Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.11.9 | Required (not 3.12) |
| PyInstaller | 6.5.0+ | API change in 6.5.0 (COLLECT) |
| osmnx | 2.0.4+ | Module structure changed from 1.x |
| rtree | Latest | Required for spatial indexing |
| tbb | Latest | Optional (numba performance) |

---

January 23, 2026  
**PyInstaller Version:** 6.5.0+  
**Python Version:** 3.11.9  
**Build Architecture:** Windows 64-bit, --onedir

**Build Scripts:**
- `build_debug.py` → Uses `DistrictHeatingSim.spec` (with console)
- `build.py` → Uses `DistrictHeatingSim_Release.spec` (no console)
- Both scripts include automatic logging and post-build optimization
**PyInstaller Version:** 6.16.0  
**Python Version:** 3.11.9  
**Build Architecture:** Windows 64-bit, --onedir
