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
  - **Still open (follow-up session):** migrate the 4 hand-written dialogs that were
    moved *verbatim* — `_solar.py`, `_geothermal.py` (3D-viz, need custom hooks),
    `_heat_pump.py` (River CSV import), `_storage.py` (ThermalStorage1D dynamic
    sections). Needs a `ComboField` and a custom-widget escape hatch in `_base.py`.
- Still to tackle: `osm_dialogs.py` (~1320), `main_view.py` (~1232),
  `interactive_network_plot.py` (~1179) — same base-class + schema treatment.
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
### C4. Fragile result aggregation (partially fixed)
`energy_system.py` keeps ~8 parallel lists (`techs`, `Wärmemengen`, `Anteile`,
`WGK`, `specific_emissions_L`, `primärenergie_L`, `colors`, `Wärmeleistung_L`)
that must be appended in lockstep across several code sites. Two divergence bugs
were fixed (2026-06); the structural fix — one record/dataclass per technology row
instead of parallel lists — is still open and would make divergence impossible.
### C5. Economic-model footgun (found 2026-06)
`annuity()` expects interest/inflation as *factors* (`1.05`), not *rates* (`0.05`).
Passing a rate silently yields negative/zero costs with no error. The bug was fixed
in examples 17/18. Unit tests on `annuity()` now exist (`tests/test_annuity.py`),
including a characterization test pinning the footgun. API hardening (accept rates
and convert internally, validate `q > 1`) is still open — when it lands, the
characterization test will flip and must be updated. The GUI already passes the
factor convention, so production was never affected — but the API invites the bug.
### C6. CHP cost calc brittle to instance name (found 2026-06)
`chp.calculate_heat_generation_costs()` selects investment cost + fuel price by
branching on `self.name.startswith("BHKW")` / `"Holzgas-BHKW"`. A `CHP` named
anything else leaves `spez_Investitionskosten_BHKW` unbound and raises
`UnboundLocalError` mid-calculation. Production names happen to start with `BHKW`,
so it works today, but the cost path should key off an explicit fuel/type attribute,
not the display name. Characterized in `tests/test_heat_generators.py::TestCHP`.
### C7. Dialog capacity read/write key asymmetry (found 2026-06)
`GasBoilerDialog` / `BiomassBoilerDialog` read the capacity field's initial value
from `th_Leistung_kW` / `P_BMK` but emit it under `thermal_capacity_kW`. Editing an
existing tech (whose stored data carries `thermal_capacity_kW`, per the generator
constructors) finds neither read-key present, so the displayed capacity silently
resets to the field default (1000 / 240 kW). Pinned by
`tests/test_technology_dialogs.py::TestKeyAsymmetry` and reproduced verbatim in the
refactor via `Field.in_key`. Fix: make read-key == write-key (`thermal_capacity_kW`)
once the generators' `to_dict`/edit round-trip is confirmed — then flip the tests.
### C8. CHP/HolzgasCHP storage-cost default typo (found 2026-06)
The "spez. Investitionskosten Speicher" field defaults to `"0.8"` in the CHP and
Holzgas-CHP dialogs but `"750"` in Biomass — almost certainly a typo (€/m³). Pinned
by `tests/test_technology_dialogs.py::TestStorageToggle` and preserved in
`_schemas.CHP_STORAGE`. Fix: set the default to `"750"` and update the test.

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
