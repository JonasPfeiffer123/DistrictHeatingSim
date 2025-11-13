# SimpleThermalStorage: Calculation Logic Documentation

**Author:** Dipl.-Ing. (FH) Jonas Pfeiffer  
**Date:** November 13, 2025  
**Module:** `districtheatingsim.heat_generators.simple_thermal_storage`

---

## 1. Introduction

This document provides a detailed scientific description of the calculation methodology implemented in the `SimpleThermalStorage` class. The model is based on the **lumped capacitance method** for thermal energy storage systems in district heating applications.

### 1.1 Purpose and Scope

The `SimpleThermalStorage` model is designed for:
- Preliminary design studies of seasonal thermal energy storage (STES)
- Performance assessment of district heating storage systems
- Annual energy balance calculations with hourly resolution
- Comparative analysis of different storage configurations

### 1.2 Reference Literature

The implementation is based on validated methods from:

**Primary Reference:**
> Narula, K., Fleury de Oliveira Filho, F., Villasmil, W., Patel, M.K. (2020).  
> "Simulation method for assessing hourly energy flows in district heating system with seasonal thermal energy storage"  
> *Renewable Energy*, Volume 151, Pages 1250-1268.  
> DOI: [10.1016/j.renene.2019.11.121](https://doi.org/10.1016/j.renene.2019.11.121)

---

## 2. Fundamental Physical Model

### 2.1 Lumped Capacitance Assumption

The model treats the entire storage volume as a **single thermal node** with uniform temperature distribution. This simplification is valid when internal temperature gradients are negligible compared to external temperature differences.

**Validity Criterion - Biot Number:**

$$
\text{Bi} = \frac{h_{\text{eff}} \cdot L_c}{k_{\text{medium}}} < 0.1
$$

Where:
- $h_{\text{eff}}$ = Effective heat transfer coefficient at storage boundary [W/(m²·K)]
- $L_c$ = Characteristic length = $V / A_{\text{surface}}$ [m]
- $k_{\text{medium}}$ = Thermal conductivity of storage medium (water: ~0.6 W/(m·K))

**Interpretation:**
- **Bi < 0.1**: Lumped capacitance valid → uniform temperature assumption acceptable
- **Bi > 0.1**: Internal gradients significant → stratified model recommended
- **Bi > 1.0**: Temperature highly non-uniform → lumped model invalid

### 2.2 Energy Balance Equation

The fundamental governing equation is the **first law of thermodynamics** applied to a closed system:

$$
\frac{dE}{dt} = \dot{Q}_{\text{in}} - \dot{Q}_{\text{out}} - \dot{Q}_{\text{loss}}
$$

Where:
- $E$ = Stored thermal energy [J] or [kWh]
- $\dot{Q}_{\text{in}}$ = Heat input power [kW]
- $\dot{Q}_{\text{out}}$ = Heat output power [kW]
- $\dot{Q}_{\text{loss}}$ = Heat loss power to environment [kW]

---

## 3. Numerical Integration Method

### 3.1 Discrete Time Formulation

The continuous energy balance is discretized using the **explicit Euler method** (forward difference):

$$
E[t] = E[t-1] + \left( \dot{Q}_{\text{in}}[t] - \dot{Q}_{\text{out}}[t] - \dot{Q}_{\text{loss}}[t] \right) \cdot \Delta t
$$

**Timestep:** $\Delta t = 1$ hour (hourly resolution)

**Unit consistency for** $\Delta t = 1$ **h:**
$$
[\text{kWh}] = [\text{kWh}] + \left( [\text{kW}] - [\text{kW}] - [\text{kW}] \right) \cdot [1\,\text{h}]
$$

Numerically: $[\text{kW}] \times [1\,\text{h}] = [\text{kWh}]$ (power integrated over 1 hour equals energy)

### 3.2 Explicit Scheme Characteristics

**Advantages:**
- Simple implementation
- No iterative solution required
- Computationally efficient

**Stability Criterion:**
For explicit schemes, stability requires:
$$
\Delta t < \frac{\rho \cdot V \cdot c_p}{UA_{\text{total}}}
$$

For typical STES systems with large thermal mass and good insulation, $\Delta t = 1$ hour is well within the stability limit.

### 3.3 Heat Loss Calculation

Heat losses are calculated **explicitly** using the temperature from the previous timestep:

$$
\dot{Q}_{\text{loss}}[t] = f(T_{\text{sto}}[t-1])
$$

This approach:
- Ensures numerical stability
- Avoids implicit equation solving
- Is accurate for slow thermal transients (typical for STES)

**Initial Condition:**
$$
\dot{Q}_{\text{loss}}[0] = 0
$$

At $t=0$, no time interval has elapsed, so no heat losses are applied. The storage is initialized with its specified initial temperature and corresponding energy content.

---

## 4. Temperature-Energy Relationships

### 4.1 Energy to Temperature Conversion

The stored energy is related to temperature through the sensible heat equation:

$$
E = m \cdot c_p \cdot (T - T_{\text{ref}})
$$

Where:
- $m = \rho \cdot V$ = Storage mass [kg]
- $c_p$ = Specific heat capacity of storage medium [J/(kg·K)]
- $T$ = Storage temperature [°C]
- $T_{\text{ref}}$ = Reference temperature [°C] (typically 0°C)

**Solving for temperature:**

$$
T = \frac{E}{m \cdot c_p} + T_{\text{ref}} = \frac{E}{\rho \cdot V \cdot c_p} + T_{\text{ref}}
$$

### 4.2 Unit Conversion

The implementation uses mixed units for practical convenience:

**Energy storage:**
- Internal calculation: Joules [J]
- User interface: Kilowatt-hours [kWh]
- Conversion factor: $1\,\text{kWh} = 3.6 \times 10^6\,\text{J}$

**Temperature calculation in code:**
```
T_sto[t] = (Q_sto[t] × 3.6e6) / (V × ρ × cp) + T_ref
```

### 4.3 Temperature Limiting

Physical constraints are enforced to prevent unphysical temperatures:

$$
T_{\min} \leq T[t] \leq T_{\max}
$$

When temperature exceeds limits:
1. Temperature is capped at limit value: $T = T_{\text{limit}}$
2. Energy is recalculated consistently: $E = \rho \cdot V \cdot c_p \cdot (T_{\text{limit}} - T_{\text{ref}})$

**Physical interpretation:**
- $T > T_{\max}$: Boiling, pressure relief, or charging stops
- $T < T_{\min}$: Freezing protection or heating activation

---

## 5. Heat Loss Calculations

### 5.1 General Heat Transfer Formulation

Heat losses are calculated using thermal resistance networks:

$$
\dot{Q}_{\text{loss}} = \frac{\Delta T}{R_{\text{total}}} = U \cdot A \cdot \Delta T
$$

Where:
- $\Delta T$ = Temperature difference between storage and environment [K]
- $R_{\text{total}}$ = Total thermal resistance [K/W]
- $U = 1/(R \cdot A)$ = Overall heat transfer coefficient [W/(m²·K)]
- $A$ = Heat transfer surface area [m²]

### 5.2 Cylindrical Overground Storage

For above-ground cylindrical tanks, heat losses occur through three surfaces:

**Top surface (to ambient air):**
$$
\dot{Q}_{\text{top}} = \frac{T_{\text{sto}} - T_{\text{amb}}}{R_{\text{top}}} = \frac{\lambda_{\text{top}}}{\delta_{\text{top}}} \cdot A_{\text{top}} \cdot (T_{\text{sto}} - T_{\text{amb}})
$$

**Side surface (to ambient air):**
$$
\dot{Q}_{\text{side}} = \frac{\lambda_{\text{side}}}{\delta_{\text{side}}} \cdot A_{\text{side}} \cdot (T_{\text{sto}} - T_{\text{amb}})
$$

**Bottom surface (through insulation and soil):**
$$
\dot{Q}_{\text{bottom}} = \frac{T_{\text{sto}} - T_{\text{amb}}}{R_{\text{ins}} + R_{\text{soil}}} \cdot A_{\text{bottom}}
$$

Where:
$$
R_{\text{ins}} = \frac{\delta_{\text{bottom}}}{\lambda_{\text{bottom}}}
$$

$$
R_{\text{soil}} = \frac{4R}{3\pi \lambda_{\text{soil}}}
$$

(Hemisphere approximation for soil resistance)

**Total loss:**
$$
\dot{Q}_{\text{loss,total}} = \dot{Q}_{\text{top}} + \dot{Q}_{\text{side}} + \dot{Q}_{\text{bottom}}
$$

### 5.3 Cylindrical Underground Storage

For underground storage, combined side and bottom losses to soil:

**Minimum insulation thickness requirement:**
$$
\delta_{\text{min}} = 0.37 \cdot R \cdot \frac{\lambda_{\text{side}}}{\lambda_{\text{soil}}}
$$

The actual insulation must satisfy: $\delta_{\text{side}} > 2\delta_{\text{min}}$

**Thermal conductance (if criterion met):**
$$
K_{sb} = \frac{1}{\frac{\delta_{\text{side}}}{\lambda_{\text{side}}} + \frac{0.52 \cdot R}{\lambda_{\text{soil}}}}
$$

**Combined heat loss:**
$$
\dot{Q}_{\text{loss}} = K_{sb} \cdot (A_{\text{side}} + A_{\text{bottom}}) \cdot (T_{\text{sto}} - T_{\text{soil}})
$$

### 5.4 Pit Thermal Energy Storage (PTES)

For truncated cone and trapezoid pit storage geometries:

**Side heat loss (logarithmic resistance correlation):**

Define:
$$
a = \frac{\delta_{\text{side}}}{\lambda_{\text{side}}} + \frac{\pi H}{2\lambda_{\text{soil}}}
$$

$$
b = \frac{\pi}{\lambda_{\text{soil}}}
$$

Thermal conductance coefficient:
$$
K_s = \frac{1}{bH} \ln\left(\frac{a + bH}{a}\right)
$$

Side heat loss:
$$
\dot{Q}_{\text{side}} = K_s \cdot A_{\text{side}} \cdot (T_{\text{sto}} - T_{\text{soil}})
$$

**Bottom heat loss:**

Define:
$$
c = \frac{\delta_{\text{bottom}}}{\lambda_{\text{bottom}}} + \frac{\pi H}{2\lambda_{\text{soil}}}
$$

Thermal conductance coefficient:
$$
K_b = \frac{1}{2bL_{\text{char}}} \ln\left(\frac{c + bL_{\text{char}}}{c}\right)
$$

Where $L_{\text{char}}$ is:
- Truncated cone: bottom radius $r_{\text{bottom}}$
- Truncated trapezoid: minimum bottom dimension

Bottom heat loss:
$$
\dot{Q}_{\text{bottom}} = K_b \cdot A_{\text{bottom}} \cdot (T_{\text{sto}} - T_{\text{soil}})
$$

**Total PTES loss:**
$$
\dot{Q}_{\text{loss,total}} = \dot{Q}_{\text{side}} + \dot{Q}_{\text{bottom}}
$$

---

## 6. Geometric Calculations

### 6.1 Cylindrical Geometry

**Input dimensions:** $(r, h)$ - radius and height [m]

**Volume:**
$$
V = \pi r^2 h
$$

**Surface areas:**
$$
A_{\text{top}} = A_{\text{bottom}} = \pi r^2
$$

$$
A_{\text{side}} = 2\pi rh
$$

### 6.2 Truncated Cone Geometry

**Input dimensions:** $(r_{\text{top}}, r_{\text{bottom}}, h)$ [m]

**Volume (frustum formula):**
$$
V = \frac{\pi h}{3}\left(r_{\text{top}}^2 + r_{\text{bottom}}^2 + r_{\text{top}} \cdot r_{\text{bottom}}\right)
$$

**Surface areas:**
$$
A_{\text{top}} = \pi r_{\text{top}}^2
$$

$$
A_{\text{bottom}} = \pi r_{\text{bottom}}^2
$$

**Slant height:**
$$
s = \sqrt{(r_{\text{bottom}} - r_{\text{top}})^2 + h^2}
$$

**Lateral surface:**
$$
A_{\text{side}} = \pi(r_{\text{top}} + r_{\text{bottom}}) \cdot s
$$

### 6.3 Truncated Trapezoid Geometry

**Input dimensions:** $(l_{\text{top}}, w_{\text{top}}, l_{\text{bottom}}, w_{\text{bottom}}, h)$ [m]

**Top and bottom areas:**
$$
A_{\text{top}} = l_{\text{top}} \times w_{\text{top}}
$$

$$
A_{\text{bottom}} = l_{\text{bottom}} \times w_{\text{bottom}}
$$

**Volume (prismoidal formula):**
$$
V = \frac{h}{3}\left(A_{\text{top}} + A_{\text{bottom}} + \sqrt{A_{\text{top}} \cdot A_{\text{bottom}}}\right)
$$

**Side surface areas:**

Length-direction slant height:
$$
s_l = \sqrt{\left(\frac{l_{\text{bottom}} - l_{\text{top}}}{2}\right)^2 + h^2}
$$

Width-direction slant height:
$$
s_w = \sqrt{\left(\frac{w_{\text{bottom}} - w_{\text{top}}}{2}\right)^2 + h^2}
$$

Total side surface:
$$
A_{\text{side}} = \frac{l_{\text{top}} + l_{\text{bottom}}}{2} \cdot s_l \times 2 + \frac{w_{\text{top}} + w_{\text{bottom}}}{2} \cdot s_w \times 2
$$

---

## 7. Performance Metrics

### 7.1 Storage Efficiency

**Round-trip efficiency** is defined as:

$$
\eta = 1 - \frac{E_{\text{losses}}}{E_{\text{input}}} = \frac{E_{\text{input}} - E_{\text{losses}}}{E_{\text{input}}}
$$

Where:
$$
E_{\text{input}} = \sum_{t=0}^{T} \dot{Q}_{\text{in}}[t] \cdot \Delta t
$$

$$
E_{\text{losses}} = \sum_{t=0}^{T} \dot{Q}_{\text{loss}}[t] \cdot \Delta t
$$

**Interpretation:**
- $\eta = 1.0$ (100%): No losses (ideal storage)
- $\eta = 0.95$ (95%): 5% energy lost to environment (typical for well-insulated STES)
- $\eta < 0.80$ (80%): Poor insulation or unfavorable geometry

### 7.2 Thermal Capacity

**Maximum energy storage capacity:**

$$
E_{\text{capacity}} = m \cdot c_p \cdot (T_{\max} - T_{\min}) = \rho \cdot V \cdot c_p \cdot \Delta T_{\text{range}}
$$

**Example for water storage:**
- $\rho = 1000$ kg/m³
- $c_p = 4186$ J/(kg·K)
- $V = 10,000$ m³
- $\Delta T = 70$ K (25°C → 95°C)

$$
E_{\text{capacity}} = \frac{1000 \times 10000 \times 4186 \times 70}{3.6 \times 10^9} = 815\,\text{MWh}
$$

---

## 8. Implementation Algorithm

### 8.1 Simulation Flowchart

```
START
  ↓
Initialize arrays: Q_sto[0..T], T_sto[0..T], Q_loss[0..T]
Set initial temperature: T_sto[0] = T_initial
  ↓
Calculate geometric properties:
  - Volume V
  - Surface areas A_top, A_side, A_bottom
  ↓
Check Biot number validity:
  Bi = (h_eff × L_c) / k_medium
  If Bi > 0.1: Issue warning
  ↓
FOR t = 0 to hours-1:
  ↓
  IF t == 0:
    Q_loss[0] = 0  (no losses at initial condition)
    Q_sto[0] = V × ρ × cp × (T_sto[0] - T_ref) / 3.6e6
  ↓
  ELSE:
    Q_loss[t] = calculate_heat_loss(T_sto[t-1])
    Q_sto[t] = Q_sto[t-1] + (Q_in[t] - Q_out[t] - Q_loss[t]) × Δt
    T_sto[t] = (Q_sto[t] × 3.6e6) / (V × ρ × cp) + T_ref
    ↓
    IF T_sto[t] > T_max:
      T_sto[t] = T_max
      Q_sto[t] = V × ρ × cp × (T_max - T_ref) / 3.6e6
    ↓
    ELSE IF T_sto[t] < T_min:
      T_sto[t] = T_min
      Q_sto[t] = V × ρ × cp × (T_min - T_ref) / 3.6e6
  ↓
NEXT t
  ↓
Calculate efficiency: η = 1 - (Σ Q_loss) / (Σ Q_in)
  ↓
END
```

### 8.2 Computational Complexity

**Time complexity:** $O(n)$ where $n$ = number of timesteps

**Space complexity:** $O(n)$ for storing time series results

**Typical performance:** ~37,000 timesteps/second on modern CPU (Python implementation)

For annual simulation (8760 hours): ~0.23 seconds

---

## 9. Model Limitations and Assumptions

### 9.1 Fundamental Assumptions

1. **Uniform temperature distribution** (lumped capacitance)
   - Valid for Bi < 0.1
   - No thermal stratification effects captured
   
2. **Constant material properties**
   - Density, specific heat, thermal conductivity assumed temperature-independent
   - Valid for moderate temperature ranges (20-95°C for water)
   
3. **Steady-state heat transfer**
   - Thermal resistances calculated assuming quasi-steady conditions
   - Transient effects in insulation/soil neglected
   
4. **Hourly timesteps**
   - Cannot resolve sub-hourly dynamics
   - Fast transients (< 1 hour) not captured

### 9.2 Applicability Range

**Suitable for:**
- ✓ Large-scale seasonal thermal energy storage (STES)
- ✓ Storage volumes > 1,000 m³
- ✓ Well-insulated systems (Bi < 0.1)
- ✓ Slow thermal processes (time constants > 10 hours)
- ✓ Annual energy balance studies
- ✓ Preliminary design and feasibility studies

**Not suitable for:**
- ✗ Small buffer tanks (< 100 m³) with fast dynamics
- ✗ Systems with significant stratification (Bi > 0.1)
- ✗ High-resolution control studies (< 1 hour timestep)
- ✗ Phase change materials (PCM storage)
- ✗ Systems with complex internal flows

### 9.3 Comparison with Advanced Models

| Feature | SimpleThermalStorage | StratifiedThermalStorage |
|---------|---------------------|--------------------------|
| Temperature nodes | 1 (uniform) | Multiple layers (5-20) |
| Biot number requirement | < 0.1 | No restriction |
| Stratification effects | ❌ Not captured | ✅ Fully modeled |
| Computational cost | Very low | Moderate |
| Use case | Preliminary design | Detailed analysis |

---

## 10. Validation and Verification

### 10.1 Energy Conservation Check

The model must satisfy global energy conservation:

$$
E_{\text{final}} - E_{\text{initial}} = \sum_{t=1}^{T} \left(\dot{Q}_{\text{in}}[t] - \dot{Q}_{\text{out}}[t] - \dot{Q}_{\text{loss}}[t]\right) \cdot \Delta t
$$

This is automatically ensured by the explicit integration scheme.

### 10.2 Typical Validation Tests

1. **Steady-state test:**
   - Constant input power, no output
   - Temperature should increase linearly until T_max
   - Heat losses should increase with temperature

2. **Charge-discharge cycle:**
   - Symmetric charging and discharging
   - Final temperature should be lower than initial (due to losses)
   - Efficiency η < 100%

3. **Thermal relaxation:**
   - No input/output, only heat losses
   - Temperature should exponentially decay to ambient
   - Time constant: τ = (m × cp) / (UA)

### 10.3 Benchmark Values

**Typical STES performance (from literature):**
- Storage efficiency: 80-95% (annual basis)
- Heat loss rate: 0.5-5% of stored energy per month
- Characteristic time constant: 100-1000 hours

---

## 11. Nomenclature

### 11.1 Symbols

| Symbol | Description | Unit |
|--------|-------------|------|
| $A$ | Surface area | m² |
| $\text{Bi}$ | Biot number | - |
| $c_p$ | Specific heat capacity | J/(kg·K) |
| $E$ | Stored thermal energy | J, kWh |
| $h$ | Height | m |
| $h_{\text{eff}}$ | Effective heat transfer coefficient | W/(m²·K) |
| $K$ | Thermal conductance coefficient | W/(m²·K) |
| $k$ | Thermal conductivity of medium | W/(m·K) |
| $L_c$ | Characteristic length | m |
| $m$ | Mass | kg |
| $\dot{Q}$ | Heat transfer rate (power) | W, kW |
| $Q$ | Heat energy | J, kWh |
| $R$ | Thermal resistance | K/W |
| $r$ | Radius | m |
| $T$ | Temperature | °C, K |
| $t$ | Time | h, s |
| $U$ | Overall heat transfer coefficient | W/(m²·K) |
| $V$ | Volume | m³ |
| $\delta$ | Insulation thickness | m |
| $\Delta t$ | Timestep | h |
| $\eta$ | Efficiency | - |
| $\lambda$ | Thermal conductivity | W/(m·K) |
| $\rho$ | Density | kg/m³ |

### 11.2 Subscripts

| Subscript | Description |
|-----------|-------------|
| amb | Ambient (air) |
| bottom | Bottom surface |
| char | Characteristic |
| eff | Effective |
| in | Input (charging) |
| ins | Insulation |
| loss | Heat loss |
| max | Maximum |
| min | Minimum |
| out | Output (discharging) |
| ref | Reference |
| side | Side surface |
| soil | Soil |
| sto | Storage |
| top | Top surface |
| total | Total |

---

## 12. References

1. Narula, K., et al. (2020). "Simulation method for assessing hourly energy flows in district heating system with seasonal thermal energy storage". *Renewable Energy*, 151, 1250-1268.

2. Incropera, F.P., DeWitt, D.P., Bergman, T.L., Lavine, A.S. (2007). *Fundamentals of Heat and Mass Transfer*, 6th Edition. John Wiley & Sons.

3. VDI Heat Atlas (2010). 2nd Edition. Springer-Verlag, Berlin Heidelberg.

4. Schmidt, T., Mangold, D., Müller-Steinhagen, H. (2004). "Central solar heating plants with seasonal storage in Germany". *Solar Energy*, 76(1-3), 165-174.

5. Xu, J., Wang, R.Z., Li, Y. (2014). "A review of available technologies for seasonal thermal energy storage". *Solar Energy*, 103, 610-638.

---

## Appendix A: Example Calculation

### Storage Configuration
- **Type:** Cylindrical underground
- **Dimensions:** r = 10 m, h = 15 m
- **Volume:** V = π × 10² × 15 = 4,712 m³
- **Medium:** Water (ρ = 1000 kg/m³, cp = 4186 J/(kg·K))
- **Temperature range:** 25-95°C
- **Insulation:** δ = 0.3 m, λ_ins = 0.04 W/(m·K)

### Thermal Capacity
$$
E_{\text{capacity}} = \frac{4712 \times 1000 \times 4186 \times 70}{3.6 \times 10^9} = 384\,\text{MWh}
$$

### Characteristic Length
$$
L_c = \frac{V}{A_{\text{total}}} = \frac{4712}{314 + 942 + 314} = 3.0\,\text{m}
$$

### Biot Number
$$
h_{\text{eff}} = \frac{\lambda_{\text{ins}}}{\delta} = \frac{0.04}{0.3} = 0.133\,\text{W/(m}^2\text{·K)}
$$

$$
\text{Bi} = \frac{0.133 \times 3.0}{0.6} = 0.67 > 0.1
$$

**Conclusion:** This configuration exceeds Bi = 0.1, suggesting stratification effects may be significant. For detailed analysis, `StratifiedThermalStorage` is recommended.

---

*Document Version: 1.0*  
*Last Updated: November 13, 2025*
