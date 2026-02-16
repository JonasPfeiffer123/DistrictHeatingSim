# Changelog

All notable changes to DistrictHeatingSim will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# [1.0.1] - 2026-02-16

### Fixed
- Data folder and all required resource files (data/, images/, leaflet/, styles/) are now included in the pip package and accessible after installation ([#148](https://github.com/JonasPfeiffer123/DistrictHeatingSim/issues/148)).
- Unified resource path handling for pip, development, and PyInstaller builds (using get_resource_path).
- Funding logo and main logo now always available via images/ folder.
- build.py and build_debug.py updated to move images/ and leaflet/ to dist/ for user accessibility.

### Packaging
- MANIFEST.in updated to include all resource folders (data, images, leaflet, styles).
- file_paths.json and all code references updated to use forward-slash and images/ for logos.

### Note
- This release addresses the issue reported by @GauravLad20112: missing data/ folder in the PyPI package. All CSVs and resources required for BDEW and VDI 4655 profiles are now shipped and accessible after pip install.

## [1.0.0] - 2026-01-31

### Added
- Complete Sphinx reST documentation for all modules
- Comprehensive API documentation with parameter descriptions
- Example categorization and documentation in index.rstcd 
- Version tracking in package `__init__.py`
- Benchmark tool for network generation performance testing
- Support for synthetic GIS data generation
- Layer generation dialogs for OSM data import

### Changed
- **BREAKING**: `NetworkGeoJSONSchema.load_from_file()` renamed to `import_from_file()`
- Migrated all docstrings from Google Style to Sphinx reST format
- Updated documentation structure with better navigation
- Reorganized example categories based on functionality
- Updated copyright year to 2025

### Fixed
- **Critical**: Column existence checks in `net_generation.py` to prevent KeyError
- **Critical**: Scalar detection in `base_heat_pumps.py` for numpy 0-dimensional arrays
- Parameter order in `photovoltaics.calculate_solar_radiation()` call
- datetime64 handling in `solar_radiation.py` for proper time conversion
- Import paths in example 17 (energy_system_seasonal_storage.py)
- File paths in examples pointing to correct data directories
- BDEW datetime calculation bug in heat requirement calculations

### Removed
- Obsolete `11_example_lod2.py` example
- Non-functional `12_example_renovation_analysis.py` example
- `leaflet_dialogs.py` (functionality moved to separate dialog files)
- `lod2.rst` documentation file
- `project_structure.md` from project_data

### Documentation
- All modules now use Sphinx reST format for better API documentation
- Added detailed parameter and return value descriptions
- Improved cross-references between modules
- Updated example descriptions to match actual functionality
- Added testing results to documentation (89.7% example success rate)

### Testing
- Systematically tested all 29 examples
- Fixed 7 major bug categories
- Verified all core functionality
- Performance benchmarks: 0.06s per building average

### Performance
- Network generation shows linear scaling with building count
- Optimized MST algorithms for large networks (tested up to 300 buildings)

---

## [0.1.0] - Previous Development Versions

Initial development versions with basic functionality.
