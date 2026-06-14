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
- **Landed 2026-06 (ruff sweep):** ran ruff over the lint-scoped tree (src minus
  gui, + tests) for the first time — **694 → 48 findings**, all behaviour-preserving
  and test-verified (168 passed after each batch). Applied: PEP 585/604 type hints
  (UP006/UP045/UP007), import sorting (I001), empty f-strings (F541), unused-import
  removal (F401, +explicit `__all__` on `heat_generators/__init__.py`), comparison
  fixes (E711/E712), `zip(strict=False)` (B905). `energy_system.py` hand-cleaned
  (mutable-default args, removed `import *`, closure binding, `raise … from e`) — the
  whole **tested** domain core is now lint-clean.
- **Landed 2026-06 (lint long-tail → gating):** cleared the remaining **48 → 0**
  findings in the untested modules (`net_simulation_pandapipes`, `net_generation`,
  `heat_requirement`, `photovoltaics`, `DistrictHeatingSim.py`, `utilities`), all
  behaviour-preserving + verified (217 passed, import smokes on every touched module):
  B904 (exception chaining), F841 (dead code removed — incl. a wasted 8760-element
  `np.array` build; the `heat_requirement` column reads kept as KeyError validation),
  E741 (Easter `l`→`ll`), E722 (`except Exception`), E402 (moved the runtime pyogrio
  filter below the imports; `# noqa` on the intentional DeprecationWarning-before-imports
  block), B007 (unused loop vars → `_`). **`ruff check .` is now GATING in CI**
  (`continue-on-error` removed, ruff pinned to `0.15.16`); the scoped tree (src minus
  gui, + tests) is clean.
- **Landed 2026-06 (GUI widening, step 1):** assessed + started clearing the GUI.
  **224 findings → 50.** Surfaced **one real bug**: `welcome_screen.py` used
  `sys.frozen`/`sys._MEIPASS`/`sys.executable` with no module-level `import sys`
  (NameError in the frozen-exe path) — fixed (F821). Then a safe-autofix sweep over the
  whole GUI (I001, F401, UP006/045/035, UP015, …) cleared 171 more, all
  behaviour-preserving (verified: 57 GUI modules import offscreen, 217 passed). The
  GUI is **still excluded** from the gating config.
- **Landed 2026-06 (GUI widening, step 2 — DONE):** cleared the remaining 50
  behaviour-neutral findings (B905 `strict=False`, E712, B904 `from e`, B007 `_`,
  E702 semicolons split, F841 — side-effecting calls kept as statements incl. the
  `float()` UTM validation + `addButton`/`plot_surface`, pure reads deleted —, E722,
  UP007). **`gui` dropped from `extend-exclude`**, so `ruff check .` now lints + **gates
  the whole `src` tree incl. the GUI**. Verified: all 57 GUI modules import offscreen,
  217 passed.
- **Landed 2026-06 (simulation golden-master):** `tests/test_simulation_golden_master.py`
  drives the real Görlitz project through the exact GUI calc chain
  (`initialize_geojson` → `time_series_preprocessing` → `thermohydraulic_time_series_net`
  → `calculate_results`) and pins the headline KPIs — geometry/demand tight (rel 1e-4,
  match the GUI), pipeflow-derived looser (1–2 %, cross-platform drift), sizing
  structural (68 ISOPLUS). `slow` + skipif-data-absent; verified deterministic. This is
  the regression net under the whole 0.14 / net-simulation pipeline. *Minor finding:*
  `calculate_results` computes `Jahresgesamtwärmebedarf` from the full-year
  `waerme_ges_kW` while `Jahreswärmeerzeugung` reflects the simulated range — so for a
  **partial** run the loss KPIs are nonsensical (negative). Harmless for the GUI (runs
  the full year); slice the demand to `[start:end]` if partial runs ever matter.
