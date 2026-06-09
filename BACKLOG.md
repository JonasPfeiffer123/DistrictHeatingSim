# DistrictHeatingSim — Technical Backlog / Known Issues

> Living document. Consolidated from the holistic code review plus findings made
> while integrating the 1D thermal storage model (2026-06). Ordered roughly by
> leverage. Update entries as they land.

## Recently resolved
- **1D thermal storage integration** — replaced `STES` / `StratifiedThermalStorage` /
  `SimpleThermalStorage` with `ThermalStorageAdapter` (network/seasonal) and
  `BufferStorage` (CHP/BiomassBoiler buffer), wrapping the published
  `thermal-energy-storage-1d` package. Merged to `main` 2026-06-09. Storage
  capital + maintenance cost now feeds the system LCOH.
- **`file://` dependency** — `pyproject.toml` now points at the public GitHub URL
  (was a local `file:///…` path that broke installs for everyone but the author).
- **Result-array divergence** (storage / buffer / unmet-demand rows) — the parallel
  result lists in `energy_system.py` are now appended in lockstep; previously they
  diverged and silently misaligned the results table, pie chart, Sankey and CSV
  export. *Structural refactor still open — see C4.*

---

## A. Foundation
### A1. Tests & CI/CD  ← in progress
~35k LOC with effectively no automated tests; `examples/` are the de-facto manual
tests. This is the safety net that makes every refactor below low-risk.
- **Landed 2026-06:** golden-master/regression suite on the GUI-free domain core —
  `tests/test_annuity.py` (VDI 2067 economics incl. the C5 footgun) and
  `tests/test_heat_generators.py` (GasBoiler, PowerToHeat, BiomassBoiler, CHP with
  frozen WGK / Wärmemenge / CO2 / primary-energy metrics). Deterministic fixtures
  in `tests/conftest.py`. GitHub Actions CI added (`.github/workflows/ci.yml`):
  `pytest` on 3.11 + 3.12 (gating) and `ruff` (advisory until the tree is clean).
  pytest/ruff config in `pyproject.toml`; `ruff` scoped to exclude the legacy GUI.
- **Landed 2026-06 (this session):** `tests/test_energy_system.py` — 34 tests:
  - `TestEnergySystemNoStorage` — integration golden-master (CHP + GasBoiler);
    pins `WGK_Gesamt`, per-tech `Wärmemengen`, and uses `_assert_parallel_lists()`
    to guard against C4-style divergence.
  - `TestEnergySystemWithNetworkStorage` — golden-master with a small
    `ThermalStorageAdapter` (100 m³ cylinder, 5 nodes); same structural guard;
    verifies SOC ∈ [0,1] and Q_loss ≥ 0 at system level.
  - `TestThermalStorageAdapter` — unit tests: SOC bounds, Q_loss ≥ 0, charge raises
    SOC / discharge lowers it, `to_dict`/`from_dict` roundtrip, old-config guard.
  - `TestBufferStorage` — unit tests: SOC/Q_loss bounds, history length, sign
    convention, reset.
  - `conftest.py` extended: `matplotlib.use('Agg')`, `time_steps`, `try_data_stub`,
    `cop_data_stub` fixtures. Suite now **68 passed** locally (Py 3.11, Windows).
- **Still open:**
  - Widen `ruff` coverage into `src/` module-by-module, then flip lint to gating
    and add `ruff format --check` over the whole tree.

## B. Architecture & maintainability
### B1. God-objects in the GUI  ← in progress
- **`_04_technology_dialogs.py` (1582 → 28-line façade): DONE 2026-06.** Extracted
  into a `technology_dialogs/` package: declarative `Field`/`CheckField` schema +
  `SchemaDialog` base (`_base.py`), per-tech schemas (`_schemas.py`), schema-driven
  `_simple.py` (Gas/PowerToHeat/WasteHeatPump) and `_combustion.py`
  (Biomass/CHP/HolzgasCHP, shared 9-field storage block via `storage_fields()`).
  The 6 migrated dialogs shrank from ~668 lines of copy-paste to ~125 lines of
  dialog-specific code + 117 lines reusable infra. `_04` is now a re-export façade
  so the import path (`from ..._04_technology_dialogs import TechInputDialog`,
  used in `_03_technology_tab.py:25`) is unchanged. Behaviour pinned by
  `tests/test_technology_dialogs.py` (44 tests, green before *and* after).
  - **Follow-up DONE 2026-06:** `_base.py` gained `ComboField` + `Section` (group
    boxes) + a viz-friendly `_build_fields()`; `_solar.py` (212→86), `_geothermal.py`
    (128→63) and `_heat_pump.py` (River+Aqva, 155→70) are now schema-driven (3D-viz /
    CSV kept via `_build()`/`getInputs()` overrides; viz reads `self._widgets`).
    Viz wiring covered by `TestVisualizationSmoke`. **48 dialog tests green.**
  - **Deliberately left hand-written:** `_storage.py` (ThermalStorage1D). It is
    *unique* (no duplication to remove) and has dynamic loss-model/fluid sections +
    conditional output (`U_top`/`T_ambient` resolved from the active section, three
    widgets for one value). Forcing it through the schema would grow `_base.py` more
    than it shrinks the dialog — net negative. Leave as-is.
