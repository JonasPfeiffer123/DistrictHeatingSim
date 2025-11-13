STES: Mass Flow-Based Seasonal Storage Calculation Logic
================================================================================

**Author:** Dipl.-Ing. (FH) Jonas Pfeiffer  
**Date:** November 13, 2025  
**Module:** ``districtheatingsim.heat_generators.STES``


--------------------------------------------------------------------------------


1. Introduction

--------------------------------------------------------------------------------


This document describes the calculation methodology of the **STES (Seasonal Thermal Energy Storage)** class, which extends ``StratifiedThermalStorage`` with **mass flow-based energy transfer** and **hydraulic operational constraints**.

1.1 Relationship to Other Storage Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The STES class represents the **most detailed level** in the storage model hierarchy:

`::

SimpleThermalStorage (Lumped capacitance, uniform temperature)
    ↓ extends
StratifiedThermalStorage (Multi-layer temperatures, energy-based charging)
    ↓ extends
STES (Mass flow-based hydraulic model, operational constraints)
``

**For fundamental concepts, refer to:**
- ```SimpleThermalStorage_Calculation_Logic.md`` <SimpleThermalStorage_Calculation_Logic.md>`_ - Basic energy balance, heat losses, geometry
- ```StratifiedThermalStorage_Calculation_Logic.md`` <StratifiedThermalStorage_Calculation_Logic.md>`_ - Stratification, layer calculations, inter-layer conduction

This document **focuses exclusively on the mass flow-based extensions** that differentiate STES from StratifiedThermalStorage.

1.2 Key Differences from StratifiedThermalStorage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

| Feature | StratifiedThermalStorage | STES |
|---------|-------------------------|------|
| **Energy transfer** | Power-based (Q_in, Q_out) | Mass flow-based (ṁ, ΔT) |
| **Charging logic** | Direct energy addition to layers | Flow mixing through layers |
| **Discharging logic** | Direct energy extraction | Return flow mixing |
| **Operational constraints** | Temperature limits only | + Hydraulic constraints |
| **System integration** | Simplified | Realistic district heating |
| **Stagnation handling** | Not modeled | Explicit tracking |
| **Unmet demand** | Not modeled | Explicit tracking |


--------------------------------------------------------------------------------


2. Mass Flow-Based Energy Transfer

--------------------------------------------------------------------------------


2.1 Fundamental Principle
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Instead of directly adding/removing energy, STES models **realistic hydraulic flows**:

.. math::



\dot{Q} = \dot{m} \cdot c_p \cdot \Delta T


Where:
- :math:`\dot{Q}` = Heat transfer rate [kW]
- :math:`\dot{m}` = Mass flow rate [kg/s]
- :math:`c_p` = Specific heat capacity [J/(kg·K)]
- :math:`\Delta T` = Temperature difference [K]

2.2 Mass Flow Calculation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Charging Mass Flow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Given heat input :math:`\dot{Q}_{\text{in}}` [kW] and temperatures:

.. math::



\dot{m}_{\text{in}} = \frac{\dot{Q}_{\text{in}} \times 1000}{c_p \cdot (T_{\text{supply}} - T_{\text{bottom}})}


**Unit verification:**
.. math::



[\text{kg/s}] = \frac{[\text{kW}] \times [1000\,\text{W/kW}]}{[\text{J/(kg·K)}] \times [\text{K}]} = \frac{[\text{W}]}{[\text{J/(kg·K)}] \times [\text{K}]} = [\text{kg/s}] \quad \checkmark


Discharging Mass Flow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Given heat output :math:`\dot{Q}_{\text{out}}` [kW]:

.. math::



\dot{m}_{\text{out}} = \frac{\dot{Q}_{\text{out}} \times 1000}{c_p \cdot (T_{\text{top}} - T_{\text{return}})}


2.3 Flow Mixing Model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Physical basis:** Incoming flow mixes with layer content via energy balance.

For layer :math:`i` with incoming flow:

.. math::



T_{\text{new}} = \frac{\dot{m}_{\text{flow}} \cdot T_{\text{flow}} + m_{\text{layer}} \cdot T_{\text{layer}}}{\dot{m}_{\text{flow}} + m_{\text{layer}}}


Where:
- :math:`\dot{m}_{\text{flow}}` = Flow mass per hour [kg] = :math:`\dot{m}` [kg/s] × 3600 [s/h]
- :math:`m_{\text{layer}}` = Layer mass [kg] = :math:`\rho \cdot V_{\text{layer}}`
- :math:`c_p` cancels out in the fraction

**Note:** This is equivalent to energy balance but computationally simpler (no need for Kelvin conversion or explicit :math:`c_p` multiplication).


--------------------------------------------------------------------------------


3. Operational Constraints

--------------------------------------------------------------------------------


3.1 Charging Constraints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Condition 1: Maximum Return Temperature**

.. math::



T_{\text{bottom}} < T_{\text{max,rücklauf}}


**Rationale:** Protect heat generators (solar collectors, heat pumps) from excessive return temperatures.

**Typical value:** :math:`T_{\text{max,rücklauf}} = 70°C`

**If violated:**
- Charging stopped: :math:`\dot{m}_{\text{in}} = 0`, :math:`\dot{Q}_{\text{in}} = 0`
- Excess heat tracked: :math:`E_{\text{excess}} \mathrel{+}= \dot{Q}_{\text{in,available}} \cdot \Delta t`
- Stagnation time incremented

**Condition 2: Minimum Temperature Difference**

.. math::



T_{\text{supply}} > T_{\text{bottom}} + \Delta T_{\min}


**Rationale:** Ensure sufficient driving force for heat transfer.

**Typical value:** :math:`\Delta T_{\min} = 10^{-3}` K (numerical threshold)

3.2 Discharging Constraints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Condition 1: Minimum Supply Temperature**

.. math::



T_{\text{top}} > T_{\text{supply,required}} - \Delta T_{\text{VLT}}


Where:
- :math:`T_{\text{supply,required}}` = Required supply temperature from generators [°C]
- :math:`\Delta T_{\text{VLT}}` = Supply temperature tolerance [K] (typical: 15 K)

**Rationale:** Ensure adequate supply temperature quality for consumers.

**If violated:**
- Discharging stopped: :math:`\dot{m}_{\text{out}} = 0`, :math:`\dot{Q}_{\text{out}} = 0`
- Unmet demand tracked: :math:`E_{\text{unmet}} \mathrel{+}= \dot{Q}_{\text{out,demand}} \cdot \Delta t`

**Condition 2: Minimum Temperature Difference**

.. math::



T_{\text{top}} > T_{\text{return}} + \Delta T_{\min}


**Rationale:** Ensure sufficient temperature difference for heat extraction.


--------------------------------------------------------------------------------


4. STES Simulation Algorithm

--------------------------------------------------------------------------------


4.1 Overview
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The STES simulation extends the StratifiedThermalStorage algorithm with **7 sequential steps per timestep**:

``::

INITIALIZATION (t=0):
  - Initialize layer temperatures
  - Calculate initial heat losses
  - Compute initial stored energy

MAIN LOOP (t > 0):
  STEP 1: Apply heat losses (from StratifiedThermalStorage)
  STEP 2: Inter-layer conduction (from StratifiedThermalStorage)
  STEP 3: Check charging constraints → Calculate ṁ_in
  STEP 4: Check discharging constraints → Calculate ṁ_out
  STEP 5: Distribute heat input via flow mixing (top→bottom)
  STEP 6: Extract heat via return flow mixing (bottom→top)
  STEP 7: Apply temperature limits, calculate total energy
``

4.2 Step-by-Step Calculation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Inherited from StratifiedThermalStorage (Steps 1-2):**

See ```StratifiedThermalStorage_Calculation_Logic.md``, Section 6.2 <StratifiedThermalStorage_Calculation_Logic.md#62-main-simulation-loop>`_ for:
- Heat loss application per layer
- Inter-layer conduction with correct interface areas

