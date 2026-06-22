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
- **Landed 2026-06 (ruff format adopted):** ran `ruff format` over the whole scoped tree
  (src incl. GUI + tests; examples/docs excluded) — **117 files reformatted**,
  behaviour-preserving (`ruff check` clean, 297 passed unchanged). The CI format step is
  now **gating** (`ruff format --check .`, `continue-on-error` removed) over the whole
  tree, not just `tests`. Formatting is no longer a decision — `ruff format` is canonical.
- **Still open:**
  - The CI `lint`/`test` jobs are gating but still **unverified on GitHub** (heavy deps +
    2 git deps; first gating run happens on the next push — expect to tweak the install
    step). Can't be verified locally.

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
- `main_view.py` (~1244) **decomposition in progress (2026-06)**:
  - **Slice 1 (done):** extracted the project/variant filesystem logic into the new
    GUI-free `gui/MainTab/project_structure.py` (`VARIANT_PREFIX`,
    `DEFAULT_VARIANT_NAME`, `discover_variants`). This removed a *triplicated* and
    subtly divergent variant scan — `main_view.get_available_variants` (no sort),
    `main_presenter` (no `isdir` check, arbitrary `variants[0]`), `comparison_tab`
    (sorted) — all three now call `discover_variants`, which is `isdir`-checked and
    **sorted** (so "activate the first variant" is deterministic — a minor, beneficial
    behaviour change for the presenter copy path). The constants moved out of
    `main_data_manager` into the PyQt-free module (re-imported there). First real test
    seam for `main_view`-adjacent logic: `tests/test_project_structure.py` (7 tests).
    All 6 GUI modules import offscreen; 239 passed.
  - **Slice 2 (done):** extracted the project-folder *creation* into
    `project_structure.py` (`PROJECT_INPUT_FOLDERS`, `VARIANT_SUBDIRS`,
    `create_variant_structure`, `create_project_structure`). The variant sub-folder
    list (`Ergebnisse`/`Gebäudedaten`/`Lastgang`/`Wärmenetz`) was **duplicated** across
    `main_presenter.create_new_project` and `create_project_variant`; both now call the
    shared, GUI-free, tmp_path-testable helpers (`create_project_structure` keeps the
    "fail on existing project" behaviour via `os.makedirs` without `exist_ok`). Pinned by
    `tests/test_project_structure.py` (+4 → 11); 280 passed.
  - **Still to tackle:** the bulk of `main_view.py` is genuine Qt glue (menus/tabs/theme/
    dialogs, ~40 methods) with **no behaviour test seam** — extracting it (e.g. a theme
    controller) only *moves* LOC and risks breaking signal/stylesheet wiring that can't be
    regression-tested here. Deliberately left until a GUI behaviour-test harness exists;
    the testable GUI-free logic around it has now been harvested (slices 1+2).
  - **Newly-surfaced god-objects (2026-06-15 audit, OPEN):** three large GUI files are *not*
    in the original B1 list but hold extractable logic — `gui/ProjectTab/project_tab.py`
    (1278 LOC; geocoding/CSV logic duplicated with its worker — see B2),
    `gui/EnergySystemTab/_11_generator_schematic.py` (1264 LOC — its `delete_selected`
    ~~tears down + rebuilds the whole scene, losing manually-dragged layout~~ **fixed 2026-06-17
    (pulled into v2.0.0)**: now removes only the selected component + its linked partner + their
    pipes/label, leaving every other item's position untouched; the full-rebuild path is gone), and
    `gui/ComparisonTab/comparison_tab.py` (1126 LOC). Same caveat as `main_view`: extract the
    GUI-free islands, leave the Qt glue. *The full god-object decompositions stay post-release.*
    - **Move-crash (found + fixed 2026-06-17, pulled into v2.0.0):** dragging a component **froze
      the app and crashed with no error** — `ComponentItem.itemChange` called `self.setPos(value)`
      *inside* the `ItemPositionChange` handler, which re-entered `itemChange` recursively (infinite
      recursion). Fixed by splitting it: `ItemPositionChange` now only snaps to grid (returns the
      value, never calls `setPos`); the pipe/label/connection-point updates moved to
      `ItemPositionHasChanged` (fires after the move, so no recursion). GUI-only, no test seam —
      verified manually in the running app.
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
   - ~~`comparison_tab.update_kpis` inlined the KPI aggregation (filter missing/zero →
     single value / `min`-`max` range / "unavailable") six times next to Qt label-setting.~~
     **Done (2026-06):** extracted the GUI-free `format_kpi_range(variant_data, key, fmt,
     empty=…)`; the view is now a data-driven loop over a `(widget, key, fmt, empty)` spec
     (~70 lines → ~16). Pinned by `tests/test_comparison_kpis.py` (7).
   - ~~`ProjectModel.calculate_centroid` recursed through `self` for a pure geometry
     average.~~ **Done (2026-06):** extracted the GUI-free `centroid_of(coordinates)`
     (point / LineString / Polygon / MultiPolygon); the model method is a thin wrapper.
     Pinned by `tests/test_project_centroid.py` (4).
   - Worker threads (`_06_calculate_energy_system_thread`, `net_calculation_threads`)
     call domain code — more acceptable (off-UI-thread) but still GUI-package
     orchestration. (`run_energy_system_calculation` is now the GUI-free seam — see C1.)
   - *Remaining smaller candidates:* `building_tab.combine_data_with_results` (thin, but
     has an in-place `reset_index` side effect to untangle first) and the
     `KostenBerechnungDialog` cost math (`Σ quantity·spec_cost`, tightly coupled to Qt
     input parsing).
   - ~~*(2026-06-15 audit)* `ProjectModel.create_csv_from_geojson` … duplicated … in
     `GeoJSONToCSVThread.run`~~ **done 2026-06-17 (pulled into v2.0.0)**: extracted the GUI-free
     `geocoding/building_csv.py::geojson_to_building_csv(...)` (reverse-geocoding + CRS transform +
     GeoJSON parsing + CSV write, with optional `progress`/`should_stop` hooks and an injectable
     `geocoder`/`transformer` for testing). `centroid_of` moved there too (re-exported from
     `project_tab` for compat). Both the model method and the worker `run()` are now thin callers;
     pinned by `tests/test_building_csv.py` (5).
   - ~~*(2026-06-15 audit)* config-name↔filename convention duplicated across tabs~~ **done
     2026-06-17**: extracted `gui/EnergySystemTab/config_naming.py`
     (`config_name_to_filename` / `filename_to_config_name`); both tabs import it, so the byte-
     identical `_filename_to_config_name` duplication is gone and both now sanitise identically
     ("A/B" → "A-B" everywhere, not just on save — the comparison tab previously lacked the
     sanitiser). The slash→dash transform is inherently lossy (can't round-trip a `/` in a
     filename), now documented + pinned by `tests/test_config_naming.py` (3). (Pulled into v2.0.0.)
     The `geojson_to_building_csv` extraction above is still open.
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

- **Worker isolation — energy system (done 2026-06).** `CalculateEnergySystemThread`
  mutated the shared `energy_system` in place via `calculate_mix`, so the UI could read
  it mid-run. The compute now runs on a **deep copy** and the main thread swaps the
  result in via `calculation_done` — the producer→swap pattern. Extracted the GUI-free
  `run_energy_system_calculation(energy_system, optimize, weights)` (deep-copies,
  computes, returns the copy) so it is unit-testable without a QThread; the thread is a
  thin wrapper. Pinned by `tests/test_energy_system_thread.py` (input left unmutated).
- **Worker double-start guard — net threads (done 2026-06).** The three
  `NetSimulationTab` workers (init / time-series / recalc) all mutate the shared
  `NetworkGenerationData` (+ its pandapipes net) in place but had **no** double-start
  guard (unlike the energy-system one), so two could run on the same object at once.
  Added `_net_thread_running()` (over the GUI-free `gui/utilities.any_thread_running`,
  duck-typed + unit-tested) and a guard on all three start methods that refuses + warns
  while a run is in flight. Pinned by `tests/test_gui_thread_guard.py`.

*Still open (deliberately deferred):* deep-copying the **pandapipes net** per net run
(full producer→swap isolation for the net side too) — expensive (large nets) and
pandapipes-deepcopy is fiddly, while the race is now bounded by the double-start guard +
the user-initiated, progress-bar-modal nature of the run. Revisit only if a concurrent
read of the net during a recalc is actually observed.
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
No `diameter_m` reads remain in `src` except the intentional one in `net_migration`
(old → new column). C11 is complete. (The 0.14 circ-pump outlet-temperature change was
considered for a 0.13 cross-check but dropped — not worth installing a second
pandapipes version; pandapipes states it does not change the outcome in most cases.)
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
### C14. Result validation accepts physically-impossible negative pressures (fixed 2026-06)
`result_validation.py` checked only for **NaN/inf**, not physical plausibility, so a
pipeflow that "converges" to a *negative absolute pressure* (vacuum/cavitation) passed
every validator silently. **Fixed:** added a *soft* `validate_pressure_plausibility(net)`
(warns via `logging`, returns the offending junction indices, never raises — an
under-pressurized result is a legitimate intermediate planning state the user fixes by
raising the pump pressure / enabling diameter optimization). Wired into `create_network`
after `validate_net_results`. Pinned by `tests/test_net_simulation.py::TestValidatePressurePlausibility`
(7 tests); 246 passed + the slow build test green on the real net.

**Investigation of *why* the warning appeared (dp too high):** the pandapipes
"pressure is negative at nodes […]" warnings on the Görlitz net are **transient**, not
the final state. Mechanism, found by probing the net:
- `init_diameter_types` (called by `create_network`) sizes pipes in a **single pass**
  from one initial pipeflow (`required_d = d·√(v/v_max)`) and picks the **closest**
  std-type via `min(abs(d − required))` — which can **round *down***, leaving pipes
  above `v_max`. On Görlitz that left velocities up to **2.68 m/s** (limit 2.0) on
  DRE20/DRE25 pipes → total `dp` ≈ **23.8 bar** → `run_control` auto-scaled the pump to
  **15.65 bar**; the negative pressures appear in the intermediate solves *before* the
  pump scales. The **final** `res_junction` is already positive (min **2.5 bar**).
- The iterative `optimize_diameter_types` (which actually enforces `v_max`) is **not**
  run by `create_network` / `initialize_geojson` — it's a separate GUI step in
  `net_calculation_threads.py` (gated on `diameter_optimization_pipe_checked`). With it,
  velocities drop to ≤ **1.99 m/s**, `dp` to **12.3 bar**, pump to **9.98 bar**. So the
  golden-master / `initialize_geojson`-only paths see the un-optimized (worse) net.
- **Follow-up (done 2026-06):** `init_diameter_types` now **rounds up** (smallest
  std-type with `inner_diameter_mm ≥ required`) instead of picking the merely closest
  type. On Görlitz this drops max velocity 2.68 → 2.02 m/s, total `dp` 23.8 → 13.4 bar,
  pump head 15.65 → 10.71 bar, and the transient "pressure is negative" warnings go to
  **zero** — the single-pass init state now already satisfies `v ≤ v_max` without relying
  on the GUI-only `optimize_diameter_types`. Golden master regenerated in the same commit
  (`test_simulation_golden_master.py::test_solver_kpis`: Pumpenstrom 0.0054716 → 0.0037649,
  Jahreswärmeerzeugung 6.2590 → 6.2508). `TestNetworkInitialization` pins only invariants,
  unaffected. 246 passed + slow build/golden-master green.
- **Insulation-grade stepping (fixed 2026-06):** `optimize_diameter_types` stepped
  position±1 over the *flat* catalog (`_STD`→`_1x`→`_2x`→next bore), so an UPSIZE could
  change insulation without changing the bore (wasted iterations; arbitrary final
  insulation grade). Now it steps within a **per-grade diameter ladder**
  (`build_diameter_ladders` / `neighbor_std_type`, both unit-tested), so sizing changes
  the bore and keeps the insulation grade constant. On Görlitz the GUI optimize path now
  yields a uniform `_STD` grade (was a mix of `_STD`/`_2x`) at the same hydraulics
  (max v 1.99 m/s, pump 9.98 bar). GUI-only path (not in the golden master); pinned by
  `tests/test_net_simulation.py::TestDiameterLadders` (6 tests). C14 fully closed.

### C15. Pump-pressure / elevation / pipe-cost modelling notes (observations, 2026-06)
Investigating "why does the Görlitz net need ~10 bar pump pressure" surfaced three
modelling facts (no code bugs — design choices / data / missing model):
1. **`v_max` is the dominant driver of pump pressure.** The net is small (9 buildings,
   2.14 MW, ~1171 m trasse) and **flat** (see 2), so the pump head is *pure friction*.
   Sweep (init+optimize, same net):

   | v_max [m/s] | pump p_flow | plift | Σ\|dp\| | max v | pipe material [m·mm] |
   |---|---|---|---|---|---|
   | 1.0 | 4.34 bar | 1.84 | 3.51 | 0.95 | 122 535 |
   | 1.5 | 6.54 bar | 4.04 | 7.32 | 1.49 | 101 366 |
   | 2.0 | 9.98 bar | 7.48 | 12.27 | 1.99 |  92 223 |

   Dropping the **default `v_max=2.0`** to a more typical DH 1.0 m/s cuts the pump
   differential ~75 % (7.48 → 1.84 bar) for ~33 % more pipe material — the classic
   pump-energy vs pipe-capex trade-off. **Update 2026-06-17 (checked for v2.0.0):** this note
   was *stale* — the production defaults are **already 1.0** (`init_diameter_types`
   `v_max_pipe=1.0`, `optimize_diameter_types` `v_max=1.0`, the GUI `dialog_config.json`
   `v_max_pipe=1.0`), lowered during the C14 work; the golden master already reflects 1.0, so no
   regeneration was needed. The only remaining `2.0` was the **unused** `optimize_diameter_parameters`
   (no callers in src/examples/tests) → set to 1.0 for consistency. Going *below* 1.0 would be a
   further modelling decision, not done. (Dead `optimize_diameter_parameters` is a removal candidate.)
2. **Elevation is implemented but the Görlitz example carries none.** The DEM pipeline
   (`net_generation/elevation_utils.py`: GeoTIFF or OpenTopoData API → Z-coords →
   `height_m` → geodetic head in pandapipes) is fully wired via the `dem_path` arg of
   `generate_and_export_layers`. But `…/Görlitz/Variante 1/Wärmenetz/Wärmenetz.geojson`
   is **2-D** (all `height_m = 0`), so terrain is ignored in its hydraulics. Real nets
   with relief must be (re)generated with a DEM or internet (API fallback) — otherwise
   the geodetic pressure component is silently absent. Data gotcha, not a bug.
3. **No per-diameter pipe/trasse cost model.** Diameter optimization is purely
   *velocity*-driven; there is no €/m-by-diameter cost anywhere in `net_*`, so the tool
   cannot cost the v_max trade-off above (trasse cost is a lump infrastructure input in
   `_05_cost_tab`). A diameter→€/m table would let the optimizer (and the user) trade
   pump energy against pipe capex properly. Possible future feature.

### C16. Energy-system optimizer has no demand-coverage constraint (verified + fixed 2026-06-16)
**Was a pre-release blocker.** `EnergySystemOptimizer.optimize` called
`scipy_minimize(objective_function, …, method="SLSQP", bounds=bounds, …)` with **only
`bounds` — no `constraints` and no unmet-demand penalty**. The objective was the pure weighted
sum `WGK_Gesamt + specific_emissions_Gesamt + primärenergiefaktor_Gesamt`, all three minimized
by *shrinking* generator capacities: less generation → the uncovered load lands in the
cost-free "Ungedeckter Bedarf" row → every term (divided by the full `Jahreswärmebedarf`) falls
toward 0. Structurally biased toward undersized/empty systems.
- **Verified (2026-06-16) before changing the model.** Direct objective probe of a CHP-only
  system across capacities: WGK/emissions/PEF all fall monotonically as the CHP shrinks (CHP=10 kW
  → WGK 5.3, only 4.4 % of demand covered), and reach **0** at a capacity so large the CHP never
  runs (min_Teillast). A seeded real SLSQP run (start 300 kW, bounds 0–1000) optimized to **0.00 kW
  / 0 % coverage / objective 0** — the optimizer literally optimized the system out of existence.
- **Fixed (penalty approach, Jonas's call).** Added `unmet_demand_penalty` (constructor +
  `optimize_mix` param, default **1e6**); the objective now adds
  `unmet_demand_penalty · max(Restwärmebedarf, 0)/Jahreswärmebedarf`. Proportional to the uncovered
  *fraction*, so it stays well-defined when full coverage is physically impossible (minimises the
  gap, then cost). Re-verified seeded: CHP-only → **296.8 kW / 67.4 %** (max achievable with one
  CHP); CHP+GasBoiler → CHP **128.7 kW / 100 %** covered. Pinned by
  `tests/test_energy_system.py::TestOptimizerCoverage` (seeded; asserts capacity > 50 kW and
  coverage > 50 %, ranges not exact values — SLSQP/platform drift). 71 domain-core tests green.
- ~~*POST-RELEASE follow-up:* the SLSQP random restarts draw from the global unseeded `np.random`~~
  **done 2026-06-17**: `EnergySystemOptimizer`/`optimize_mix` take an optional `seed` and the restarts
  now draw from a local `np.random.default_rng(seed)` (no global side effect; `seed=None` stays
  non-deterministic). `optimize_mix` is now reproducible — pinned by
  `TestOptimizerCoverage::test_seed_makes_optimization_reproducible` (and the coverage test uses
  `seed=42` instead of seeding the global RNG). (Pulled into v2.0.0.)

### C17. Heat-pump electricity overstated at part load → wrong emissions/WGK (fixed 2026-06-16)
Two HP techs did not rescale electricity to the capped heat output (both were untested):
- **`RiverHeatPump.calculate_operation` (fixed).** It capped
  `Wärmeleistung_kW = min(Last_L, Wärmeleistung_FW_WP)` but took
  `el_Leistung_kW`/`Kühlleistung_kW` from `calculate_heat_pump` at the **full nominal**
  capacity and never rescaled, so at load < nominal `Strommenge_MWh`, CO₂, primary energy
  and WGK were overstated. Now, on the operating mask,
  `el_Leistung_kW = Wärmeleistung_kW / COP` and the river extraction follows the energy
  balance `Kühlleistung_kW = Wärmeleistung_kW − el_Leistung_kW`. (The per-timestep
  `generate()` path delivers full nominal heat, so it was already consistent — no change.)
- **`Geothermal.generate` (fixed).** It wrote the **extraction** power into the electricity
  array: `el_Leistung_kW[t] = Wärmeleistung_kW[t] − (Wärmeleistung_kW[t]/Wärmeleistung)·el_Leistung`
  reduced (since `Wärmeleistung_kW[t] == Wärmeleistung` here) to `Wärmeleistung − el_Leistung
  = Entzugsleistung`, not the electrical power. Now `el_Leistung_kW[t] = Wärmeleistung_kW[t]
  / COP[t]` (the dead `el_Leistung` local was removed). The bulk `calculate_operation` path
  was already correct.
- **Tests:** `tests/test_heat_generators.py::TestRiverHeatPumpPartLoad` (el scales to the
  capped output; energy balance Q = extraction + el) and `::TestGeothermalElectricity`
  (generate reports electrical, not extraction, power), both built on a small deterministic
  COP grid (`_COP_GRID`, interpolates to COP 4.0). 13 heat-generator tests green; ruff clean.
- *POST-RELEASE:* `calculate_COP` silently clamps the required flow temperature to
  source+75 K (`base_heat_pumps.py:118`) and zeros the COP out of table bounds (`:140-148`,
  `print` not `logging`) — warn/flag instead of silently clamping.
- ~~*POST-RELEASE (found 2026-06-16):* `Geothermal.generate`/`RiverHeatPump.generate` pass
  **scalar** `VLT` into the array-shaped `calculate_COP` → NumPy `DeprecationWarning`~~ **fixed
  2026-06-17**: both `generate()` paths now pass the scalar as `np.atleast_1d(VLT)` and take `[0]`,
  so the "ndim > 0 to scalar" deprecation is gone (it would have become an error on a future
  NumPy). Pinned by running `TestGeothermalElectricity`/`TestRiverHeatPumpPartLoad` with the
  deprecation promoted to an error. (Pulled into v2.0.0.) *(The 75 K clamp warning above stays
  post-release.)*

### C18. `QClipboard()` instantiated directly → copy/paste buttons dead (fixed 2026-06-16)
`layer_generation_dialog.py:594` and `:607` did `clipboard = QClipboard()`; `QClipboard`
has no public constructor in PyQt6 (`TypeError: … cannot be instantiated`), so the
"Koordinaten kopieren/einfügen" buttons raised on click — the feature was dead.
**Fixed:** both sites now use `QApplication.clipboard()` (the canonical singleton accessor);
the unused `from PyQt6.QtGui import QClipboard` import was dropped and `QApplication` added
to the QtWidgets import. Verified: module imports offscreen, ruff check + format clean.
(Qt-glue with no behaviour-test seam — smoke-import + lint, as for the other GUI fixes.)

### C19. ProjectTab geocoding handler/signal mismatch → no auto-reload (fixed 2026-06-16)
`GeocodingThread.calculation_done` is `pyqtSignal(object)` and emits the tuple
`(self.inputfilename, result_dict)` (`gui/LeafletTab/net_generation_threads.py:247,276`;
`process_data` returns a dict, `geocoding/geocoding.py:55`), and the LeafletTab handler
unpacks it. But ProjectTab's `on_geocode_done(self, fname)`
(`gui/ProjectTab/project_tab.py:730`) treated the whole tuple as a path →
`os.path.exists(tuple)` raised `TypeError` (swallowed by Qt). After "Geokoordinaten
berechnen" the table was never reloaded and no success message showed (the CSV *was*
written). **Fixed:** `on_geocode_done(self, result)` now unpacks `fname, _summary = result`
(mirroring `leaflet_tab.on_geocode_done`) before the reload. Verified: module imports
offscreen, ruff check + format clean. (Same Qt-glue caveat as C18.)

