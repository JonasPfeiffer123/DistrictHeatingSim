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

### 2. Create Debug Build

```powershell
python build_debug.py
```

**What happens during debug build:**
- Creates --onedir build (EXE + data folder)
- Enables console output for debugging
- Adds debug logging
- Retains all symbols for debugging

### Build Structure (--onedir)

```
dist/
└── DistrictHeatingSim/
    ├── DistrictHeatingSim.exe          # Main program (Entry Point)
    ├── _internal/                       # Python runtime environment (protected)
    │   ├── python312.dll               # Python interpreter
    │   ├── base_library.zip            # Python standard library
    │   ├── geopandas/                  # Geospatial libraries
    │   ├── pandas/                     # Data processing
    │   ├── PyQt6/                      # GUI framework
    │   └── districtheatingsim/         # Application code
    │       ├── gui/                    # GUI modules
    │       │   ├── MainTab/
    │       │   │   ├── file_paths.json         # ✅ Included
    │       │   │   └── recent_projects.json    # ❌ Removed (device-specific)
    │       │   └── NetSimulationTab/
    │       │       └── dialog_config.json      # ✅ Included
    │       └── [other modules]
    ├── data/                            # Editable data (TRY, COP)
    ├── project_data/                   # Example projects (188 MB)
    │   └── Görlitz/                    # Görlitz example project
    │       ├── Variante 1/
    │       └── Variante 2/
    ├── gui/                            # GUI configurations
    ├── styles/                         # Stylesheet data
    └── utilities/                      # Utility files
```

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

#### `build_debug.py` - Main Configuration

```python
import PyInstaller.__main__
import os
import sys
from datetime import datetime

def cleanup_device_specific_files():
    """Remove device-specific files after build"""
    files_to_remove = [
        'dist/DistrictHeatingSim/gui/MainTab/recent_projects.json',
        'dist/DistrictHeatingSim/_internal/gui/MainTab/recent_projects.json',
        'dist/DistrictHeatingSim/_internal/districtheatingsim/gui/MainTab/recent_projects.json',
    ]
    
    removed_count = 0
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"  ✓ Removed: {file_path}")
                removed_count += 1
            except Exception as e:
                print(f"  ✗ Failed to remove {file_path}: {e}")
    
    if removed_count > 0:
        print(f"\n✓ Cleanup completed: {removed_count} file(s) removed")
    else:
        print("\n  No device-specific files found to remove")

# Main configuration for debug build
PyInstaller.__main__.run([
    '--onedir',              # Directory mode (for large data)
    '--windowed',            # GUI application
    '--console',             # DEBUG: Console for debugging
    '--name', 'DistrictHeatingSim',
    '--icon', 'images/icon.ico',
    
    # Debug options
    '--debug=all',
    '--log-level=DEBUG',
    
    # Data bundling
    '--add-data', 'src/districtheatingsim/data;data',
    '--add-data', 'src/districtheatingsim/project_data;project_data',
    # ... additional data
    
    # Custom hooks
    '--additional-hooks-dir=hooks',
    
    # Hidden imports
    '--hidden-import=geopandas',
    '--hidden-import=fiona',
    # ... additional imports
    
    'src/districtheatingsim/DistrictHeatingSim.py'
])

# Post-Build Cleanup
print("\n" + "="*70)
print("Post-Build Cleanup: Removing device-specific files...")
print("="*70)
cleanup_device_specific_files()
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

---

**Last Updated:** October 21, 2025  
**PyInstaller Version:** 6.16.0  
**Python Version:** 3.11.9  
**Build Architecture:** Windows 64-bit, --onedir