- **`osm_dialogs.py` (1248 → 939): DONE 2026-06.** Two near-identical download
  dialogs (`DownloadOSMDataDialog`, `OSMBuildingQueryDialog`) shared method-level
  duplication. Extracted in two steps:
  - `osm/area_selection.py` (GUI-free, **13 tests**): `build_highway_filter`,
    `polygon_from_csv`/`_from_geojson`, `resolve_area_polygon`. Both worker methods
    (`downloadWithOSMnx`/`downloadBuildings`) now call it; ~95 lines of duplicated
    geo logic removed and the C9 thread bug fixed.
  - `osm_dialogs_base.py::OSMDownloadDialogBase`: shared map-polygon capture
    (`getCapturedPolygonFromMap`, `clearCapturedPolygon`, `_begin_polygon_capture`),
    thread-lifecycle (`_onDownloadCanceled`/`_onDownloadError`) and construction,
    parametrised via `self._download_button` / `_temp_polygon_filename`. Both
    dialogs inherit it; import path (`from ...osm_dialogs import …`, used in
    `leaflet_tab.py:28`) unchanged. Smoke-tested by `tests/test_osm_dialogs.py`
    (14 tests). The two distinct `initUI`/`startQuery`/`_onDownloadComplete` stay
    per-dialog (genuinely different — streets have highway filters + 4 area types).
- Still to tackle: `main_view.py` (~1232), `interactive_network_plot.py` (~1179) —
  same base-class treatment.
### B2. MVP violations
The main frame is clean, but individual tabs reach directly into
`data_manager` / domain objects and make business-logic decisions past the
presenter; dialogs call presenter methods directly.
### B3. Plotly tightly coupled to pandapipes
`interactive_network_plot.py` wires Plotly directly to pandapipes → hard to test.
### B4. DE/EN naming mix
`Wärmeleistung_kW` next to `HeatPump`, German UI strings + English docstrings;
inconsistent method names (`calculate_heat_generation_cost()` vs `…costs()`).

