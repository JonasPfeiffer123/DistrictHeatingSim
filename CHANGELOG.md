# Changelog

All notable changes to DistrictHeatingSim will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.3] - 2026-03-18

### Added
- **CSV importer dialog**: load CSVs in any column format, auto-detect delimiter,
  auto-suggest column mappings via alias table and substring matching, fill missing
  fields with per-column defaults.
- **CSV template creation**: one-click generation of a correctly structured template
  CSV including all optional BDEW columns.
- **Extended BDEW profile parameters**: optional columns `Heizgrenztemperatur`,
  `Heizexponent`, and `P_max` in building CSV map directly to pyslpheat BDEW API
  parameters; missing values fall back to library defaults.
- **Configurable calculation year**: SpinBox in ProjectTab, persisted in
  `project_settings.json`; dynamic German national holiday computation for any year
  via Anonymous Gregorian Easter algorithm replaces hardcoded 2021 holidays.
- **Configurable projected CRS**: per-project CRS stored in `project_settings.json`
  and applied consistently across all coordinate transformations.
- **Multiple energy system configurations per project variant**: each variant can
  store several named energy system configs; active config tracked in
  `project_settings.json`.
- **TRY/COP file portability**: selected files are copied into project-local
  `Klimadaten/` and `Wärmepumpendaten/` subfolders; relative paths stored in
  `project_settings.json` so projects remain self-contained across machines.
- **TRY geographic location display**: `TemperatureDataDialog` shows the station
  coordinates extracted from the DWD filename pattern (primary) or by converting
  the file-header `Rechtswert`/`Hochwert` values from EPSG:3034 (Lambert Conformal
  Conic) to WGS84 (fallback); label updates live as the user browses.
- **COP Kennfeld visualisation**: `HeatPumpDataDialog` embeds a matplotlib heatmap
  of the COP matrix with per-cell annotations; updates live on file change.

### Fixed
- **Geocoding feedback**: `process_data()` now returns a summary dict
  (`total / success / failed / failed_addresses`); a dialog is shown after
  geocoding with succeeded and failed address counts.
- **Nominatim rate limiting**: added delay between requests to prevent HTTP 429
  errors from the Nominatim geocoding service.
- **OSM tile layer**: replaced unavailable OSM tile URL with CartoDB Positron to
  fix 403 errors in Qt WebEngine.
- **Pump junction assignment**: corrected VL/RL junction assignment in network
  initialisation.
- **Two pre-existing simulation errors** in network initialisation resolved.
- **OSM building import**: coordinates now correctly converted to EPSG:25833;
  fixed pandas `.at[]` indexing for building data.

### Refactored
- **CalculationTab** split from a 1865-line God Class into focused sub-widgets.
- **EnergySystem and heat generator base classes** cleaned up; wild imports removed.
- **Full GUI debug-print cleanup** across all tabs (comparison, leaflet,
  net-simulation, energy-system, building, project, dialogs).
- MVP architecture completed across all tabs.

### Build / Packaging
- Migrated from `setup.py` + `MANIFEST.in` to `pyproject.toml`
  (PEP 517/518, setuptools backend).
- Documentation dependencies moved to `[project.optional-dependencies] docs`;
  install with `pip install ".[docs]"`.
- `documentation_requirements.txt`, `RELEASE_CHECKLIST.md`, and `todo.md` removed;
  tracking moved to GitHub Issues.

## [1.0.2] - 2026-03-17

### Changed
- Migrated heat demand calculation to [pyslpheat](https://github.com/JonasPfeiffer123/pyslpheat) package.
  `heat_requirement_BDEW.py` and `heat_requirement_VDI4655.py` have been removed; callers now use
  `from pyslpheat import bdew_calculate, vdi4655_calculate`.

### Removed
- Internal modules `heat_requirement_BDEW.py` and `heat_requirement_VDI4655.py`.
- Bundled BDEW and VDI 4655 coefficient CSV files (`data/BDEW profiles/`, `data/VDI 4655 profiles/`);
  these are now shipped inside the `pyslpheat` package.

## [1.0.1] - 2026-02-16

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
