# filepath: build_debug.py
"""
Debug build script for DistrictHeatingSim with comprehensive logging.
"""
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
    
    # PyInstaller command with full debug
    cmd = [
        'pyinstaller',
        '--onedir',  # Changed from --onefile to support large data files
        '--windowed',
        '--name', 'DistrictHeatingSim',
        # Add all data directories from src/districtheatingsim
        '--add-data', 'src/districtheatingsim/data;data',
        '--add-data', 'src/districtheatingsim/leaflet;leaflet',
        '--add-data', 'src/districtheatingsim/geocoding;geocoding',
        '--add-data', 'src/districtheatingsim/gui;gui',
        # Add gui subdirectories explicitly to ensure all config files are included
        '--add-data', 'src/districtheatingsim/gui/MainTab;gui/MainTab',
        '--add-data', 'src/districtheatingsim/gui/NetSimulationTab;gui/NetSimulationTab',
        '--add-data', 'src/districtheatingsim/gui/BuildingTab;gui/BuildingTab',
        '--add-data', 'src/districtheatingsim/gui/ComparisonTab;gui/ComparisonTab',
        '--add-data', 'src/districtheatingsim/gui/EnergySystemTab;gui/EnergySystemTab',
        '--add-data', 'src/districtheatingsim/gui/LeafletTab;gui/LeafletTab',
        '--add-data', 'src/districtheatingsim/gui/ProjectTab;gui/ProjectTab',
        '--add-data', 'src/districtheatingsim/heat_generators;heat_generators',
        '--add-data', 'src/districtheatingsim/heat_requirement;heat_requirement',
        '--add-data', 'src/districtheatingsim/net_generation;net_generation',
        '--add-data', 'src/districtheatingsim/net_simulation_pandapipes;net_simulation_pandapipes',
        '--add-data', 'src/districtheatingsim/osm;osm',
        '--add-data', 'src/districtheatingsim/project_data;project_data',
        '--add-data', 'src/districtheatingsim/project_data;districtheatingsim/project_data',
        '--add-data', 'src/districtheatingsim/utilities;utilities',
        '--add-data', 'src/districtheatingsim/styles;styles',
        # Add file_paths.json to multiple locations to ensure it's found
        '--add-data', 'src/districtheatingsim/gui/MainTab/file_paths.json;gui/MainTab',
        '--add-data', 'src/districtheatingsim/gui/MainTab/file_paths.json;districtheatingsim/gui/MainTab',
        '--add-data', 'src/districtheatingsim/gui/MainTab/file_paths.json;.',
        # Add pandapipes data directories
        '--add-data', 'C:\\Users\\jonas\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages\\pandapipes\\std_types\\library;pandapipes/std_types/library',
        '--add-data', 'C:\\Users\\jonas\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages\\pandapipes\\properties;pandapipes/properties',
        # Exclude conflicting Qt bindings (app uses PyQt6)
        '--exclude-module', 'PyQt5',
        '--exclude-module', 'PySide2',
        '--exclude-module', 'PySide6',
        # Exclude other unnecessary modules to reduce size
        '--exclude-module', 'tkinter',
        # Use custom hooks directory for geospatial packages
        '--additional-hooks-dir=hooks',
        # Hidden imports for libraries that PyInstaller may miss
        '--hidden-import=geopandas',
        '--hidden-import=overpy',
        '--hidden-import=geojson',
        '--hidden-import=networkx',
        '--hidden-import=numpy_financial',
        '--hidden-import=pandapipes',
        '--hidden-import=pandapipes.timeseries',
        '--hidden-import=contextily',
        '--hidden-import=rasterio.sample',
        '--hidden-import=CoolProp',
        '--hidden-import=matplotlib.backends.backend_qt5agg',
        '--debug=all',
        '--log-level=DEBUG',
        '--console',  # Keep console for debug
        'src/districtheatingsim/DistrictHeatingSim.py'
    ]
    
    try:
        # Run PyInstaller and capture output
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Build started: {datetime.now()}\n")
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write("-" * 80 + "\n\n")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Stream output to both console and file
            for line in process.stdout:
                print(line, end='')
                f.write(line)
            
            process.wait()
            
            f.write("\n" + "-" * 80 + "\n")
            f.write(f"Build finished: {datetime.now()}\n")
            f.write(f"Return code: {process.returncode}\n")
        
        if process.returncode == 0:
            print(f"\n✓ Build successful!")
            print(f"Executable: dist/DistrictHeatingSim.exe")
            
            # Post-build cleanup: Remove device-specific files
            print("\nCleaning up device-specific files...")
            cleanup_device_specific_files()
        else:
            print(f"\n✗ Build failed with return code {process.returncode}")
            print(f"Check log file for details: {log_file}")
            
        return process.returncode
        
    except Exception as e:
        print(f"\n✗ Build error: {e}")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n\nFATAL ERROR: {e}\n")
        return 1


def cleanup_device_specific_files():
    """
    Remove device-specific configuration files from the build.
    
    These files should be created fresh on each user's machine and
    should not be bundled with the application.
    """
    import os
    
    # Files to remove (device-specific)
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
                print(f"  ⚠ Could not remove {file_path}: {e}")
    
    if removed_count == 0:
        print("  ℹ No device-specific files found to remove")
    else:
        print(f"  ✓ Cleaned up {removed_count} device-specific file(s)")


def move_user_data_outside():
    """
    Move data and project_data folders outside _internal for user accessibility.
    
    These folders contain user-editable data and example projects that should
    be easily accessible and modifiable by users.
    """
    import os
    import shutil
    
    dist_root = 'dist/DistrictHeatingSim'
    internal = os.path.join(dist_root, '_internal')
    
    # Folders to move (these should be user-accessible)
    folders_to_move = [
        'data',           # TRY, COP data files
        'project_data'    # Example projects (Görlitz, etc.)
    ]
    
    moved_count = 0
    
    for folder in folders_to_move:
        # Check various possible locations in _internal
        possible_sources = [
            os.path.join(internal, folder),
            os.path.join(internal, 'districtheatingsim', folder)
        ]
        
        target = os.path.join(dist_root, folder)
        
        for source in possible_sources:
            if os.path.exists(source):
                try:
                    # Remove target if it already exists
                    if os.path.exists(target):
                        shutil.rmtree(target)
                    
                    # Move folder to root level
                    shutil.move(source, target)
                    print(f"  ✓ Moved: {folder}/ from _internal to root")
                    moved_count += 1
                    break  # Found and moved, don't check other sources
                    
                except Exception as e:
                    print(f"  ⚠ Could not move {folder}: {e}")
    
    if moved_count == 0:
        print("  ℹ No user-data folders found to move")
    else:
        print(f"  ✓ Moved {moved_count} user-data folder(s) to root level")
        print(f"  → Users can now easily access and modify these folders")


if __name__ == '__main__':
    exit_code = build_with_debug()
    
    if exit_code == 0:
        print("\n" + "="*70)
        print("Post-Build Optimization: Moving user-accessible data...")
        print("="*70)
        move_user_data_outside()
    
    sys.exit(exit_code)
