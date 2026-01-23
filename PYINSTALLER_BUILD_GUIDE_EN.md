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
```

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