**STES-Specific Steps (Steps 3-7):**

Step 3: Charging Constraint Check
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``.. code-block:: python

IF T_bottom < T_max_rücklauf:
    IF T_supply > T_bottom + ε:
        ṁ_in = (Q_in × 1000) / (cp × (T_supply - T_bottom))
        Q_in = Q_in  # Accept charging
    ELSE:
        ṁ_in = 0  # Insufficient ΔT
        Q_in = 0
ELSE:
    ṁ_in = 0  # Stagnation
    Q_in = 0
    E_excess += Q_in_available × Δt
    stagnation_time += 1
``

Step 4: Discharging Constraint Check
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``.. code-block:: python

IF T_top > T_supply_required - ΔT_VLT:
    IF T_top > T_return + ε:
        ṁ_out = (Q_out × 1000) / (cp × (T_top - T_return))
        Q_out = Q_out  # Accept discharging
    ELSE:
        ṁ_out = 0  # Insufficient ΔT
        Q_out = 0
ELSE:
    ṁ_out = 0  # Storage too cold
    Q_out = 0
    E_unmet += Q_out_demand × Δt
``

Step 5: Heat Input Distribution (Top → Bottom)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``.. code-block:: python

T_flow = T_supply  # Initial flow temperature

FOR i = 0 to n_layers-1:  # Top to bottom
    IF ṁ_in > 0:
        # Flow mass per hour [kg]
        m_flow = ṁ_in × 3600
        
        # Layer mass [kg]
        m_layer = ρ × V_i
        
        # Mixing temperature [°C]
        T_new[i] = (m_flow × T_flow + m_layer × T_old[i]) / (m_flow + m_layer)
        
        # Update for next layer
        T_flow = T_new[i]