- **Landed 2026-06 (examples smoke net):** `tests/test_examples_smoke.py` runs the
  GUI-free / network-free `examples/` scripts as subprocesses (UTF-8 + Agg + offscreen,
  from the repo root) and asserts they exit cleanly — the examples were the de-facto
  manual tests but nothing guarded them against API drift (they rot silently, cf. the
  0.13→0.14 migration and C13). Does **not** pin values (some use `np.random`); only
  catches crashes/import breakage. Fast set (03/03b/09/10/14/15/17/18_chp/BHKW) runs by
  default; `06`/`07` are `slow` (~15-25 s, numba). `08` excluded (multi-minute full time
  series — covered by `test_simulation_golden_master.py`). Network/Qt/external-path
  examples excluded. Surfaced + fixed C13 (encoding) and stale examples (18_stanet
  hardcoded OneDrive path → committed STANET data; 09 "not up-to-date" note removed).
- **Still open:**
  - Decide on `ruff format` (not yet applied — `ruff format --check tests` reports 10
    files; the CI format step is **advisory** for now). Adopting it reformats the tree.
  - The CI `lint` job is now gating but still **unverified on GitHub** (first gating run
    happens on the next push).

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
- `interactive_network_plot.py` **done (B1/B3, 2026-06)**: 1179 → 755 LOC, now a
  Plotly-only renderer; all net queries moved to the new `plot_data.py` (548 LOC,
  Plotly-/GUI-free, unit-tested). See B3.
- Still to tackle: `main_view.py` (~1232).
### B2. MVP violations
The main frame is clean, but the MVP pattern is applied inconsistently and domain
logic leaks into the views. Concrete findings (2026-06 survey):

1. **Two architectures side by side.** `BuildingTab` and `LeafletTab` have a real
   Model/View/Presenter triad; `NetSimulationTab`, the `EnergySystemTab` sub-tabs,
   `ComparisonTab` and `ProjectTab` skip the presenter and hold `folder_manager` +
   `data_manager` directly, coordinating themselves.
2. **Domain/business logic executed inside views:**
   - ~~`net_simulation_tab.recalculateNetwork` runs `pp.pipeflow` + `run_control`
     directly in a view method.~~ **First slice done (2026-06):** the solver step is
     now `utilities.recalculate_net(net)` (pipeflow + controllers, wraps solver
     failures in a clear `RuntimeError`), called from a `NetRecalculationThread`
     worker (no more UI-thread freeze), with `_on_recalculation_done/_error` handlers
     mirroring the init/timeseries flows. Unit-tested via the net seam
     (`test_net_simulation.py` — reconverge + error wrapping). **Done.**
   - ~~`_05_cost_tab.py:422` calls `annuity(...)` in the view.~~ **Done (2026-06):**
     the economic mapping is now `annuity.infrastructure_annuity(…, economic_parameters)`
     (maps the GUI dict to `annuity()`, guards a zero lifespan); the tab's
     `calc_annuität` is a thin pass-through. Tested in
     `test_annuity.py::TestInfrastructureAnnuity`.
   - ~~`network_info_panel.py:105` calls `network_data.calculate_results()` in a panel.~~
     **Done (2026-06):** the worker threads (init/timeseries/recalc) now compute
     `calculate_results()` off the UI thread when they produce the net; the panel just
     renders `network_data.kpi_results` (falling back to compute only for an older
     loaded project whose JSON predates `kpi_results`). KPI computation pinned by
     `test_net_simulation.py::TestNetworkInitialization::test_calculate_results_topology_kpis`.
   - Worker threads (`_06_calculate_energy_system_thread`, `net_calculation_threads`)
     call domain code — more acceptable (off-UI-thread) but still GUI-package
     orchestration.
3. **Cross-component reach-through.** `main_view` drives other tabs by calling their
   presenters directly (`buildingTab.presenter.load_csv(...)`,
   `projectTab.presenter.save_csv(...)`).

