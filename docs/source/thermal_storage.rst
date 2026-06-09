Thermal Storage (1D Model)
==========================

DistrictHeatingSim models thermal storage with a one-dimensional, vertically
stratified tank model provided by the external package
`thermal-energy-storage-1d <https://github.com/JonasPfeiffer123/thermal-energy-storage-1d>`_
(import name ``thermal_energy_storage_model``). This single model replaces the
previous ``STES``, ``StratifiedThermalStorage`` and ``SimpleThermalStorage``
implementations, which have been removed.

Two wrappers in :mod:`districtheatingsim.heat_generators.thermal_storage` adapt
the model to the two storage roles used in the tool:

* :class:`~districtheatingsim.heat_generators.thermal_storage.ThermalStorageAdapter`
  — network-level / seasonal storage that participates in the energy-system
  dispatch and economic analysis.
* :class:`~districtheatingsim.heat_generators.thermal_storage.BufferStorage`
  — a short-term buffer tank attached to an individual generator (CHP,
  biomass boiler).

Underlying model
----------------

``ThermalStorage1D`` discretises the tank into ``n_nodes`` vertical layers and
advances the temperature profile per timestep:

* **Solver** — ``"implicit"`` (default) is unconditionally stable and avoids
  CFL restrictions at hourly resolution; ``"explicit"`` is also available.
* **Advection** — ``"tvd"`` (default, 2nd order) or ``"upwind"`` (1st order).
* **Buoyancy** — optional convective-mixing correction (default on).
* **Geometry** — cylinder, truncated cone, or truncated pyramid.
* **Loss model** — constant U-value, split lid/wall U-values, or a
  ground-temperature model.
* **Fluid** — temperature-dependent water properties (default) or constant
  ``rho`` / ``cp`` / ``lambda_fluid``.

Per timestep the adapter stores heat loss, port temperatures (top / middle /
bottom node), state of charge, and net storage flow, so they can be plotted
in the results tab.

Network / seasonal storage
--------------------------

:class:`ThermalStorageAdapter` is added to an :class:`EnergySystem` via
``add_storage()`` and implements the storage interface the dispatch loop
expects (``simulate_stratified_temperature_mass_flows``,
``current_storage_temperatures``, ``current_storage_state``, ``Q_loss``,
``calculate_efficiency``, ``calculate_costs``).

Generators charge the tank at a fixed supply temperature ``T_charge`` and
discharge against a fixed return temperature ``T_discharge_return``; these are
deliberately decoupled from the variable network supply curve (``VLT_L``),
which is the consumer side.

Configuration options
~~~~~~~~~~~~~~~~~~~~~~~

These are exposed in the *Thermischer Netzspeicher* dialog and accepted by the
``ThermalStorageAdapter`` constructor.

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Parameter
     - Default
     - Description
   * - ``volume`` / ``height``
     - 1000 m³ / 10 m
     - Tank volume and height.
   * - ``n_nodes``
     - 50
     - Number of vertical layers.
   * - ``T_min`` / ``T_max``
     - 40 / 95 °C
     - Temperature limits used for the state-of-charge calculation.
   * - ``initial_temp``
     - 60 °C
     - Uniform initial temperature.
   * - ``geometry_type``
     - ``"cylinder"``
     - ``"cylinder"``, ``"truncated_cone"`` or ``"truncated_pyramid"``.
   * - ``loss_model_type``
     - ``"constant"``
     - ``"constant"`` (``U_loss``), ``"split"`` (``U_top`` lid / wall avg of
       ``U_side``, ``U_bottom``) or ``"ground"`` (``U_top``, ``z_ground``).
   * - ``T_ambient``
     - 10 °C
     - Ambient (or ground-surface) temperature for the loss model.
   * - ``fluid_type``
     - ``"water"``
     - ``"water"`` (temperature-dependent) or constant ``rho`` / ``cp`` /
       ``lambda_fluid``.
   * - ``solver``
     - ``"implicit"``
     - ``"implicit"`` or ``"explicit"``.
   * - ``advection_scheme``
     - ``"tvd"``
     - ``"tvd"`` or ``"upwind"``.
   * - ``buoyancy``
     - ``True``
     - Enable convective-mixing correction.
   * - ``lambda_eff_factor``
     - 5.0
     - Effective vertical conductivity multiplier (stratification mixing).
   * - ``T_charge`` / ``T_discharge_return``
     - 90 / 50 °C
     - Fixed generator-side charge / discharge temperatures.
   * - ``spez_Investitionskosten``
     - 50 €/m³
     - Specific investment cost for the VDI 2067 annuity.

Generator buffer storage
-------------------------

:class:`BufferStorage` is a thin wrapper used by CHP and biomass-boiler
dispatch to replace the previous inline scalar energy bucket
(``speicher_fill`` / ``speicher_kapazitaet``). It tracks heat losses and a real
stratified temperature profile.

It is configured from a few simple inputs — tank ``volume`` plus the generator
flow / return temperatures (``T_flow`` / ``T_return``, which set the SOC
limits) — and derives a tank height from the volume (aspect ratio
:math:`h \approx (2V/\pi)^{1/3}`). The dispatch loop calls ``step(Q_net_kw,
dt_h)`` once per timestep with the net power into the tank (positive = charge,
negative = discharge) and reads back ``get_soc()``, ``get_capacity_kwh()`` and
``get_heat_loss_kw()``.

Loading old projects
--------------------

There is no automatic migration of legacy storage configurations. When
``ThermalStorageAdapter.from_dict()`` encounters keys from an old format
(e.g. ``storage_type``, ``dimensions``, ``lambda_top``) it logs a warning and
returns ``None``; the energy system still loads, and the storage must be
re-configured in the GUI.

See also
--------

* :mod:`districtheatingsim.heat_generators.thermal_storage` — full API
  reference.
* ``examples/17_energy_system_seasonal_storage.py`` — seasonal storage in an
  energy system.
* ``examples/18_chp_pufferspeicher.py`` — CHP with a generator buffer tank.