### C20. `preprocessData` UnboundLocalError if the main feed pump isn't named exactly (fixed 2026-06-16)
Same class as fixed C6. In `_01_energy_system_main_tab.py:506-508`,
`flow_temp_circ_pump`/`return_temp_circ_pump` were assigned only inside
`if pump_type == "Heizentrale Haupteinspeisung"`, then used unconditionally to build
`EnergySystem`. A results CSV without that exact key (renamed feed, multi-producer net) →
`UnboundLocalError`. **Fixed:** both are initialised to `None` before the loop; if no main
feed is found, `preprocessData` raises a clear `ValueError` naming the CSV. The call site in
`start_calculation` now wraps `preprocessData()` in `try/except (ValueError, KeyError)` and
surfaces the message via `QMessageBox.warning` + `return` (no crash, no orphaned thread).
Verified: module imports offscreen, ruff check + format clean. (GUI orchestration with no
behaviour-test seam.)

### C21. Domain robustness edges in EnergySystem (fixed 2026-06-16)
GUI-free domain-core edge cases that used to fail silently or opaquely. All three fixed +
unit-tested:
- **Single-timestep duration (fixed).** `EnergySystem.duration = (np.diff(time_steps[:2]) /
  np.timedelta64(1,"h"))[0]` raised `IndexError` for a single-timestep profile (empty
  `np.diff`). Now guarded by `len(self.time_steps) >= 2`, falling back to `1.0` h (hourly
  resolution) instead of crashing in `__init__`.