Full normalisation (presenters everywhere) is a large, untestable GUI refactor; the
tractable wins are pulling domain logic out of the views into testable domain
functions (leveraging the net-simulation test seam).
### B3. Plotly tightly coupled to pandapipes (done 2026-06)
`interactive_network_plot.py` (was ~1179 LOC, one class, 60 `self.net` reads) mixed
pandapipes queries with Plotly trace building in each `_add_<component>` method → hard
to test. **Decoupled** into `net_simulation_pandapipes/plot_data.py`, a Plotly-free /
GUI-free, unit-tested data layer (548 LOC); `interactive_network_plot.py` is now a
755-LOC Plotly-only renderer. Slice-by-slice (one commit each): parameters
(`available_plot_parameters` + `parameter_label`/`parameter_value`), junctions
(`junction_plot_data` + `junction_geodata_wgs84`), pipes (`pipe_plot_data`), heat
consumers (`heat_consumer_plot_data`), pumps (`pump_plot_data`, both pump tables +
the supply/return hover swap), flow controls (`flow_control_plot_data`). Each `_add_*`
is now a thin renderer over a `*_plot_data(net, junctions_wgs84, parameter)` call.
Tested in `tests/test_net_simulation.py` (TestAvailablePlotParameters, TestJunctionPlotData,
TestParameterHelpers, TestPipePlotData, TestHeatConsumerPlotData, TestPumpPlotData,
TestFlowControlPlotData) + a slow render smoke (`test_interactive_plot_renders`, builds
a real figure from the net seam).
### B4. DE/EN naming mix
`Wärmeleistung_kW` next to `HeatPump`, German UI strings + English docstrings;
inconsistent method names (`calculate_heat_generation_cost()` vs `…costs()`).
### B5. Domain core imports the GUI (fixed 2026-06)
`heat_generators/energy_system.py` imported `CustomJSONEncoder` from
`gui/EnergySystemTab/_10_utilities.py`, which imports PyQt6 — so the GUI-free domain
core (and every test that touches it) transitively required PyQt6, and the Linux CI
failed to even import it (`libEGL.so.1`). **Fixed**: moved the encoder (a pure
`json.JSONEncoder`, no GUI dependency) to `heat_generators/json_encoder.py`;
`energy_system` imports it from there, `_10_utilities` re-exports it for the GUI. The
domain core is now PyQt6-free, pinned by `tests/test_serialization.py` (subprocess:
importing `energy_system` must not load `PyQt6`). *Note:* the CI apt step for Qt libs
is still required for the actual GUI tests.

## C. Correctness & robustness
### C1. Threading not thread-safe (partially fixed 2026-06)
Worker threads mutate shared state without locking; error signatures were inconsistent;
thread lifecycle is partly unguarded. **Fixed:**
- **Error signals unified** — all 10 GUI worker threads now use `pyqtSignal(str)`
  carrying the formatted message (was a mix of `str` / `Exception`, plus
  `NetGenerationThread` emitting `Exception(...)` on a `str` signal — a type mismatch).
- **Concurrent-calc race** — `CalculateEnergySystemThread` (which mutates the shared
  `energy_system` via `calculate_mix`) gained a `stop()`, and `start_calculation` now
  refuses to launch a second run while one is in flight (previously it orphaned the
  first thread and let two mutate the same object at once).
- **Threads stopped on close** — each thread-owning tab (`NetSimulationTab`,
  `EnergySystemTab`, `VisualizationTabLeaflet`→its presenter) now has a `stop_threads()`
  method (built on `gui/utilities.stop_qthreads`, which `stop()`s each running thread),
  and `main_view.closeEvent` calls it on every tab before `event.accept()` — no more
  QThread destroyed while still running on app exit.