## C. Correctness & robustness
### C1. Threading not thread-safe
Worker threads (e.g. `_06_calculate_energy_system_thread.py`) mutate the shared
`energy_system` object without locking; error signatures are inconsistent
(sometimes an Exception, sometimes a str); thread lifecycle on dialog close is
partly unguarded.
### C2. Solver path lacks error handling
`run_timeseries()` runs without try/except, no convergence diagnostics, no
NaN/inf checks on results; disconnected / infeasible networks are not caught.
### C3. Naive return-network offset
The return network is generated by a naive geometry translation offset → fails at
tight crossings.
### C4. Fragile result aggregation (structurally fixed 2026-06)
`energy_system.py` kept ~8 parallel lists (`techs`, `Wärmemengen`, `Anteile`,
`WGK`, `specific_emissions_L`, `primärenergie_L`, `colors`, `Wärmeleistung_L`)
appended in lockstep across four code sites — the source of two (fixed) divergence
bugs. **Structural fix landed:** each row is now a `TechnologyResult` record
(`heat_generators/results.py`, English fields) appended via the single
`EnergySystem._add_tech_result(...)`; the German lists are a pure projection built
once by `_project_results()`. One append → all lists stay in lockstep, so divergence
is now impossible. Records are the source of truth (`es.tech_results`), not
serialized; the German `results` keys are kept for GUI + serialization compat
(Option A). Pinned by `tests/test_energy_system.py::TestTechnologyResultRecords`.
The broad DE/EN rename of the `results` *dict keys* (+ GUI + saved-project
migration) remains separate — see B4.
### C5. Economic-model footgun (fixed 2026-06)
`annuity()` expects interest/inflation as *factors* (`1.05`), not *rates* (`0.05`);
a rate silently yielded ~0 cost. **Fixed**: `annuity()` now raises a clear
`ValueError` when `interest_rate_factor <= 1` or `inflation_rate_factor < 1` (also
rejects `q == 1`, which makes the annuity factor 0/0). `r == 1` (0 % inflation)
stays valid. Pinned by `tests/test_annuity.py::TestAnnuityRateFactorGuard` (the old
characterization test was flipped). The GUI always passed factors, so production was
never affected — the guard just makes the misuse loud.
### C6. CHP cost calc brittle to instance name (fixed 2026-06)
`chp.calculate_heat_generation_costs()` (and `__init__`/`get_display_text`) branched
on `self.name.startswith("BHKW")` / `"Holzgas-BHKW"`; a `CHP` named anything else
left `spez_Investitionskosten_BHKW` unbound → `UnboundLocalError` (and `__init__`
never set the CO₂/primary-energy factors). **Fixed**: `CHP` now keys economics off
an explicit `self.fuel_type` (`"gas"` / `"wood_gas"`), a new constructor param
inferred from the name once (default `"gas"`); call sites use `_resolve_fuel_type()`
(falls back to name inference for pre-C6 saves, since `from_dict` bypasses
`__init__`). Standard `BHKW`/`Holzgas-BHKW` behaviour is unchanged (golden master
green); arbitrary names now default to gas instead of crashing. Pinned by
`tests/test_heat_generators.py::TestCHP` (`test_arbitrary_name_defaults_to_gas`,
`test_explicit_fuel_type_overrides_name`).
### C7. Dialog capacity read/write key asymmetry (fixed 2026-06)
`GasBoilerDialog` / `PowerToHeatDialog` / `BiomassBoilerDialog` read the capacity
field's initial value from `th_Leistung_kW` / `P_BMK` but emitted it under
`thermal_capacity_kW` (the generators' actual attribute), so editing an existing
tech reset the displayed capacity to the field default. **Fixed**: the schema
fields now read and write `thermal_capacity_kW` (dropped the `in_key` overrides in
`_schemas.py`); the add flow is unaffected (new techs open with an empty dict).
Round-trip now pinned by `tests/test_technology_dialogs.py::TestCapacityRoundTrip`.
(`Field.in_key` remains available as a general capability but is now unused.)
### C8. CHP/HolzgasCHP storage-cost default typo (fixed 2026-06)
The "spez. Investitionskosten Speicher" field defaulted to `"0.8"` in the CHP and
Holzgas-CHP dialogs but `"750"` in Biomass — a typo (€/m³). **Fixed**:
`_schemas.CHP_STORAGE` now defaults to `"750"`; `TestStorageToggle` updated.
### C9. GUI access inside OSM download threads (fixed 2026-06)
The OSM worker methods (`downloadWithOSMnx`/`downloadBuildings`) run inside
`OSMStreetDownloadThread`/`OSMBuildingDownloadThread` but called
`QMessageBox.warning(self, …)` + `return` when a CSV lacked `UTM_X`/`UTM_Y` — GUI
access off the main thread, and the `return None` then crashed on `polygon.bounds`.
**Fixed** by extracting the logic to `osm/area_selection.py`, which `raise`s
`ValueError`; the thread catches it and emits `download_error` → a proper error box
on the main thread. Pinned by `tests/test_area_selection.py`. (Audit the other
threads in `net_generation_threads.py` for the same anti-pattern.)
### C10. Overpass HTTP 406 on building download (fixed 2026-06)
`OSMBuildingQueryDialog` building downloads failed with
`OverpassUnknownHTTPStatusCode: 406`. Root cause: overpy 0.7 issues its request via
`urllib` **without a User-Agent**, and overpass-api.de rejects the default
`Python-urllib/x.y` UA with HTTP 406. **Fixed** in
`osm/import_osm_data_geojson.py`: a module-level global urllib opener now sends a
descriptive User-Agent, and `download_data` targets the HTTPS endpoint
(`OVERPASS_ENDPOINT`). Verified live (canonical endpoint returns features again);
config pinned by `tests/test_osm_import.py`. Only raw-urllib (overpy) traffic is
affected by the global opener — geopy/osmnx use their own HTTP stacks.

## D. State & data
### D1. Double state source
`try_filename` lives in both `DataManager` and `ProjectFolderManager` and is
synchronized manually — no single source of truth. Folder names like "Variante 1"
are hardcoded.
### D2. No schema versioning / migration
`project_settings.json` and the project JSONs have no version field → old projects
break on format changes. (The storage `from_dict` → `None` + warning is a one-off,
not a general migration path.)
### D3. Scattered physical constants / magic numbers
`cp` is sometimes 4.18, sometimes 4.2 kJ/kgK; `273.15` is hardcoded ~20×; CO₂
factors and temperature limits (e.g. the 75 K Hub) live locally in individual
generators. Fix: a central `constants.py` + a unit convention — eliminates the
4.18/4.2 class of bugs.

## E. Hygiene
### E1. `.gitignore` casing
`error_log.txt` (line 159) and `build_Logs/` (line 162) are ignored. Note: the
build-logs entry is capital-L (`build_Logs/`), which matches on case-insensitive
Windows but would **not** match a lowercase `build_logs/` on case-sensitive
Linux/CI — worth normalizing before CI runs on Linux. (An earlier review flagged a
committed `error_log.txt`; on inspection it was never tracked — already ignored, so
no action there.) The 52 MB Görlitz example project is large but acceptable.
### E2. Naming/method-name inconsistencies
Same root cause as B4.

---

## Suggested order
1. **A1 — Tests & CI** (the bracket that de-risks everything below).
2. **D3 — central constants** (cheap, kills a whole bug class).
3. **C4 / C5** (result-record refactor + economics hardening) — low-risk once A1 exists.
4. **B1** (break up the dialog god-object; biggest LOC win).
5. The rest (B2/B3, C1–C3, D1/D2, E1) as capacity allows.