- **Zero-demand guard (fixed).** `aggregate_results` divides every share/WGK/emissions term
  by `results["Jahreswärmebedarf"]`, which is 0 for an all-zero/empty load profile → the whole
  result set went NaN/inf silently. `calculate_mix` now raises a clear `ValueError` right after
  `initialize_results()` when `Jahreswärmebedarf <= 0`.
- **Cost sentinels unified + CHP `None` fall-through (fixed).** The zero-Wärmemenge sentinel
  is now `inf` in `chp.py`/`biomass_boiler.py`/`solar_thermal.py` (was `0`), matching
  GasBoiler/PowerToHeat/storage so an idle generator never shows a misleading `0` WGK. (Safe:
  the `WGK_Gesamt` aggregation in `aggregate_results:231` is gated on `Wärmemenge > 1e-6`, so
  the sentinel only affects the per-tech display record, not the system total — golden masters
  unchanged.) CHP's `calculate_heat_generation_costs` used to fall off the end returning `None`
  when `self.BEW` was neither `"Ja"` nor `"Nein"` (`chp.py:361-364`) → `None` flowed into WGK;
  now an `else: raise ValueError`.
- **Tests:** `tests/test_energy_system.py::TestEnergySystemRobustness` (single-step duration,
  zero-demand raise) + `tests/test_heat_generators.py::TestCHP` (`test_invalid_bew_raises`,
  `test_zero_heat_amount_cost_is_inf`). 68 domain-core tests green.