``

**Physical interpretation:**
- Hot supply flow enters top layer
- Mixes with layer content → raises layer temperature
- Flow exits layer at layer temperature → enters next layer
- Progressive temperature cascade through storage

Step 6: Heat Extraction (Bottom → Top)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``.. code-block:: python

T_return = T_consumer_return  # Initial return temperature

FOR i = n_layers-1 to 0:  # Bottom to top
    IF ṁ_out > 0:
        # Flow mass per hour [kg]
        m_flow = ṁ_out × 3600
        
        # Layer mass [kg]
        m_layer = ρ × V_i
        
        # Mixing temperature [°C]
        T_new[i] = (m_flow × T_return + m_layer × T_old[i]) / (m_flow + m_layer)
        
        # Update for next layer
        T_return = T_new[i]
``

**Physical interpretation:**
- Cold return flow enters bottom layer
- Mixes with layer content → cools layer
- Flow exits at layer temperature → enters next layer up
- Progressive heating of return flow through storage

Step 7: Finalization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``.. code-block:: python

Apply temperature limits
================================================================================
T_layers = clip(T_layers, T_min, T_max)

Calculate total stored energy from temperatures [kWh]
================================================================================
E_total = Σ(V_i × ρ × cp × (T_i - T_ref) / 3.6e6)

Calculate average temperature
================================================================================
T_avg = mean(T_layers)

Store system interface temperatures
================================================================================
T_supply_to_consumers = T_layers[0]      # Top layer
T_return_to_generators = T_layers[-1]    # Bottom layer
``

4.3 Flowchart
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``::

START (t > 0)
  ↓
STEP 1: Heat Losses
  Calculate Q_loss per layer
  Update T_new[i] -= ΔT_loss
  ↓
STEP 2: Inter-Layer Conduction
  FOR each interface:
    Calculate Q_cond with A_interface (horizontal!)
    Update T_new[i] and T_new[i+1]
  ↓