*Still open:* the deeper isolation (worker operates on a deep copy / the
producer→`calculation_done`→main-thread-swap pattern made uniform) for the cases a
single in-flight run is read by the UI — lower priority now the double-start + close
races are closed.
### C2. Solver path lacks error handling (partially fixed 2026-06)
`run_timeseries()` ran without try/except and no NaN/inf checks, so a non-converged
or infeasible run either crashed opaquely or let NaN propagate into the heat/
temperature post-processing. **Fixed for the thermohydraulic path:**
`net_simulation_pandapipes/result_validation.py::validate_simulation_results`
(GUI-free, numpy-only — unit-tested in `tests/test_net_simulation.py`) raises a clear
`RuntimeError` on an empty result set or NaN/inf in any result array;
`thermohydraulic_time_series_net` now wraps `run_timeseries` in try/except (adds run
context) and validates `np_results` before post-processing. The **simplified** path is
also guarded: `validate_design_state` rejects a NaN/inf design state (failed init
pipeflow) before it is scaled across every time step. Both validators are unit-tested
in `tests/test_net_simulation.py`. **Build-time guard added:** `create_network` now
calls `validate_net_results(net)` after the design pipeflow + diameter sizing — an
empty or NaN/inf `res_junction` raises a clear `RuntimeError` (disconnected/infeasible
network) instead of letting NaN reach the time series. Unit-tested
(`TestValidateNetResults`) + verified it passes on the real Görlitz net.
*Update (C11):* a live end-to-end network seam now **exists** —
`test_net_simulation.py::TestNetworkInitialization` (marked `slow`) builds + solves a
tiny net on pandapipes 0.14 and `recalculate_net` is tested through it. The earlier
blocker (the repo's `examples/06_*` not converging) was resolved by the 0.14 migration;
the seam is the leverage for the remaining C1/C3 + the `net_simulation_pandapipes` ruff
long-tail.
### C3. Naive return-network offset (fixed 2026-06)
The return network was generated by translating **every vertex by one fixed vector**
(`offset_lines_by_angle`), so segments running parallel to that direction ended up
collinear with — lying on top of — the supply line (worst at tight crossings).
**Fixed:** each vertex is now offset **perpendicular to its local direction** (the
segment perpendicular, flipped to the `angle_degrees` preferred side), so segments of
every orientation are separated. Connectivity is preserved exactly — the offset is
computed once per vertex coordinate, so a shared vertex maps to a single return
coordinate (the junction model keys on exact coordinate tuples); at a multi-orientation
junction the return naturally converges but never overlaps. Z/elevation carried over.
Pinned by `tests/test_net_generation.py::TestReturnNetworkOffset` (perpendicular offset,
shared-junction connectivity, no supply/return overlap for any orientation, Z
preserved). Independent of the golden-master (which loads pre-generated geometry).
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
### C11. pandapipes 0.13 → 0.14 migration (in progress 2026-06)
The repo's pipe types (`KMR 100/250-2v`, `material="KMR"`) only exist on pandapipes
**0.14**, where they are anchored as ISOPLUS bonded-steel pipes (`ISOPLUS_DRE…`); on
0.13 those std-types are absent (the code was already broken for them). **Done:**
pin bumped to `0.14.0`; `KMR 100/250-2v` → `ISOPLUS_DRE100_2x` and `material="KMR"` →
`"P235GH/PUR/PEHD"` across `dialog_config.json`, the diameter helpers and the examples.
0.14 stores the ISOPLUS heat loss as `u_w_per_mk` [W/m·K] (per length) and leaves the
legacy `u_w_per_m2k` empty, so `net_simulation_pandapipes/pipe_std_types.py::resolve_pipe_u_w_per_m2k`
returns the per-area value when present else converts via the outer surface
(`u/(π·d_outer)`, matching pandapipes); applied at all 6 read sites; unit-tested in
`tests/test_net_simulation.py`. **Diameter columns migrated:** 0.14 removed the pipe
`diameter_m` column (std-type pipes carry `inner_diameter_mm` [mm]); all 12 sites in
`utilities.py` (`init_diameter_types`, `optimize_diameter_types`,
`optimize_diameter_parameters`, the GeoJSON export) now use `inner_diameter_mm` with
explicit unit handling. **`examples/06` runs end-to-end on 0.14** (all three net
builders converge; pipes get ISOPLUS std-types, finite u-values). Added an end-to-end
**network test seam**: `tests/test_net_simulation.py::TestNetworkInitialization`
(marked `slow`, ~30 s numba cold-start) builds a tiny net + runs the production
diameter-init path, asserting convergence / finiteness / ISOPLUS selection — the first
real test of the simulation code, and the seam for C1/C3. **Old-project load
migration:** a net pickled on 0.13 (KMR std-types, `diameter_m`, no
`inner_diameter_mm`) crashed `pipeflow` on load and showed obsolete KMR names.
`net_migration.migrate_loaded_net` (called in `net_simulation_tab.loadNet`) re-anchors
KMR pipes to their ISOPLUS successors (`kmr_to_isoplus_std_type`, taking diameter +
u from the catalog) and adds `inner_diameter_mm` from the legacy `diameter_m`; unit-
tested in `tests/test_net_simulation.py`. **Embedded-catalog gotcha:** a pickled net
ships its own `net.std_types["pipe"]` library — an old one holds only KMR types, so the
remap must look up (and replace the net's library from) a *fresh* net's catalog, else
the GUI combo keeps offering KMR. `pipe_config_table.py` also read/wrote the obsolete
`diameter_m` column at 5 sites → moved to `inner_diameter_mm`. **Nearest-size snap:**
some legacy names have a blank outer diameter (`KMR 175/-2v`) and a nominal width with
no ISOPLUS size (DN175); `nearest_isoplus_for_kmr` parses these and snaps to the same
insulation grade at the nearest available width (DN175 → DRE200, rounding up on a tie),
so every pipe maps to a valid type instead of silently defaulting to `80_GGG` (and
crashing the u lookup). Verified on the real Görlitz net (68 pipes → all ISOPLUS,
pipeflow converges). `apply_changes_to_net` also guards the u lookup. **197 passed.**
**Full production path verified on 0.14:** ran the GUI's net-generation +
time-series chain on the real Görlitz data — `initialize_geojson` / `create_network`
→ `time_series_preprocessing` → `thermohydraulic_time_series_net` →
`calculate_results` produces the headline metrics (Jahreswärmebedarf, Trassenlänge,
Verteilverluste …); example 07's time-series path also runs. Last `material_filter="KMR"`
references in `examples/06b/08` migrated to `"P235GH/PUR/PEHD"`.
**pandas chained-assignment fixed:** the time-series controllers + diameter helpers
wrote through chained indexing (`net.heat_consumer["treturn_k"].at[i] = …`,
`net.pipe.std_type.at[i] = …`) → silently a no-op under pandas 3.0 Copy-on-Write. All
9 write sites in `controllers.py` / `utilities.py` moved to single-step `.at[i, col]`
/ `.loc[:, col]`; verified the full time-series runs clean under
`-W error::FutureWarning`.
**`examples/08` modernised:** dropped the obsolete split-to-temp-files dance + the
multi-path `NetworkGenerationData` API (`flow_line_path` …) for the current
`network_geojson_path`; points at `examples/data/osmnx_steiner_output/Wärmenetz.geojson`
with `secondary_producers=[]` (that data set has one producer). Runs end-to-end on 0.14
(net generation → time series → `calculate_results` → plots).
*Still open (minor):* the changed circ-pump behaviour — pandapipes logs a one-time
INFO that the pump outlet temperature is now fixed; "in most cases this does not change
the outcome", not yet cross-checked against 0.13. No `diameter_m` reads remain in `src`
except the intentional one in `net_migration` (old → new column). C11 is otherwise
complete.
### C12. NetworkGenerationData arrays round-trip as strings (fixed 2026-06)
`net_simulation_tab.saveNet` writes the network-init JSON with
`json.dump(meta, …, default=str)`, so the numpy-array fields
(`return_temperature_heat_consumer`, `min_supply_temperature_heat_consumer`, …) are
saved as their `str(array)` repr instead of a list — and `NetworkGenerationData.from_dict`
loaded them back as **`str`**. `thermohydraulic_time_series_net` gates its controller
updates on `isinstance(…, np.ndarray)`, so the (string) return-temperature controllers
were silently skipped → their 1-row design `DFData` survived → the time series died at
step 1 with `KeyError: 1` (surfaced via the C2 wrapper as "Thermohydraulic time-series
simulation failed"). This blocked **every** loaded project's time-series run, not just
old ones. **Fixed (load side):** `from_dict` now coerces every `np.ndarray`-typed field
back to an array (`NetworkGenerationData._coerce_array`: list / 1-D `str(array)` repr →
array; truncated/2-D/garbage → `None`, since those are recomputed or reloaded from the
CSV). The per-consumer fields are small and parse cleanly; verified end-to-end on the
Görlitz project (load → preprocess → thermohydraulic → `calculate_results`). Tested by
`tests/test_net_simulation.py::TestNetworkDataArrayCoercion`. **Save side fixed too:**
`saveNet` now dumps with `NetworkDataClass.json_default` (numpy arrays → lists, scalars
→ native, `str` fallback) instead of `default=str`, so arrays are written losslessly
(no more numpy `…` abbreviation); the big time-series arrays are still popped + stored
in the CSV. Lossless save+load round-trip pinned by
`TestNetworkDataArrayCoercion::test_json_default_round_trip_is_lossless`.
**`secondary_producers` round-trip fixed:** `json_default` now serialises any dataclass
via `asdict` (so each `SecondaryProducer` is saved as a dict, not `str(obj)`), and
`from_dict` rebuilds them with `_coerce_secondary_producers` (dict → object; legacy
`str` reprs dropped). Previously a non-empty list saved as `str(obj)` and loaded as
strings, breaking the time-series code's `producer.index` access. Pinned by
`tests/test_net_simulation.py::TestSecondaryProducerRoundTrip` + verified through
`from_dict` on the real Görlitz config. C12 is complete.
### C13. Non-ASCII prints crash under the Windows cp1252 console (fixed 2026-06)
~37 diagnostic `print` statements across 9 domain/simulation modules emit non-ASCII
characters (`→`, `≤`, German umlauts). On Windows the default console codepage is
cp1252, where `→`/`≤` are unencodable, so `print()` raises `UnicodeEncodeError`. The
worst was `net_simulation_pandapipes/utilities.py::optimize_diameter_types` (printed
`{current_type} → {new_type}`): this is **production code the GUI runs**, so the
diameter optimization crashed mid-run whenever stdout was cp1252 (terminal launch,
frozen exe, or any redirected stdout). Reproduced via `examples/08` (failed inside
`utilities.py:559`, not the example). **Fixed in two layers:** (1) the GUI entry point
`DistrictHeatingSim.main()` now calls `_configure_stdio_encoding()`, reconfiguring
stdout/stderr to UTF-8 with `errors="backslashreplace"` (guarded for the frozen
no-console case) — robust for *all* current/future prints in the running app; (2) the
4 `→`/`≤` decorations in `optimize_diameter_types` are now ASCII (`->`/`<=`) so the
simulation library is safe even when imported outside the app. Verified: `examples/08`
runs end-to-end under `PYTHONIOENCODING=cp1252`. Guarded by `tests/test_examples_smoke.py`
(runs the examples with UTF-8) — the GUI entry-point reconfigure itself is not unit-tested
(it mutates process-global streams). *Note:* the remaining umlaut prints in
`heat_generators/*` are cp1252-safe (umlauts exist in cp1252) and covered by layer (1).
### C14. Result validation accepts physically-impossible negative pressures (open)
`result_validation.py` (`validate_simulation_results` / `validate_net_results`) checks
only for **NaN/inf**, not physical plausibility. The real Görlitz golden-master run
converges with *negative absolute pressures* at ~9 junctions — pandapipes itself logs
"results are physically incorrect as pressure is negative at nodes […]" — yet every
validator passes it silently and `calculate_results` reports KPIs as if valid. Root
cause is config, not code: `flow_pressure_pump=4.0` / `lift_pressure_pump=1.5` bar
under-pressurizes that network (head < friction loss at the far nodes → vacuum). But
the app gives the planner no signal that the result is unphysical. **Recommendation:**
add a *soft* `validate_pressure_plausibility(net)` that surfaces a clear warning (not a
`RuntimeError` — under-pressurized planning scenarios are legitimate intermediate
states, and raising would break the golden master which pins this exact net). Decide
warn-vs-raise with Jonas before implementing. Found while investigating the golden-master
warning 2026-06.

## D. State & data
### D1. Double state source (fixed 2026-06)
`try_filename`/`cop_filename` lived in both `DataManager` and `ProjectFolderManager`,
mirrored by hand in `main_view` (and slightly buggy: raw vs project-copied path).
**Fixed**: `ProjectFolderManager` is now the single owner (it persists them in
`project_settings.json`); `DataManager` holds only `map_data`; the three consumer
tabs read `folder_manager.try_filename/.cop_filename` (they already held the ref).
Pinned indirectly by `tests/test_project_settings.py`. *Still open:* folder names
like "Variante 1" are still hardcoded (separate, smaller item).
### D2. No schema versioning / migration (fixed 2026-06)
Neither `project_settings.json` nor the EnergySystem project JSON had a version
field. **Fixed**: both carry a `version` (`PROJECT_SETTINGS_VERSION`,
`ENERGY_SYSTEM_SCHEMA_VERSION`) and route loads through a migration hook
(`_migrate_project_settings`; `from_dict` reads + warns on newer-than-app files).
Old files (no `version` = v0) still load with defaults. Pinned by
`tests/test_project_settings.py` + `tests/test_energy_system.py::TestSerializationVersion`.
(The storage `from_dict` → `None` + warning remains its own one-off path.)
### D3. Scattered physical constants / magic numbers (largely fixed 2026-06)
`cp` was both 4.18 and 4.2 kJ/kgK; `273.15` was hard-coded ~20×; CO₂/primary-energy/
BEW factors were duplicated across generators. **Fixed**: central
`districtheatingsim/constants.py` (`KELVIN_OFFSET`, `CP_WATER_KJ_KGK`, `CO2_FACTOR_*`,
`PRIMARY_ENERGY_FACTOR_*`, `BEW_SUBSIDY_SHARE`). All generators + the
`net_simulation_pandapipes` Kelvin/cp sites now import from it. The factor + Kelvin
centralization is value-identical (golden masters unchanged); **cp was unified to
4.18** — this *changed* the former `4.2` sites in the (untested) pandapipes layer by
~0.5 % toward correctness. Pinned by `tests/test_constants.py`.
- **Still open:** temperature limits (e.g. the 75 K Hub) and `cp=4187 J/kgK` in
  `thermal_storage.py` (different unit system) were intentionally left; fold in if a
  unit convention is formalized.
### D4. Project-wide serialization/versioning strategy (not started)
D2 versioned only two artifacts (`project_settings.json`, EnergySystem JSON). The app
reads/writes **many** serialized files of different kinds, and most are unversioned.
A blanket "add a version field everywhere" is wrong — the strategy must be
differentiated by artifact kind.

**Inventory (the persistence footprint):**
- **Project-state JSON (app-owned, format evolves → version):** `project_settings.json`
  ✅(D2), EnergySystem results JSON ✅(D2), building combined-data JSON
  (`BuildingTab/building_tab.py::save_json`), `dialog_config.json`
  (`NetSimulationTab/net_generation_dialog.py`).
- **App-config JSON (app-owned, lower priority, regenerable):** `recent_projects.json`,
  `file_paths.json` (`MainTab/main_data_manager.py::ProjectConfigManager`).
- **Network GeoJSON (app-owned):** `net_generation/network_geojson_schema.py` — version
  belongs *inside* the GeoJSON (top-level/`properties` key), not a sidecar.
- **Domain CSV (app + user-editable):** building/Lastgang CSVs (`UTM_X`/`UTM_Y` …),
  geocoding CSV (`GeoJSONToCSVThread` fieldnames), results CSV
  (`energy_system.save_to_csv`, `pp_net_time_series_simulation.save_results_csv`). The
  **column header is the contract** — a version row would break pandas/Excel interop.
- **Interchange / ephemeral (do NOT version):** OSM GeoJSON layers (external standard),
  Leaflet HTML, plot outputs (regenerated on demand).

**Strategy:**
1. **One shared helper + registry.** D2 already duplicated the version+migrate logic
   twice (the C4 anti-pattern again). Add `utilities/schema.py` with
   `write_versioned(data, kind, version)` / `read_versioned(raw, kind, current, migrate)`
   writing a `"_meta"` block, plus a single registry listing every versioned artifact +
   its current version + migration steps. Migrate `project_settings`/`EnergySystem` onto
   it (removes the scattered `*_VERSION` constants).
2. **Separate `schema_version` from `app_version`.** Schema version drives migration;
   `app_version` (`districtheatingsim` from `pyproject`, e.g. 1.0.3) is diagnostics only.
   Both live in `"_meta"`.
3. **CSV = column-contract validation, not a version field.** Centralize required
   columns (`csv_schemas.py`: required columns per file kind + `validate(df, schema)`),
   point loaders at it, raise a clear error on missing/renamed columns (extends the
   `UTM_X/UTM_Y` checks already present).
4. **A version field is worthless without (a) a migration path and (b) a golden-file
   regression test** per artifact: a fixture of an *old* version that must still load.
   That discipline — not the field — is the real protection.

**Rollout (leverage → effort):** (1) `utilities/schema.py` + registry, migrate the two
D2 artifacts onto it; (2) building JSON + `dialog_config.json`; (3) NetworkGeoJSON schema
version + load validation; (4) CSV column-contracts. Incremental, no big bang. Explicitly
out of scope: ephemeral/interchange artifacts.

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
**Done 2026-06:** A1 (test suite + CI + ruff sweep of the tested tree), B1
(`_04_technology_dialogs` + `osm_dialogs`), C4–C10, D1, D2, D3. The domain core is
now well-tested and lint-clean; the easy low-risk wins there are harvested.

**What's left clusters into untested territory — pick by appetite:**
1. **Test seam for `net_simulation_pandapipes`** (small pandapipes network fixture +
   characterization test). Unlocks C1/C2/C3 *and* the ruff long-tail (48 findings) at
   low risk — the highest-leverage enabler.
2. **C2 — solver error handling** (run_timeseries try/except + NaN/inf/convergence
   checks). Real robustness; needs (1) or careful manual verification.
3. **B1 remainder** — `main_view.py` (~1232); big LOC win but untested GUI god-object.
   (`interactive_network_plot.py` / B3 done 2026-06.)
4. **C1 — threading** audit (worker threads mutate shared state; inconsistent error
   signatures). Subtle; wants a seam too.
5. Quick wins: refresh hardcoded "Variante 1" (D1 leftover), E1 (`.gitignore` casing).
6. Larger/optional: B2 (MVP violations), B4/E2 (DE/EN naming), D4 (serialization
   versioning strategy), widen ruff into `gui/` + flip lint to gating.