### C22. `QThread.terminate()` can corrupt the in-flight geocoding CSV (restart sites fixed 2026-06-16; OSM-cancel left)
**Severity: pre-release — C1 leftover.** Restarting geocoding/generation called `terminate()`
+ `wait()`. `QThread.terminate()` kills the thread at an arbitrary point — it can abort
mid-write of the geocoded CSV / generated output, leaving a truncated file. C1 moved other
threads to cooperative `stop()`/`isInterruptionRequested()`; these sites still hard-terminated.
**Fixed (the three restart sites):** `gui/ProjectTab/project_tab.py:722` and
`gui/LeafletTab/leaflet_tab.py:388,623` now call the cooperative `stop()` the threads already
define (`GeocodingThread.stop`, `NetGenerationThread.stop` — `requestInterruption()` + `wait()`).
The blocking `run()` doesn't poll `isInterruptionRequested()`, so `stop()` simply *waits* for the
current run to finish writing cleanly before the new one starts — the right "restart" semantics
and no mid-write kill. Verified: both modules import offscreen, ruff clean.
**Left (deliberately): `osm_dialogs_base.py:155` (`_onDownloadCanceled`).** This is a genuinely
different case: (1) it is a user *cancel*, not a restart, so a cooperative `stop()` that *waits*
would freeze the UI for the whole in-flight osmnx/Overpass download; (2) the OSM download threads
(`OSMStreetDownloadThread`/`OSMBuildingDownloadThread`) have **no** interruption seam — `run()` is
a single blocking `download_func(...)` call that can't poll for cancellation; (3) the corruption-
safe "detach + let it finish in the background" pattern risks a *"QThread destroyed while running"*
crash if the dialog's thread ref is reassigned. Every option (terminate=corrupt, wait=freeze,
detach=GC-crash) has a real downside and there is no GUI behaviour-test seam to verify the fix.
Correct fix needs a small refactor (write the download to a temp path + atomic rename on success,
so a killed/abandoned download never leaves a consumable partial file) — post-release, with the
other `net_generation_threads.py` thread-audit work (C9 follow-up).