STEP 3: Charging Check
  IF T_bottom < T_max_rücklauf AND ΔT sufficient:
    Calculate ṁ_in
    Q_in = Q_in_available
  ELSE:
    ṁ_in = 0, Q_in = 0
    Track excess_heat or insufficient ΔT
  ↓
STEP 4: Discharging Check
  IF T_top > T_required - ΔT_VLT AND ΔT sufficient:
    Calculate ṁ_out
    Q_out = Q_out_demand
  ELSE:
    ṁ_out = 0, Q_out = 0
    Track unmet_demand
  ↓
STEP 5: Heat Input (Top→Bottom)
  T_flow = T_supply
  FOR i = 0 to n-1:
    IF ṁ_in > 0:
      T_new[i] = mixing(T_flow, T_old[i], ṁ_in, m_layer)
      T_flow = T_new[i]
  ↓
STEP 6: Heat Extraction (Bottom→Top)
  T_return = T_consumer_return
  FOR i = n-1 to 0:
    IF ṁ_out > 0:
      T_new[i] = mixing(T_return, T_old[i], ṁ_out, m_layer)
      T_return = T_new[i]
  ↓
STEP 7: Finalization
  Clip T_new to [T_min, T_max]
  Calculate E_total from T_new
  Calculate T_avg
  Store interface temperatures
  ↓
END
``


--------------------------------------------------------------------------------


5. Performance Metrics

--------------------------------------------------------------------------------


5.1 Inherited Metrics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**From SimpleThermalStorage:**
- Storage efficiency: :math:`\eta = 1 - \sum Q_{\text{loss}} / \sum Q_{\text{in}}`
- Thermal capacity: :math:`E_{\text{capacity}} = \rho \cdot V \cdot c_p \cdot \Delta T_{\text{range}}`

**From StratifiedThermalStorage:**
- Stratification index: :math:`\text{SI} = (T_{\text{top}} - T_{\text{bottom}}) / (T_{\max} - T_{\min})`
- Effective temperature: :math:`T_{\text{eff}} = \sum (T_i \cdot V_i) / \sum V_i`

5.2 STES-Specific Metrics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Excess Heat (Stagnation)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Total heat that could not be stored due to constraints:

.. math::



E_{\text{excess}} = \sum_{t=1}^{T} \dot{Q}_{\text{in,rejected}}[t] \cdot \Delta t \quad [\text{kWh}]


**Interpretation:**
- High value → Storage oversized or insufficient discharge
- Low value → Good match between generation and storage capacity

Unmet Demand
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Total heat demand that could not be satisfied:

.. math::



E_{\text{unmet}} = \sum_{t=1}^{T} \dot{Q}_{\text{out,unsatisfied}}[t] \cdot \Delta t \quad [\text{kWh}]


**Interpretation:**
- High value → Storage undersized or insufficient charging
- Low value → Storage meets demand reliably

Stagnation Time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Total hours when storage could not accept heat:

.. math::



t_{\text{stagnation}} = \text{count}(T_{\text{bottom}} \geq T_{\text{max,rücklauf}}) \quad [\text{hours}]


**Typical values:**
- < 100 h/year: Well-balanced system
- 100-500 h/year: Acceptable for seasonal storage
- > 500 h/year: Consider larger storage or better control

Storage Utilization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. math::



U = \frac{E_{\text{out,actual}}}{\sum Q_{\text{in}} \cdot \Delta t}


Fraction of charged energy actually used by consumers.


--------------------------------------------------------------------------------


6. Numerical Implementation

--------------------------------------------------------------------------------


6.1 Pre-Calculated Constants (Performance Optimization)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Inherited from StratifiedThermalStorage:**
``.. code-block:: python

Calculated once before main loop
================================================================================
layer_thermal_capacity = layer_volume × ρ × cp  # [J/K]
A_interface = _calculate_interface_areas()      # [m²]
conduction_coeff = λ × A_interface / δ_layer    # [W/K]
conversion_factor = 3.6e6                       # [J/kWh]
``

**Performance gain:** ~15-20% speedup compared to inline calculations.

