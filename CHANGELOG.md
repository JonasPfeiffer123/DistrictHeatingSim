# Changelog

All notable changes to DistrictHeatingSim will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-10-16

First release since 1.0.3. It bundles the 2026-06 refactoring, the 2026-09 performance audit
and the fixes from a first-time-user test of the GUI (2026-10-08, four real projects).
**Several fixes change calculation results** (see *Changed results*): recalculate a project
before comparing it with numbers from 1.0.x.

### Upgrading from 1.0.x
- **Recalculate existing projects** (heat demand → network initialisation → time series →
  generators). Saved networks are migrated on load (pandapipes 0.13 → 0.14, stale pipe outer
  diameters, pump controller gain), but stored load profiles and station profiles keep their
  old values until they are recalculated.
- **Residential projects (VDI 4655)** must recalculate the heat demand: their stored profiles
  have 35 040 quarter-hour rows.
- **New file formats:** load profiles (`Lastgang/Gebäude Lastgang.parquet`) and generator
  results (`Ergebnisse*.parquet`) are stored as Parquet, the pandapipes network as JSON instead
  of a pickle. Older JSON/pickle files still load (the newer file wins). **1.0.x cannot read the
  new files.**
- Settings and the recent-projects list moved to `%APPDATA%\DistrictHeatingSim` (taken over
  once from the installation folder). The log file is
  `%LOCALAPPDATA%\DistrictHeatingSim\logs\districtheatingsim.log`.
- A project that mixes VDI 4655 (EFH/MFH) and BDEW building types is refused; use the BDEW
  residential types HEF/HMF instead.
- Dependencies: pyslpheat pinned to v0.4.2, thermal-energy-storage-1d to v1.1.0,
  `plotly>=7.1`; new optional extra `fast` (numba, `pip install -e .[fast]`).

### Changed results
- **Pipe heat losses were 2–4× too high**: the diameter sizing never updated the pipes' outer
  diameter. Zittau design state 126.2 → 52.7 kW; Görlitz heat generation −2.0 %.
- **Simplified time series** booked the non-simultaneity of the building peaks as a permanent
  network loss. Zittau yearly network losses 49.3 % → 18.1 % (together with the fix above).
- **Minimum load** (2 %) refers to each house station's own peak instead of the largest
  station's. Small buildings were up to 49 % too high; Görlitz demand 4443.6 → 4155.1 MWh/a.
- **Pump lift**: the bad-point controller follows the current worst station; it kept the one
  found before the diameter sizing. Zittau 3.2 → 5.44 bar (one station had been at −1.09 bar).
- **Solar thermal lost about half its yield after a project was saved and reloaded** (IAM
  table keys; 200 m² vacuum tubes 93.4 vs 46.0 MWh). The storage balance is consistent now
  (±0.1 %).
- **Insulation grade** of the start pipe type (e.g. `_2x`) is kept by the diameter sizing; it
  fell back to the standard insulation.
- **VDI 4655 profiles are hourly** (summed from quarter hours). Read as hours, the quarter-hour
  rows gave 4× the annual energy and covered only January to March.
- **Infrastructure costs** are estimated from the network (route × 1000 €/m, house stations
  Σ peak load × 250 €/kW) instead of a flat 2 Mio. € network placeholder.

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
- **"Neues Projekt" assistant**: name and folder, place search with a CRS suggestion, TRY check
  (distance, DWD link, own file), climate zone, persons per household, and buildings from a
  table, OpenStreetMap or by hand.
- **Project location and climate**: location, VDI 4655 climate zone and persons per household
  per project (they were fixed to Oberlausitz / zone 9 / 2); a warning when the TRY lies more
  than 50 km away; new solar collectors take the project location; the map opens at the project.
- **Flow-centric network editing on the map**: only the supply line is edited, return lines and
  house connections are rebuilt on save. "Konnektivität prüfen" finds split networks and offers
  Auto-Snap; the network initialisation refuses a split network with a clear message.
- **Outdated results are marked** ("⚠ Veraltet" in the progress tracker, "(veraltet)" in the
  variant comparison) when buildings, load profiles or the network changed after a result was
  computed (`Berechnungsstand.json`; steps computed before 2.0.0 are not checked).
- **Time series**: progress with remaining time and a cancel button; optional parallel worker
  processes for the detailed calculation.
- "Datei → Projekt speichern" (Ctrl+S); a save writes only what changed.
- Network KPIs with and without house connections (route length, densities); after the
  initialisation a summary of the pump lift and the worst station.
- Geocoding report: addresses not found, found only to the street or town, or sharing one
  point, marked in the building table and on the map.
- OSM buildings → building list: addresses from the OSM tags, demand estimated from footprint ×
  storeys, outbuildings skipped.
- Table import: Excel exports (Windows-1252), decimal commas, street and house number from two
  columns, and a check of the values before anything is saved.
- Map: address labels with a toggle, the saved network loads with the project, works offline
  (bundled Leaflet libraries), OpenStreetMap basemaps without an API key.
