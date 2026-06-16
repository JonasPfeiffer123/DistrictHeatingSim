# Changelog

All notable changes to DistrictHeatingSim will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-06-16

### Added
- **1D thermal storage model**: `ThermalStorageAdapter` (network/seasonal) and
  `BufferStorage` (CHP/biomass buffer) wrapping the published
  [thermal-energy-storage-1d](https://github.com/JonasPfeiffer123/thermal-energy-storage-1d)
  package, replacing the previous `STES` / `StratifiedThermalStorage` /
  `SimpleThermalStorage` classes. Storage capital + maintenance cost now feeds the
  system LCOH; dispatch, serialization and result plots are wired through it.
- **Terrain/elevation support**: DEM (GeoTIFF) or OpenTopoData API → per-vertex
  `height_m`, fed into the pandapipes geodetic head (`net_generation/elevation_utils.py`).
- **3D network visualisation** and improved STANET CSV import.
- **GUI entry point**: `districtheatingsim` console command (`[project.gui-scripts]`),
  in addition to `python -m districtheatingsim`.
- **Schema versioning & migration** for `project_settings.json`, the EnergySystem
  JSON, the building combined-data JSON, `dialog_config.json` and the network GeoJSON,
  via a shared `utilities/schema.py` helper (`_meta` block + registry).
- **CSV column-contract validation** (`utilities/csv_schemas.py`): missing/renamed
  columns now raise a clear up-front error naming every missing column.
- **Soft negative-pressure (cavitation) warning** in the pipeflow result validation.

### Changed
- **BREAKING — pandapipes 0.13 → 0.14.** Pinned to `pandapipes==0.14.0`. The legacy
  `KMR …` pipe std-types (`material="KMR"`) are re-anchored to ISOPLUS bonded-steel
  pipes (`ISOPLUS_DRE…`, `material="P235GH/PUR/PEHD"`); the heat-loss/diameter columns
  moved to `u_w_per_mk` / `inner_diameter_mm`. **Projects saved on 0.13 are migrated
  automatically on load** (KMR → nearest ISOPLUS, diameter/u recovered, std-type
  catalog refreshed). Diameter init now rounds *up* to satisfy `v_max` in a single pass.
- **Central physical constants** (`districtheatingsim/constants.py`): `KELVIN_OFFSET`,
  `CP_WATER_KJ_KGK`, CO₂ / primary-energy / BEW factors. Water `cp` unified to
  4.18 kJ/kg·K (changed the former 4.2 sites in the pandapipes layer by ~0.5 %).
- **EnergySystem results** are now `TechnologyResult` records (single source of truth);
  the German parallel result lists are a projection, so they can no longer diverge.
- `ProjectFolderManager` is the single owner of the TRY/COP file paths.
- Domain core is now PyQt6-free (encoder moved to `heat_generators/json_encoder.py`),
  so it imports and tests headless.

### Fixed
- **Energy-system optimizer no longer optimises the system out of existence**: a
  penalty on uncovered demand stops SLSQP from minimising the objective by undersizing
  generators (verified: a CHP previously collapsed to 0 kW / 0 % coverage).
- **Heat-pump electricity at part load**: River and Geothermal heat pumps now rescale
  electricity to the delivered (capped) heat output, fixing overstated
  electricity/CO₂/primary-energy/WGK.
- **CHP economics** keyed off an explicit `fuel_type` instead of the instance name
  (an arbitrarily-named CHP no longer raises `UnboundLocalError`).
- **`annuity()`** rejects the rate-instead-of-factor footgun (was silently ~0 cost).
- Dialog capacity read/write key asymmetry and the CHP/Holzgas storage-cost default typo.
- **GUI thread safety**: unified worker error signals, guards against concurrent
  energy-system / network runs, threads stopped on app close, and cooperative `stop()`
  (no `terminate()`) on geocode/generation restart to avoid truncated CSVs.
- **Return-network geometry**: each vertex is offset perpendicular to its local
  direction, so supply and return no longer overlap at angled segments.
- **Windows cp1252 console**: non-ASCII diagnostic prints no longer crash the app /
  diameter optimization (`UnicodeEncodeError`).
- Removed pandas chained-assignment writes (silent no-ops under Copy-on-Write).
- `NetworkGenerationData` numpy arrays and `secondary_producers` round-trip losslessly
  through the project JSON (previously saved/loaded as strings, breaking the time series).
- `preprocessData` raises a clear error when no main feed pump is found; EnergySystem
  guards single-step durations, zero-demand profiles and inconsistent zero-cost sentinels.
- Dead copy/paste buttons (`QClipboard()` constructor) and the ProjectTab geocode
  auto-reload (signal/handler tuple mismatch).
- Overpass building download HTTP 406 (missing User-Agent).
- Network build is guarded against non-convergence / NaN/inf result states.
- OS-agnostic TRY path in the photovoltaics example (Linux CI).

### Refactored
- **God-object decomposition**: `_04_technology_dialogs.py` → schema-driven
  `technology_dialogs/` package; shared `OSMDownloadDialogBase`;
  `interactive_network_plot.py` → a GUI-/Plotly-free `plot_data.py` data layer;
  GUI-free islands extracted from `main_view` (`project_structure.py`).
- **Domain logic pulled out of views** (B2): network recalculation/KPIs, infrastructure
  annuity, variant KPI aggregation, geometry centroid — into tested, GUI-free functions.

### Testing / CI
- New domain-core + simulation golden-master test suite (**313 non-slow tests**),
  deterministic fixtures, examples smoke suite.
- GitHub Actions CI: **gating** pytest (3.11 + 3.12) and `ruff check` +
  `ruff format --check` over the whole `src` tree (incl. GUI) + tests.

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