6.2 Temperature as Primary State Variable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Critical design decision:**

``.. code-block:: python

Temperature is PRIMARY - directly simulated
================================================================================
T_layers[t] = f(T_layers[t-1], losses, conduction, flows)

Energy is SECONDARY - calculated from temperature
================================================================================
E_total[t] = Σ(V_i × ρ × cp × (T_i[t] - T_ref) / 3.6e6)
``

**Advantages:**
- ✅ No drift between temperature and energy
- ✅ Physical constraints easily enforced on temperature
- ✅ Mass flow mixing naturally operates on temperature
- ✅ Consistent energy calculation

**Previous approach (removed):**
- Maintained separate ``heat_stored_per_layer`` array
- Applied losses and transfers to both energy and temperature
- Risk of inconsistency and numerical drift

6.3 Simplified Mixing Calculation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Energy balance approach (complex):**
.. math::



T_{\text{mix}} = \frac{\dot{m}_1 \cdot c_p \cdot (T_1 + 273.15) + \dot{m}_2 \cdot c_p \cdot (T_2 + 273.15)}{(\dot{m}_1 + \dot{m}_2) \cdot c_p} - 273.15


**Simplified approach (equivalent):**
.. math::



T_{\text{mix}} = \frac{\dot{m}_1 \cdot T_1 + \dot{m}_2 \cdot T_2}{\dot{m}_1 + \dot{m}_2}


**Rationale:**
- :math:`c_p` cancels out (same medium)
- Kelvin conversion unnecessary for temperature differences
- Computationally faster and clearer


--------------------------------------------------------------------------------


7. System Integration

--------------------------------------------------------------------------------


7.1 Interface Temperatures
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**STES provides four interface temperatures for district heating integration:**

| Variable | Description | Physical Meaning |
|----------|-------------|------------------|
| ``T_Q_in_flow`` | Generator supply [°C] | Temperature from heat generators (input) |
| ``T_Q_in_return`` | Generator return [°C] | Return temperature to generators = ``T_bottom`` |
| ``T_Q_out_flow`` | Consumer supply [°C] | Supply temperature to consumers = ``T_top`` |
| ``T_Q_out_return`` | Consumer return [°C] | Return temperature from consumers (input) |

**System integration flow:**

``::

Heat Generators (Solar, CHP, etc.)
  ↓ T_supply, ṁ_in
STES (Charging)
  ↓ T_return = T_bottom
Heat Generators

Consumers (Buildings)
  ↓ T_return_consumer, ṁ_out
STES (Discharging)
  ↓ T_supply = T_top
Consumers
``

7.2 Coupling with District Heating Network
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Typical configuration:**

1. **Charging loop:**
   - Heat generators → STES top
   - STES bottom → Heat generators
   - Constraint: ``T_bottom < T_max_rücklauf``

2. **Discharging loop:**
   - STES top → Distribution network
   - Distribution network → STES bottom
   - Constraint: ``T_top > T_supply_required - ΔT_VLT``

3. **Hydraulic decoupling:**
   - Separate mass flows for charging and discharging
   - No simultaneous charging and discharging (simplified model)
   - Real systems may use heat exchangers or mixing valves


--------------------------------------------------------------------------------


8. Model Comparison

--------------------------------------------------------------------------------


8.1 Feature Matrix
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

| Feature | Simple | Stratified | STES |
|---------|--------|------------|------|
| **Temperature nodes** | 1 | n layers | n layers |
| **Stratification** | ❌ | ✅ | ✅ |
| **Energy transfer** | Direct | Direct | Mass flow-based |
| **Hydraulic model** | ❌ | ❌ | ✅ |
| **Operational constraints** | T limits only | T limits only | + Hydraulic |
| **System integration** | Simplified | Simplified | Realistic |
| **Stagnation tracking** | ❌ | ❌ | ✅ |
| **Unmet demand tracking** | ❌ | ❌ | ✅ |
| **Computational cost** | Very low | Low | Moderate |
| **Use case** | Screening | Detailed design | System integration |