- Pipe type selection by insulation grade, then nominal width; edited pipes are highlighted.
- New projects get the bundled TRY and COP files.
- `optimize_mix(seed=…)` for reproducible optimizations.

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
- The **simplified time series** is the default (the detailed one took 1.5–3 h for a year).
- **One heat-demand method per project** (VDI 4655 or BDEW).
- German throughout: Qt's own dialogs ("Abbrechen"), error messages with cause and hint
  instead of tracebacks (the traceback goes to the log file), units in all dialogs.
- Logging to a rotating log file instead of `print`.
- The heat demand tab shows the project's building list read-only; buildings are edited in the
  project tab only.
- The bundled example opens as a working copy in `Documents\DistrictHeatingSim`.
- The OSM street download includes `unclassified` streets and offers `track`.
- Overpass and Nominatim: retries and a fallback server; a final failure is reported in German.
- The AqvaHeat heat pump is hidden from the GUI (the model is incomplete).
- The 85/70 °C preset is called "Warmes Netz".

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
- **Optimizer** no longer returns systems that cover no demand (a CHP at 0 % coverage in 8 of
  12 seeds); runs stopped by the iteration limit compete with their actual objective.
- Crashes: two or more secondary producers in the time series; a static supply temperature
  with a start step > 0; network generation with elevation data, and MST with 3-D building
  points; a normal network without a COP file; a building with zero demand; a leap-year
  calculation year; the pipe material filter left over from KMR; reopening a network saved on
  the map (`feature_type`); dragging a component in the generator schematic; plotly 7
  (`Scattermap`); project load on a OneDrive folder (`WinError 183`).
- A failed network generation was reported as success.
- MST networks: house connections end on the return network (all of them were unconnected).
- The polygon street download dropped streets that cross the polygon boundary.
- Projects outside UTM zone 33: changing the CRS reprojects the building list; producer
  geocoding and the OSMnx export use the project CRS.
- Data safety: saving is refused while a calculation runs; imports write into the project's
  building list, not into the source file; no extra BOM per save; a save no longer writes the
  old network over one generated on the map since; project-tab edits are no longer overwritten
  by the heat demand tab.
- Tabs reset on a project change (no layers or results of the previous project); a double
  click in the project tree only switches variants; opening, closing and switching ask to save
  only when something is unsaved.
- Duplicate technology names after reloading a configuration.
- Variant comparison shows its KPIs at once; energy-mix pies share one legend; the year chart
  starts at 0 with readable names; sensitivity ranges lie around the base prices; the CSV
  export asks for the file.
- Welcome screen at 125–150 % display scaling.
- Project file paths on Linux and macOS.

### Performance
- Start to the welcome screen 3.7 → 0.5 s (tabs built on first use, heavy imports deferred).
- Network time series ~3.7× faster (Görlitz 275 → 74 ms per step): pump controller gain 0.6 and
  an undamped pipeflow with a damped retry.
- Energy-system optimizer with solar thermal ~2× faster (`examples/10` 28 → 13.5 s), 2 s with
  the optional numba kernel; the storage step is 2–3× faster with thermal-energy-storage-1d 1.1.0.
- Network generation: MST via scipy (300 points 3.9 s → 16 ms), nearest-street lookups via a
  spatial index (500 buildings 5.5 → 0.4 s).
- Heat demand runs on a worker thread (the window no longer freezes); pyslpheat 0.4.1 is
  10–20× faster per building.
- Görlitz files: load profiles 15.8 → 1.9 MB, generator results 20.8 → 1.8 MB.

### Refactored
- **God-object decomposition**: `_04_technology_dialogs.py` → schema-driven
  `technology_dialogs/` package; shared `OSMDownloadDialogBase`;
  `interactive_network_plot.py` → a GUI-/Plotly-free `plot_data.py` data layer;
  GUI-free islands extracted from `main_view` (`project_structure.py`).
- **Domain logic pulled out of views** (B2): network recalculation/KPIs, infrastructure
  annuity, variant KPI aggregation, geometry centroid — into tested, GUI-free functions.
- GUI-free data layers for the variant comparison, the progress tracker and the generator
  schematic; one place for naming and finding generator configurations (`config_naming.py`).

### Testing / CI
- New domain-core + simulation golden-master test suite (**861 tests**, 840 without the
  slow ones), deterministic fixtures, examples smoke suite.
- GUI tests with pytest-qt; an end-to-end harness that drives the real GUI through the
  scenarios of the 2026-10-08 user test (`tests/e2e/`).
- GitHub Actions CI: **gating** pytest (3.11 + 3.12) and `ruff check` +
  `ruff format --check` over the whole `src` tree (incl. GUI) + tests; also runs on work
  branches and annotates failing tests.

### Build / Packaging
- PyInstaller: pyslpheat and thermal-energy-storage-1d data bundled, numpy 2.x submodules
  collected, UPX off; shared spec/build helpers; `multiprocessing.freeze_support()` so the
  parallel time series works in the exe.

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