### C23. Pipe-type UI: KMR residue, non-ISOPLUS clutter, wheel-scroll, no change cue (fixed 2026-06-18)
Four issues around the pipe-type selectors, all user-reported and fixed for v2.0.0:
- **KMR material filter (C11 residue).** `dialog_config.json` still had
  `diameter_optimization.material_filter = ["KMR", "FL", "HK"]`, so "Wärmenetz generieren" defaulted
  to `material_filter="KMR"` → `init_diameter_types` filtered the std-types to the (now non-existent)
  KMR material → `ValueError: No standard pipe types found for material filter: KMR`. Set to
  `["P235GH/PUR/PEHD"]` (the ISOPLUS material).
- **Only ISOPLUS pipes selectable.** The initial-pipe combo (`network_config_tab.py`) and the pipe
  table (`pipe_config_table.py`) listed *all* pandapipes std-types (gas/water utility pipes too).
  New `pipe_std_types.isoplus_std_type_names(df)` (filters by the `material` column, falls back to the
  `ISOPLUS` name prefix; unit-tested) now feeds both selectors.
- **Wheel-scroll changed the selection.** Scrolling while hovering a combo cycled its value. New
  `gui/utilities.NoScrollComboBox` ignores wheel events (the table/page scrolls instead; value still
  changes via click); used for the table + initial-pipe combos.
- **No change cue.** Pipe rows whose std-type/DN/k were edited since the last calculation are now
  tinted (`_capture_baseline` at each `_fill_table`; `_update_row_highlight` on edit; cleared on the
  next calculation). GUI-only — verified by the helper test + manual GUI run.

### C24. OSM highway filter missed `unclassified` / `track` streets (fixed 2026-06-18)
The street-download UI only offered 6 highway types (`primary|secondary|tertiary|residential|
living_street|service`), so streets tagged `unclassified` (a normal minor public road, very common
in villages) or `track` were silently dropped. Verified live against **Ödernitz** (Niesky): the
Helmut-Just-Straße and Brunnenstraße have `unclassified` segments, and Apfelallee/Wilhelminenthal
are fully `unclassified` — all were missing; Ullersdorfer Straße is a `track`. **Fixed:** added
`unclassified` and `track` to the offered highway types in both dialogs (`osm_dialogs.py`,
`layer_generation_dialog.py`) and to the default filter strings, in **both** download paths — the
OSMnx custom-filter and the direct Overpass tag query (`examples/02`). `unclassified` is checked by
default; `track` is offered but **off** by default (most tracks are field/forest paths without
buildings). Pinned by `tests/test_osm_dialogs.py::TestHighwayFilter` (offered + default state).

## D. State & data
### D1. Double state source (fixed 2026-06)
`try_filename`/`cop_filename` lived in both `DataManager` and `ProjectFolderManager`,
mirrored by hand in `main_view` (and slightly buggy: raw vs project-copied path).
**Fixed**: `ProjectFolderManager` is now the single owner (it persists them in
`project_settings.json`); `DataManager` holds only `map_data`; the three consumer
tabs read `folder_manager.try_filename/.cop_filename` (they already held the ref).
Pinned indirectly by `tests/test_project_settings.py`. *Variant-name leftover fixed
2026-06:* the variant folder name was hardcoded as the literal `"Variante 1"` / the
prefix `"Variante"` across 6 GUI files (creation, default, detection, sequential
naming) — drift between the default name and the `startswith("Variante")` detection
was a latent bug. Centralized into `main_data_manager.DEFAULT_VARIANT_NAME` /
`VARIANT_PREFIX` (the `ProjectFolderManager` module, a leaf so no import cycle);
`main_presenter`, `main_view`, `comparison_tab`, `project_tab`, `welcome_screen` now
import them. Behaviour-identical (all 6 modules import offscreen; 232 passed). UI
strings like "Variantenvergleich" and the `__main__` demo path in `building_tab` are
left as-is.
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
- **Won't do (deliberate, 2026-06):** the remaining temperature limits (e.g. the 75 K
  Hub) and `cp=4187 J/kgK` in `thermal_storage.py` (different unit system) stay as-is.
  Jonas's call — not worth the churn/risk for no behavioural gain. D3 is considered
  closed.
### D4. Project-wide serialization/versioning strategy (done 2026-06)
D2 versioned only two artifacts (`project_settings.json`, EnergySystem JSON). The app
reads/writes **many** serialized files of different kinds, and most are unversioned.
A blanket "add a version field everywhere" is wrong — the strategy must be
differentiated by artifact kind.

**Step 1 landed (2026-06):** `utilities/schema.py` (GUI-free, stdlib-only — safe for the
domain core, B5) holds the shared bookkeeping: a `SCHEMA_VERSIONS` registry (single
source of truth, replaced the scattered `*_VERSION` constants), `add_meta(data, kind)`
(writes a `_meta` block with `schema_version` + diagnostic `app_version`),
`schema_version_of` (tolerant read: `_meta` → legacy top-level `version` → 0) and
`check_version` (warns if newer than the app). `project_settings.json` and the
EnergySystem JSON now route save/load through it; old files (legacy top-level `version`
*and* pre-versioning) still load — pinned by `tests/test_schema.py` (8) plus
backward-compat cases in `test_project_settings.py` / `test_energy_system.py`. 262 passed.

**Step 2 landed (2026-06):** routed the building combined-data JSON
(`BuildingTab/building_tab.py::BuildingModel.save_json`/`load_json`) and
`dialog_config.json` (`NetSimulationTab/net_generation_dialog.py`) through the same
helper (registry kinds `building_data`, `dialog_config`). The `_meta` block is skipped
by the building loader's existing `'wärme'` filter and ignored by the dialog tabs (which
read config by key); legacy/pre-versioning files of both kinds still load. Pinned by
`tests/test_artifact_versioning.py` (4). 266 passed.

**Step 3 landed (2026-06):** the network GeoJSON already embedded its version as
`metadata.version` (a semver *string*, e.g. `"2.0"` — its own convention, kept distinct
from the int `_meta` registry since a FeatureCollection carries metadata inline). Added
the missing **load validation**: `NetworkGeoJSONSchema.validate_version` warns (soft) on
a missing or newer-major version and is called from `import_from_file` (the GUI load
path — `project_tab`, `_02_energy_system_dialogs`). *Note:* the simulation path
(`initialize_geojson`) reads geometry via `gpd.read_file`, which drops the top-level
`metadata` member, so it never sees the version — out of scope here. Pinned by
`tests/test_net_generation.py::TestNetworkGeoJSONVersion` (4). 270 passed.

**Step 4 landed (2026-06):** CSV column-contracts. New `utilities/csv_schemas.py`
(GUI-/pandas-free at import) centralizes the required columns per CSV kind
(`building` — the 8 demand/profile columns; `coordinates` — `UTM_X`/`UTM_Y`) with
`validate_csv_columns(df, kind)` raising a `KeyError` that names *every* missing column
up front. Wired into `import_and_create_layers` (generalized the ad-hoc UTM check,
preserving the `KeyError` the caller already catches) and
`heat_requirement_calculation_csv.generate_profiles_from_csv` (turns the opaque
mid-calculation `KeyError` into a clear up-front one). No version field — the header
*is* the contract (a version row would break pandas/Excel interop), as planned. Pinned
by `tests/test_csv_schemas.py` (6); example 03 still runs on the real CSV. 276 passed.
**D4 complete.**

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