8.2 When to Use Each Model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**SimpleThermalStorage:**
- ✓ Preliminary feasibility studies
- ✓ Parameter screening (100+ design variants)
- ✓ Bi < 0.1 (well-mixed assumption valid)
- ✓ Focus on total energy balance

**StratifiedThermalStorage:**
- ✓ Detailed performance analysis
- ✓ Temperature quality assessment
- ✓ Stratification effects significant
- ✓ Control strategy development

**STES:**
- ✓ District heating system integration
- ✓ Realistic operational constraints
- ✓ Stagnation and supply reliability analysis
- ✓ Mass flow and hydraulic considerations important
- ✓ Generator and consumer coupling

8.3 Computational Performance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Typical annual simulation (8760 hours):**

| Model | Timesteps/sec | Simulation Time | Relative |
|-------|---------------|-----------------|----------|
| SimpleThermalStorage | ~37,000 | ~0.24 s | 1× |
| StratifiedThermalStorage (n=10) | ~15,000 | ~0.58 s | 2.4× |
| STES (n=10) | ~12,000 | ~0.73 s | 3.0× |

**STES overhead:** ~25% slower than StratifiedThermalStorage due to:
- Mass flow calculations
- Constraint checking
- Flow mixing iterations

**Acceptable for:** Real-time control studies, yearly simulations, multi-year scenarios


--------------------------------------------------------------------------------


9. Validation and Quality Assurance

--------------------------------------------------------------------------------


9.1 Energy Conservation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Global energy balance must hold:**

.. math::



E[t] - E[t-1] = (\dot{Q}_{\text{in,actual}}[t] - \dot{Q}_{\text{out,actual}}[t] - \dot{Q}_{\text{loss}}[t]) \cdot \Delta t


Where:
- :math:`\dot{Q}_{\text{in,actual}}` may be 0 if stagnation occurs
- :math:`\dot{Q}_{\text{out,actual}}` may be 0 if supply insufficient

**Verification:**
Temperature is primary state variable → Energy calculated consistently from temperature → Conservation guaranteed by construction.

9.2 Mass Flow Consistency
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Verify mass flow calculations:**

Given :math:`\dot{Q} = \dot{m} \cdot c_p \cdot \Delta T`, check:

.. math::



\dot{Q}_{\text{calculated}} = \dot{m} \cdot c_p \cdot (T_{\text{in}} - T_{\text{out}}) \approx \dot{Q}_{\text{target}}


**Typical tolerance:** < 1% deviation acceptable

9.3 Stratification Preservation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**During charging:** Top layers should be hotter than bottom layers.

**During discharging:** Stratification should be maintained or slightly reduced.

**Check:** Monitor stratification index over time:
.. math::



\text{SI}(t) = \frac{T_{\text{top}}(t) - T_{\text{bottom}}(t)}{T_{\max} - T_{\min}}


Should not exhibit unphysical inversions or oscillations.


--------------------------------------------------------------------------------


10. Limitations and Assumptions

--------------------------------------------------------------------------------


10.1 Inherited Limitations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**From SimpleThermalStorage and StratifiedThermalStorage:**
- Constant material properties
- Steady-state heat transfer
- Hourly timestep resolution
- One-dimensional stratification
- No convective mixing (except via mass flows)

See ```SimpleThermalStorage_Calculation_Logic.md``, Section 9 <SimpleThermalStorage_Calculation_Logic.md#9-model-limitations-and-assumptions>`_ and ```StratifiedThermalStorage_Calculation_Logic.md``, Section 12 <StratifiedThermalStorage_Calculation_Logic.md#122-stratification-specific-limitations>`_.

10.2 STES-Specific Limitations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**1. Simplified Hydraulic Model**
- No pressure drop calculations
- No pump power requirements
- Mass flows calculated from energy requirements, not hydraulics

