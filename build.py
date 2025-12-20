# filepath: build.py
"""
Release build script for DistrictHeatingSim (no console window).
"""
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
    
    print(f"Starting PyInstaller RELEASE build...")
    print(f"Log file: {log_file}")
    
    # PyInstaller command for release (no console)
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'DistrictHeatingSim_Release.spec'
    ]
    
    try:
        # Run PyInstaller and capture output
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Release build started: {datetime.now()}\n")
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
            print(f"\n✓ Release build successful!")
            print(f"Output directory: dist/DistrictHeatingSim/")
            print(f"Executable: dist/DistrictHeatingSim/DistrictHeatingSim.exe")
            print(f"\nUser-accessible folders:")
            print(f"  - dist/DistrictHeatingSim/data/")
            print(f"  - dist/DistrictHeatingSim/project_data/")
            print(f"  - dist/DistrictHeatingSim/images/")
            print(f"  - dist/DistrictHeatingSim/leaflet/")
            
            # Post-build cleanup
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
    """Remove device-specific configuration files from the build."""
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
    """Move data and project_data folders outside _internal for user accessibility."""
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
                    break
                    
                except Exception as e:
                    print(f"  ⚠ Could not move {folder}: {e}")
    
    if moved_count == 0:
        print("  ℹ No user-data folders found to move")
    else:
        print(f"  ✓ Moved {moved_count} user-data folder(s) to root level")


if __name__ == '__main__':
    print("="*70)
    print("RELEASE BUILD - No Console Window")
    print("="*70)
    print()
    
    exit_code = build_release()
    
    if exit_code == 0:
        print("\n" + "="*70)
        print("Post-Build Optimization: Moving user-accessible data...")
        print("="*70)
        move_user_data_outside()
        
        print("\n" + "="*70)
        print("✓ RELEASE BUILD COMPLETE")
        print("="*70)
        print("\nThe application is ready for distribution.")
        print("Location: dist/DistrictHeatingSim/")
    
    sys.exit(exit_code)