**Rollout (leverage → effort):** ~~(1) `utilities/schema.py` + registry, migrate the two
D2 artifacts onto it~~ **done**; ~~(2) building JSON + `dialog_config.json`~~ **done**;
~~(3) NetworkGeoJSON schema version + load validation~~ **done**;
~~(4) CSV column-contracts~~ **done 2026-06**. Explicitly out of scope:
ephemeral/interchange artifacts. **All four steps landed — D4 complete.**

## E. Hygiene
### E1. `.gitignore` casing (resolved 2026-06)
The build-logs ignore entry is now lowercase `build_logs/` (`.gitignore:162`), which
matches on case-sensitive Linux/CI — the earlier capital-L concern no longer applies.
(No code path actually creates a build-logs dir, so the entry is vestigial but
harmless.) The earlier `error_log.txt` flag was a non-issue — it was never tracked,
only ignored. The 52 MB Görlitz example project is large but acceptable. Nothing to do.
### E2. Naming/method-name inconsistencies
Same root cause as B4.
### E3. Cross-platform & defensive-coding hygiene (partially fixed 2026-06-17)
**Severity: post-release (Windows-first app; bites Linux/CI dev).**
- ~~Hardcoded backslashes in `gui/ProjectTab/project_tab.py` (`required_files` +
  `os.path.join(base_path, "Wärmenetz\\Wärmenetz.geojson")`)~~ — **fixed 2026-06-17**: all the
  `required_files` literals and the two `Wärmenetz\\Wärmenetz.geojson` sites now use forward
  slashes (portable on both Windows and POSIX), so the progress tracker / dimensioned-network
  check work on Linux/CI. (Pulled into v2.0.0.)
- ~~Broad `except Exception: pass` swallowers~~ **fixed 2026-06-17 (pulled into v2.0.0)**: the
  silent swallowers in `project_tab.py` (CSV-status → masked a corrupt/locked CSV as "ist
  vorhanden"; network-dimensioned read; CRS auto-suggest; CSV fast-path probe; sample-coord
  extraction) and `comparison_tab.py` (`update_kpis`, `update_charts`, variant network-KPI read)
  now `logging.warning`/`logging.debug` the exception (file/parse ones narrowed to
  `OSError`/`csv.Error`/`json.JSONDecodeError`/`ValueError`/`KeyError`; best-effort ones kept broad
  but logged at debug). `import logging` added to both files.