**2. Perfect Mixing Assumption**
- Flow uniformly distributed across layer cross-section
- No jet effects or short-circuiting
- Requires good diffuser design in practice

**3. Sequential Charging and Discharging**
- No simultaneous charging and discharging
- Real systems may have both (e.g., during transition periods)
- Conservative simplification

**4. Constant System Temperatures**
- Generator supply and consumer return temperatures specified externally
- No feedback from storage state to system operation
- Suitable for fixed setpoint operation

**5. No Heat Exchanger Modeling**
- Direct connection assumed
- Real systems often use heat exchangers
- Introduces additional temperature drops

10.3 Applicability Range
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Suitable for:**
- ✓ Large-scale seasonal thermal energy storage (> 5,000 m³)
- ✓ District heating system integration studies
- ✓ Annual energy balance and reliability analysis
- ✓ Operational constraint assessment
- ✓ Stagnation and supply quality studies

**Not suitable for:**
- ✗ Detailed hydraulic design (use CFD)
- ✗ Sub-hourly control dynamics
- ✗ Systems with complex flow patterns
- ✗ Multi-storage configurations without adaptation


--------------------------------------------------------------------------------


11. References

--------------------------------------------------------------------------------


11.1 Primary Literature
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Same as SimpleThermalStorage and StratifiedThermalStorage:

1. **Narula, K., et al. (2020).** "Simulation method for assessing hourly energy flows in district heating system with seasonal thermal energy storage". *Renewable Energy*, 151, 1250-1268.

11.2 Additional References for Mass Flow Modeling
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

2. **Bauer, D., et al. (2010).** "German central solar heating plants with seasonal heat storage". *Solar Energy*, 84(4), 612-623.

3. **Novo, A.V., et al. (2010).** "Review of seasonal heat storage in large basins: Water tanks and gravel-water pits". *Applied Energy*, 87(2), 390-397.

4. **Ochs, F., et al. (2009).** "Effective thermal conductivity of moistened insulation materials as function of temperature". *International Journal of Thermal Sciences*, 48(7), 1343-1355.

11.3 Related Documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ```SimpleThermalStorage_Calculation_Logic.md`` <SimpleThermalStorage_Calculation_Logic.md>`_ - Base model fundamentals
- ```StratifiedThermalStorage_Calculation_Logic.md` <StratifiedThermalStorage_Calculation_Logic.md>`_ - Stratification physics and layer calculations


--------------------------------------------------------------------------------


12. Nomenclature

--------------------------------------------------------------------------------


12.1 Additional Symbols (Beyond SimpleThermalStorage and StratifiedThermalStorage)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

| Symbol | Description | Unit |
|--------|-------------|------|
| :math:`\dot{m}_{\text{in}}` | Charging mass flow rate | kg/s |
| :math:`\dot{m}_{\text{out}}` | Discharging mass flow rate | kg/s |
| :math:`T_{\text{supply}}` | Generator supply temperature | °C |
| :math:`T_{\text{return}}` | Consumer return temperature | °C |
| :math:`T_{\text{max,rücklauf}}` | Maximum allowable return temperature to generators | °C |
| :math:`\Delta T_{\text{VLT}}` | Supply temperature tolerance | K |
| :math:`E_{\text{excess}}` | Total excess heat (stagnation) | kWh |
| :math:`E_{\text{unmet}}` | Total unmet demand | kWh |
| :math:`t_{\text{stagnation}}` | Stagnation duration | hours |

12.2 Subscripts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

| Subscript | Description |
|-----------|-------------|
| actual | Actually transferred (may differ from target) |
| available | Available for transfer |
| demand | Requested by consumers |
| rejected | Could not be accepted (stagnation) |
| unsatisfied | Could not be delivered |


--------------------------------------------------------------------------------


*Document Version: 1.0*  
*Last Updated: November 13, 2025*  
*Extends: StratifiedThermalStorage_Calculation_Logic.md*  
*Part of: District Heating Simulation Seasonal Storage Model Documentation*