- **Hardcoded backslashes in `examples/` paths (CI-relevant subset fixed 2026-06-16).** A
  literal `"examples\\data\\TRY\\…"` in `examples/14_example_photovoltaics.py` failed the gating
  `test_examples_smoke.py` on Linux CI (`FileNotFoundError` — `\` is not a separator on POSIX).
  Fixed to forward slashes (the convention in 08/09/10/18_stanet). **Still backslashed (not in the
  smoke set, so not CI-gated — fix when touched):** `20_leaflet_test.py:53` (Qt, excluded),
  `benchmark_synthetic_net_generation.py:16-18,74` and `generate_synthetic_gis_data.py:95,98-100`
  (dev/benchmark scripts). Forward slashes work on Windows too — no `os.path.join` churn needed.

## F. Release readiness & distribution (2026-06-15 audit)
The mechanics of actually shipping a clean release. None of these are A–E code debt; they
gate the release itself.
### F1. Two git dependencies block PyPI distribution (decided 2026-06-16)
`pyproject.toml:27-28` pulls `pyslpheat` and `thermal-energy-storage-1d` via `@ git+https://…`.
PyPI rejects any distribution whose metadata carries a direct (`git+`) URL, so
`pip install districtheatingsim` from PyPI is impossible as-is; only the source/git-URL install
works (and silently requires `git`). **Decision (Jonas, 2026-06-16): GitHub-source /
PyInstaller-exe only — no PyPI for now** (the two deps stay unpublished). The `git+` deps stay
as-is (fine for `pip install git+…` / `pip install .` / editable). Consequences: keep the install
docs on the GitHub/git-URL path and drop any bare `pip install districtheatingsim` PyPI hint
(F5: `index.rst:91`). Revisit only if PyPI distribution is wanted later (then publish both deps).
### F2. No console/GUI entry point (fixed 2026-06-16)
There was no `[project.scripts]`/`[project.gui-scripts]` in `pyproject.toml`; after `pip install`
there was no `districtheatingsim` command (only `python -m districtheatingsim`). The README told
users to run the in-tree `DistrictHeatingSim.py`, which doesn't exist for a pip install.
**Fixed:** added `[project.gui-scripts]` `districtheatingsim = "districtheatingsim.DistrictHeatingSim:main"`
and updated the two README run instructions to the `districtheatingsim` command (`python -m
districtheatingsim` as the equivalent). Verified: `pip install -e .` registers the
`districtheatingsim` executable (`shutil.which` resolves it); the entry-point target imports +
is callable; pyproject parses. (`gui-scripts` rather than `scripts` so the Windows launcher opens
no console window.)
### F3. Empty CHANGELOG + version bump (done 2026-06-16)
`CHANGELOG.md` `[Unreleased]` was empty despite 114 commits since `v1.0.3`. **Done:** wrote the
full release section from the git log + the "landed" notes (Added/Changed/Fixed/Refactored/
Testing), with the pandapipes 0.13→0.14 migration flagged **BREAKING**. **Bumped 1.0.3 → 2.0.0**
(major, Jonas's call — the pandapipes break + forced old-project migration) at all four sites
(`pyproject.toml`, `__init__.py`, `docs/source/conf.py` release+version, and the stale **1.0.0**
badge in `docs/source/index.rst`); the CHANGELOG header is now `[2.0.0] - 2026-06-16` with a fresh
empty `[Unreleased]`. Verified: all four sites read 2.0.0 and `districtheatingsim.__version__`
imports as `2.0.0`. (The bare `pip install districtheatingsim` in `index.rst:91` is left to F5.)
### F4. CI now gating but the run status is unconfirmed
**Severity: pre-release.** `HEAD == origin/main == b03bf77` — everything is pushed, so the
gating `ci.yml` (pytest 3.11/3.12 + `ruff check` + `ruff format --check`) triggered on the
last push. The earlier CLAUDE.md/BACKLOG note "main is ahead of origin / CI never run" is
**stale** and should be corrected. The risky step is `pip install -e .[dev]` (2 git clones +
heavy scientific stack on Ubuntu). Check the GitHub Actions result for `b03bf77`; if red, fix
before tagging. (`rasterio`/elevation extra is *not* a CI failure point — imported lazily,
not at test-collection time.)
### F5. Docs sweep (done 2026-06-16)
Prose docs (`thermal_storage.rst`, README) were already current (no KMR/STES residue — verified
by a stale-term sweep). The rot was in the **hand-maintained autodoc stubs**, which missed every
module added during the refactors. **Done** — added the missing `automodule` blocks (rather than a
blanket `sphinx-apidoc -f`, which would clobber the curated prose pages): `heat_generators.{results,
json_encoder}`, `constants` (→ `districtheatingsim.rst`), `net_simulation_pandapipes.{net_migration,
pipe_std_types,plot_data,result_validation}`, `utilities.{csv_schemas,schema}`, `osm.area_selection`,
`net_generation.elevation_utils`, and the whole `technology_dialogs/` package (`_base`/`_schemas`/
`_dispatcher`/`_simple`/`_combustion`/`_solar`/`_geothermal`/`_heat_pump`/`_storage`) alongside the
`_04_technology_dialogs` façade in the EnergySystemTab stub. Also fixed the **1.0.0 → 2.0.0** badge
(F3) and the install/run instructions in `index.rst` (bare `pip install districtheatingsim` → the
git URL; in-tree `DistrictHeatingSim.py` → the `districtheatingsim` entry point). **Verified:**
`sphinx -b html` builds (exit 0); all 12 new modules render into the HTML; the remaining build
warnings are **pre-existing** docstring-formatting issues (math notation / indentation in
`osmnx_steiner_network`, `controllers`, `thermal_storage`, the `*_error` pyqtSignal docstrings) —
*not* introduced here, logged below as a post-release cleanup.
- *POST-RELEASE:* clean the pre-existing autodoc docstring warnings (reST `|x|` substitutions read
  as undefined in `osmnx_steiner_network.create_steiner_tree` / `controllers.*.is_converged`,
  "Inline emphasis" in the `calculation_error`/`download_error` signal docstrings, "Unexpected
  indentation" in `thermal_storage.current_storage_temperatures`).
### F6. PyInstaller build + specs reviewed and reorganised (build run still pending — 2026-06-16)
**Severity: pre-release (the chosen distribution channel — see F1).** With PyPI off the table the
**PyInstaller exe is the primary user-facing artifact**, but the six build files had not been
revisited since the 2026-06 refactors. Reviewed all six; **fixed the real bugs and deduplicated**:
- **🔴 pyslpheat data was missing from the build (real bug, fixed).** `pyslpheat` ships `data/`
  (BDEW/VDI profile CSVs, TRY files) + `images/` that PyInstaller's import-following does **not**
  collect — the frozen exe's heat-demand calc would have failed at runtime. The specs now call
  `collect_data_files('pyslpheat')` + `collect_data_files('thermal_energy_storage_model')` (the
  real import name of `thermal-energy-storage-1d`). Verified: `get_datas()` pulls **30** pyslpheat
  entries incl. `bdew/hourly_coefficients.csv`, the VDI 4655 load profiles and TRY `.dat` files.
- **🔴 cp1252 console crash (C13 class, fixed).** `build.py`/`build_debug.py` printed `✓✗⚠ℹ→` →
  `UnicodeEncodeError` on a fresh Windows console. Now `build_common.configure_utf8_stdout()` +
  ASCII markers (`[OK]`/`[WARN]`/`[FAIL]`/`[INFO]`).
- **🔴 wrong exe path** in `build_debug.py` (`dist/DistrictHeatingSim.exe` → `dist/DistrictHeatingSim/…`).
- **🟠 deduplicated.** The two specs were ~95% identical and `build.py`/`build_debug.py` duplicated
  the cleanup/move helpers verbatim. New **`spec_common.py`** (shared `datas`/`hiddenimports`/excludes,
  the data collection, OS-agnostic entry path) imported by both specs; new **`build_common.py`**
  (UTF-8 setup, `run_pyinstaller`, cleanup, `move_user_data_outside`, `post_build`) used by both thin
  scripts.
- **🟠 dead code removed.** The `datas_inside/outside_internal` split in both specs partitioned
  `a.datas` then concatenated it straight back — a no-op (the real "move outside" is the post-build
  step). Replaced with `COLLECT(exe, a.binaries, a.datas, …)`. Also dropped the vestigial
  `numpy_financial` hiddenimport (its only consumers, `renovation_analysis`/`SanierungsanalysefuerGUI`,
  no longer exist) and the leftover verbose `('v',…)` EXE option from the **release** spec.
- **🟡 guide rewritten.** `PYINSTALLER_BUILD_GUIDE_EN.md` was stale (referenced a non-existent
  `requirements.txt`, "188 MB" Görlitz (actually ~55 MB), two conflicting PyInstaller-version footers,
  and a `run_debug.bat` that didn't match the actual file — the real one *runs* the built exe, it is
  not a build launcher). Rewritten to the reorganised layout.
All new/changed Python modules import clean + ruff check/format clean.

**Build run done (2026-06-17) — three runtime crashes found + fixed:**
- **numpy 2.x not fully bundled.** The frozen exe crashed at startup with
  `ModuleNotFoundError: No module named 'numpy._core._exceptions'` — PyInstaller 6.5.0 (released
  before numpy 2.0) ships a stale numpy hook that misses the `numpy._core` submodules of numpy 2.3.5.
  Fixed: `HIDDENIMPORTS += collect_submodules("numpy")` in `spec_common.py`. (A newer PyInstaller +
  pyinstaller-hooks-contrib would also fix it.)
- **thermal-energy-storage-1d editable install not bundled.** Next crash:
  `ImportError: cannot import name 'ConstantAmbientLoss' from 'thermal_energy_storage_model'
  (unknown location)`. The dep is installed **editable** (PEP 660, at `C:\Users\jonas\thermal-energy-
  storage-1d`); PyInstaller can't resolve its custom import finder, so it bundled only `py.typed`.
  `collect_submodules` returned the names but PyInstaller still couldn't find the source. Fixed by
  copying the whole package dir in as **data** (`get_datas()` → `(_tes_dir, "thermal_energy_storage_model")`),
  so its modules are importable from `_internal`. (pyslpheat is a normal site-packages install and was
  bundled fine — modules + its data via `collect_data_files`.)
- **UPX disabled.** Set `upx=False` in both specs — UPX wasn't installed (harmless "UPX is not
  available" log line) and UPX-packed exes frequently trip Windows Defender/AV false positives, so off
  is the right default for a distributed exe.
After these, the debug exe **starts and runs** (reaches the Qt event loop, no import errors). Verified
in the real build: `_internal/pyslpheat/data/bdew/*.csv` + VDI profiles bundled, all new domain modules
present, `_internal/thermal_energy_storage_model/{__init__,losses,…}.py` present.
**STILL PENDING — the manual GUI functional test** (Windows-only, Jonas): launch, create/load a project,
run a net + an energy-system calc end-to-end. *Note:* the debug build's verbose-import EXE option
(`('v',…)`) makes a headless/piped launch crawl — irrelevant to the no-console release build.
Backslash entry path is now OS-agnostic (`os.path.join`), though the build remains Windows-only.

### F7. Read the Docs build broken — config referenced removed requirements files (fixed 2026-06-22)
**Severity: pre-release (the public docs site `districtheatingsim.readthedocs.io` had not built in a
while).** RTD failed at `pip install … -r requirements.txt` (exit 1): the `pyproject.toml` migration
(`d6f105a`) deleted both `requirements.txt` and `documentation_requirements.txt`, but `.readthedocs.yaml`
still pointed at them. **Fixed:** `.readthedocs.yaml` now installs the package with its `[docs]` extra
straight from `pyproject.toml` (`method: pip` / `path: .` / `extra_requirements: [docs]`) — single
source of truth, no standalone requirements files.
- **Full runtime install is deliberate, not mocking.** autodoc imports the real modules, and the
  codebase uses PEP 604 unions in runtime-evaluated annotations (e.g.
  `base_heat_generator.get_plot_data -> dict[str, list | np.ndarray]`, `utilities.py:140`,
  `LineString | None`). A docs-only + `autodoc_mock_imports` build was prototyped and **rejected**: it
  crashed the import of ~40 modules (the whole `heat_generators` domain core cascades off
  `base_heat_generator.py:163`) because `list | <Mock>` raises `TypeError` at function-definition time.
  Salvaging it would need `from __future__ import annotations` across the domain core, which
  `NetworkDataClass` blocks (it reads `cls.__annotations__` at runtime, lines 453/472/476).
- **Verified** in a clean venv with the full runtime: `sphinx -b html` → exit 0, **0 autodoc import
  failures**, all modules render. Residual warnings are the **pre-existing** cosmetic docstring/reST
  nits already logged under F5 POST-RELEASE, plus the deprecated `display_version` sphinx_rtd_theme
  option in `conf.py` (one line, harmless).

---

## Suggested order
**Done 2026-06:** A1 (test suite + CI + full ruff sweep incl. GUI, gating), B1
(`_04_technology_dialogs`, `osm_dialogs`, `interactive_network_plot`/B3), B5, C2
(solver error handling + the `net_simulation_pandapipes` test seam,
`TestNetworkInitialization`), C3–C13, D1, D2, D3. The domain core + the simulation
pipeline are now well-tested and lint-clean; the easy low-risk wins are harvested.

**The 2026-06 cluster (C14, threading isolation, quick wins, D4) is cleared.** A ground-up
re-audit on **2026-06-15** found the remaining work splits cleanly into *before* the planned
clean release and *after* (Weiterentwicklung). Most A–E debt is closed; what's left is
concentrated in newly-found correctness bugs in the un-refactored modules (C16–C22) and the
release mechanics themselves (section F). See the **Release plan** below.

## Release plan (2026-06-15 audit)

### Before the new release
**Correctness bugs (all verified at file:line on 2026-06-15):**
1. ~~**C18 / C19** — quick wins: `QClipboard()` dead buttons; ProjectTab geocode handler
   mismatch (no auto-reload).~~ **Done 2026-06-16.**
2. ~~**C20 / C21 / C22** — `preprocessData` UnboundLocalError (C6 class); EnergySystem
   robustness edges (1-step duration, zero-demand NaN, cost sentinels/None);
   `QThread.terminate()` CSV corruption.~~ **Done 2026-06-16** (C22: the 3 restart sites;
   the OSM-download *cancel* in `osm_dialogs_base` is carved out to post-release — see C22).
3. ~~**C17** — river/geothermal HP electricity overstated at part load (untested → fix + test).~~
   **Done 2026-06-16.**
4. ~~**C16** — optimizer has no coverage constraint. Highest value, but **verify against a
   real run first** before touching the model.~~ **Verified + fixed 2026-06-16** (unmet-demand
   penalty, default 1e6; the collapse was confirmed against a real seeded run first).

**Release mechanics (section F):**
5. ~~**F1** — decide the distribution model (2 git deps block PyPI).~~ **Decided 2026-06-16:
   GitHub-source / PyInstaller-exe only — no PyPI for now** (git deps stay; keep install docs on
   the git-URL path).
6. ~~**F2** — add the `[project.gui-scripts]` entry point.~~ **Done 2026-06-16** (+ README run
   instructions; `pip install -e .` registers the `districtheatingsim` command).
7. ~~**F3** — write the CHANGELOG `[Unreleased]` section + bump the version (4 sites incl. the
   stale 1.0.0 docs badge).~~ **Done 2026-06-16** (bumped 1.0.3 → **2.0.0**, major).
8. **F4** — check the GitHub Actions status for the latest push (CI is now gating). *Currently
   green per Jonas; re-confirm after pushing the C16–C22 / F2–F3 commits.*
9. ~~**F5** — docs sweep (regenerate autodoc stubs; fix the badge + the bad `pip install` in
   `index.rst`).~~ **Done 2026-06-16** (12 missing autodoc modules added; install/run docs fixed;
   `sphinx -b html` builds clean of new errors).
10. **F6** — PyInstaller build + specs reviewed/reorganised + bugs fixed (2026-06-16) **and the build
    run + fixed (2026-06-17)**: numpy 2.x `collect_submodules`, thermal-energy-storage-1d editable
    dir-copy, `upx=False`. The debug exe now starts/runs with no import errors. *Remaining: the manual
    GUI functional test (load project + run net/energy-system), Windows-only, Jonas.*

**Pulled forward into v2.0.0 (2026-06-17):** E3 `project_tab` backslash paths + except-swallowers,
B2 `config_naming` + `geojson_to_building_csv` extractions, C16 optimizer `seed`, C17 `generate()`
scalar→`calculate_COP` deprecation, the schematic `delete_selected` rebuild, and the `v_max` default
consistency (C15.1 — already 1.0 in production).

### After the new release (Weiterentwicklung)
- **Architecture:** B1 remaining god-object *decompositions* (`project_tab`, `_11_generator_schematic`,
  `comparison_tab`, `main_view` — extract the GUI-free islands, leave the Qt glue);
  B4/E2 DE/EN naming sweep.
- **Modelling / features:** diameter→€/m cost model (C15.3); going *below* `v_max=1.0` if wanted
  (C15.1); WP 75 K clamp warning (C17 note); remove the dead `optimize_diameter_parameters`.

## Pre-release (do last, only once the above are settled)
- **Update the docs — now scoped as F5.** Sweep `docs/` (Sphinx/readthedocs) + the README
  for everything the refactors changed (constants, `TechnologyResult`, the pandapipes 0.14 /
  ISOPLUS pipe model, the thermal-storage adapter, the new test/CI workflow); regenerate the
  autodoc stubs (they miss every new module — see F5). Only worth doing once the API churn
  from the C16–C22 fixes has stopped — otherwise it rots again immediately.
- **Clean release + history reset.** Long-term plan (Jonas): once the optimizations are
  in, cut a clean release and collapse the long history (squash to a baseline commit or
  start a fresh orphan branch / fresh repo state). Do the docs update *before* this so
  the released baseline ships accurate docs.
