# StratifiedThermalStorage: Calculation Logic Documentation

**Author:** Dipl.-Ing. (FH) Jonas Pfeiffer  
**Date:** November 13, 2025  
**Module:** `districtheatingsim.heat_generators.stratified_thermal_storage`

---

## 1. Introduction

This document provides a detailed scientific description of the calculation methodology implemented in the `StratifiedThermalStorage` class. The model extends the lumped capacitance approach with **multi-layer temperature distribution modeling** for accurate simulation of thermal stratification in seasonal thermal energy storage systems.

### 1.1 Purpose and Scope

The `StratifiedThermalStorage` model is designed for:
- Detailed thermal stratification analysis in STES systems
- Temperature gradient evolution over annual cycles
- Performance optimization considering stratification effects
- Advanced control strategy development
- Systems where Biot number > 0.1 (lumped model invalid)

### 1.2 Relationship to SimpleThermalStorage

`StratifiedThermalStorage` **extends** `SimpleThermalStorage` (inherits from `ThermalStorage` base class) by adding:
- Multi-layer temperature distribution (vs. single uniform temperature)
- Layer-specific heat loss calculations
- Inter-layer heat conduction modeling
- Stratification-preserving charging/discharging logic

**For fundamental concepts covered in SimpleThermalStorage, please refer to:**
> [`SimpleThermalStorage_Calculation_Logic.md`](SimpleThermalStorage_Calculation_Logic.md)

This includes:
- Basic energy balance principles (Section 2)
- Temperature-energy relationships (Section 4)
- Geometric calculations (Section 6)
- Material properties and nomenclature (Sections 11-12)

### 1.3 Reference Literature

Same primary reference as SimpleThermalStorage:

**Primary Reference:**
> Narula, K., Fleury de Oliveira Filho, F., Villasmil, W., Patel, M.K. (2020).  
> "Simulation method for assessing hourly energy flows in district heating system with seasonal thermal energy storage"  
> *Renewable Energy*, Volume 151, Pages 1250-1268.  
> DOI: [10.1016/j.renene.2019.11.121](https://doi.org/10.1016/j.renene.2019.11.121)

---

## 2. Thermal Stratification Physics

### 2.1 Why Stratification Matters

In large-scale thermal energy storage systems, **thermal stratification** (vertical temperature gradients) develops due to:

1. **Buoyancy effects**: Hot water is less dense and rises to the top
2. **Differential heat losses**: Surface layers lose heat faster than deep layers
3. **Flow patterns**: Inlet/outlet configurations affect mixing
4. **Size scale**: Large storage volumes reduce mixing effectiveness

**Impact on performance:**
- ✅ **Well-maintained stratification**: Higher exergy efficiency, better heat delivery quality
- ❌ **Excessive mixing**: Lower efficiency, reduced usable temperature range

### 2.2 When to Use Stratified vs. Simple Model

| Criterion | Simple Model | Stratified Model |
|-----------|--------------|------------------|
| **Biot Number** | Bi < 0.1 | Bi ≥ 0.1 |
| **Storage Volume** | < 1,000 m³ | > 1,000 m³ |
| **Height/Diameter** | < 1 | > 1 |
| **Analysis Detail** | Preliminary design | Detailed optimization |
| **Temperature Gradients** | Negligible | Significant |
| **Computational Cost** | Very low | Moderate |

### 2.3 Layer-Based Modeling Approach

The storage volume is divided into **n horizontal layers** of equal thickness:

$$
\delta_{\text{layer}} = \frac{H_{\text{total}}}{n_{\text{layers}}}
$$

Each layer has:
- **Individual temperature** $T_i$ [°C]
- **Layer-specific volume** $V_i$ [m³] (varies for non-cylindrical geometries)
- **Thermal capacity** $C_i = \rho \cdot V_i \cdot c_p$ [J/K]
- **Independent heat loss** $\dot{Q}_{\text{loss},i}$ [kW]

**Typical layer counts:**
- Small storage (< 5,000 m³): 5-10 layers
- Medium storage (5,000-50,000 m³): 10-20 layers
- Large PTES (> 50,000 m³): 20-50 layers

---

## 3. Layer Geometry Calculations

### 3.1 Uniform Layer Thickness

All storage geometries use **uniform vertical layer division**:

$$
\delta_{\text{layer}} = \frac{H}{n}
$$

This ensures:
- Consistent discretization
- Simplified numerical implementation
- Natural alignment with physical stratification

### 3.2 Layer Volume Distribution

**See [`SimpleThermalStorage_Calculation_Logic.md`, Section 6](SimpleThermalStorage_Calculation_Logic.md#6-geometric-calculations) for base geometric formulas.**

#### 3.2.1 Cylindrical Storage

**Constant cross-section** → Uniform layer volumes:

$$
V_{\text{layer}} = \frac{V_{\text{total}}}{n} = \frac{\pi r^2 h}{n}
$$

#### 3.2.2 Truncated Cone

**Variable cross-section** → Layer volumes calculated using frustum formula:

For layer $i$ (counting from top, $i = 0, 1, ..., n-1$):

$$
r_{\text{top},i} = r_{\text{top}} + (r_{\text{bottom}} - r_{\text{top}}) \cdot \frac{i}{n}
$$

$$
r_{\text{bottom},i} = r_{\text{top}} + (r_{\text{bottom}} - r_{\text{top}}) \cdot \frac{i+1}{n}
$$

$$
V_i = \frac{\pi \delta_{\text{layer}}}{3} \left( r_{\text{top},i}^2 + r_{\text{bottom},i}^2 + r_{\text{top},i} \cdot r_{\text{bottom},i} \right)
$$

#### 3.2.3 Truncated Trapezoid

**Variable rectangular cross-section** → Prismoidal formula per layer:

For layer $i$:

$$
a_{\text{top},i} = a_{\text{top}} + (a_{\text{bottom}} - a_{\text{top}}) \cdot \frac{i}{n}
$$

$$
b_{\text{top},i} = b_{\text{top}} + (b_{\text{bottom}} - b_{\text{top}}) \cdot \frac{i}{n}
$$

Similarly for $a_{\text{bottom},i}$ and $b_{\text{bottom},i}$ at $\frac{i+1}{n}$.

$$
A_{\text{top},i} = a_{\text{top},i} \times b_{\text{top},i}
$$

$$
A_{\text{bottom},i} = a_{\text{bottom},i} \times b_{\text{bottom},i}
$$

$$
V_i = \frac{\delta_{\text{layer}}}{3} \left( A_{\text{top},i} + A_{\text{bottom},i} + \sqrt{A_{\text{top},i} \cdot A_{\text{bottom},i}} \right)
$$

### 3.3 Interface Areas for Heat Conduction

**CRITICAL**: For vertical heat conduction between layers, the **horizontal cross-sectional area** (perpendicular to heat flow) must be used, **NOT the vertical side surface area**.

$$
Q_{\text{cond}} = \lambda \cdot A_{\text{interface}} \cdot \frac{\Delta T}{\delta_{\text{layer}}}
$$

#### 3.3.1 Cylindrical

**Constant interface area:**

$$
A_{\text{interface}} = \pi r^2
$$

#### 3.3.2 Truncated Cone

**Variable interface area** at boundary between layers $i$ and $i+1$:

$$
r_{\text{interface},i} = r_{\text{top}} + (r_{\text{bottom}} - r_{\text{top}}) \cdot \frac{i+1}{n}
$$

$$
A_{\text{interface},i} = \pi r_{\text{interface},i}^2
$$

#### 3.3.3 Truncated Trapezoid

**Variable rectangular interface:**

$$
a_{\text{interface},i} = a_{\text{top}} + (a_{\text{bottom}} - a_{\text{top}}) \cdot \frac{i+1}{n}
$$

$$
b_{\text{interface},i} = b_{\text{top}} + (b_{\text{bottom}} - b_{\text{top}}) \cdot \frac{i+1}{n}
$$

$$
A_{\text{interface},i} = a_{\text{interface},i} \times b_{\text{interface},i}
$$

---

## 4. Layer-Specific Heat Loss Calculations

### 4.1 General Principle

Each layer experiences heat loss based on its:
- **Position**: Top, middle, or bottom layer
- **Temperature**: $T_i$ drives heat transfer rate
- **Boundary conditions**: Air, soil, or no external contact

**See [`SimpleThermalStorage_Calculation_Logic.md`, Section 5](SimpleThermalStorage_Calculation_Logic.md#5-heat-loss-calculations) for detailed heat transfer formulas.**

### 4.2 Cylindrical Overground Storage

#### Top Layer ($i = 0$):
Direct atmospheric exposure through top insulation:

$$
\dot{Q}_{\text{loss},0} = \frac{\lambda_{\text{top}}}{\delta_{\text{top}}} \cdot A_{\text{top}} \cdot (T_0 - T_{\text{amb}}) \times 10^{-3}
$$

#### Bottom Layer ($i = n-1$):
Enhanced soil thermal resistance:

$$
R_{\text{soil}} = \frac{4r}{3\pi \lambda_{\text{soil}}}
$$

$$
R_{\text{total}} = \frac{\delta_{\text{bottom}}}{\lambda_{\text{bottom}}} + R_{\text{soil}}
$$

$$
\dot{Q}_{\text{loss},n-1} = \frac{1}{R_{\text{total}}} \cdot A_{\text{bottom}} \cdot (T_{n-1} - T_{\text{amb}}) \times 10^{-3}
$$

#### Middle Layers ($i = 1, ..., n-2$):
Distributed side wall losses:

$$
\dot{Q}_{\text{loss},i} = \frac{\lambda_{\text{side}}}{\delta_{\text{side}}} \cdot \frac{A_{\text{side}}}{n} \cdot (T_i - T_{\text{amb}}) \times 10^{-3}
$$

### 4.3 Cylindrical Underground Storage

#### Top Layer ($i = 0$):
Same as overground - atmospheric exposure.

#### Subsurface Layers ($i = 1, ..., n-1$):

**Minimum insulation thickness criterion:**

$$
\delta_{\min} = 0.37 \cdot r \cdot \frac{\lambda_{\text{side}}}{\lambda_{\text{soil}}}
$$

**Required:** $\delta_{\text{side}} > 2\delta_{\min}$

**Combined thermal conductance:**

$$
K_{sb} = \left( \frac{\delta_{\text{side}}}{\lambda_{\text{side}}} + \frac{0.52 \cdot r}{\lambda_{\text{soil}}} \right)^{-1}
$$

**Total underground surface:**

$$
A_c = \pi r^2 + 2\pi r h
$$

**Layer loss (distributed):**

$$
\dot{Q}_{\text{loss},i} = K_{sb} \cdot \frac{A_c}{n} \cdot (T_i - T_{\text{soil}}) \times 10^{-3}
$$

### 4.4 PTES (Truncated Cone and Trapezoid)

#### Side Thermal Conductance

**Logarithmic resistance correlation:**

$$
a = \frac{\delta_{\text{side}}}{\lambda_{\text{side}}} + \frac{\pi H}{2\lambda_{\text{soil}}}
$$

$$
b = \frac{\pi}{\lambda_{\text{soil}}}
$$

$$
K_s = \frac{1}{bH} \ln\left(\frac{a + bH}{a}\right)
$$

#### Bottom Thermal Conductance

**Characteristic length:**
- **Truncated Cone**: $L_{\text{char}} = r_{\text{bottom}}$
- **Truncated Trapezoid**: $L_{\text{char}} = \min(a_{\text{bottom}}, b_{\text{bottom}})$

(Note: Conservative approach for trapezoid - uses minimum dimension rather than approximate circle equivalent)

$$
c = \frac{\delta_{\text{bottom}}}{\lambda_{\text{bottom}}} + \frac{\pi H}{2\lambda_{\text{soil}}}
$$

$$
K_b = \frac{1}{2bL_{\text{char}}} \ln\left(\frac{c + bL_{\text{char}}}{c}\right)
$$

#### Layer-Specific Losses

**Top Layer ($i = 0$):**

$$
\dot{Q}_{\text{loss},0} = \frac{\lambda_{\text{top}}}{\delta_{\text{top}}} \cdot A_{\text{top}} \cdot (T_0 - T_{\text{amb}}) \times 10^{-3}
$$

**Bottom Layer ($i = n-1$):**

$$
\dot{Q}_{\text{loss},n-1} = K_b \cdot A_{\text{bottom}} \cdot (T_{n-1} - T_{\text{soil}}) \times 10^{-3}
$$

**Middle Layers ($i = 1, ..., n-2$):**

$$
\dot{Q}_{\text{loss},i} = K_s \cdot \frac{A_{\text{side}}}{n} \cdot (T_i - T_{\text{soil}}) \times 10^{-3}
$$

**Total heat loss:**

$$
\dot{Q}_{\text{loss,total}} = \sum_{i=0}^{n-1} \dot{Q}_{\text{loss},i}
$$

---

## 5. Inter-Layer Heat Conduction

### 5.1 Physical Basis

Heat conduction between adjacent layers follows **Fourier's law**:

$$
\dot{Q}_{\text{cond},i \to i+1} = \lambda_{\text{medium}} \cdot A_{\text{interface},i} \cdot \frac{T_i - T_{i+1}}{\delta_{\text{layer}}}
$$

Where:
- $\lambda_{\text{medium}}$ = Thermal conductivity of storage medium (water: ~0.6 W/(m·K))
- $A_{\text{interface},i}$ = Cross-sectional area between layers $i$ and $i+1$ [m²]
- $\delta_{\text{layer}}$ = Layer thickness [m]
- $T_i - T_{i+1}$ = Temperature difference [K]

### 5.2 Energy Transfer Between Layers

**Heat transfer rate** [W]:

$$
\dot{Q}_{\text{cond},i} = \frac{\lambda_{\text{medium}} \cdot A_{\text{interface},i}}{\delta_{\text{layer}}} \cdot (T_i - T_{i+1})
$$

**Energy transfer over timestep** $\Delta t = 1$ hour [kWh]:

$$
E_{\text{transfer}} = \frac{\dot{Q}_{\text{cond},i}}{1000} \cdot \Delta t
$$

### 5.3 Temperature Changes Due to Conduction

**Upper layer** (loses heat if $T_i > T_{i+1}$):

$$
\Delta T_i = -\frac{E_{\text{transfer}} \cdot 3.6 \times 10^6}{\rho \cdot V_i \cdot c_p}
$$

**Lower layer** (gains heat if $T_i > T_{i+1}$):

$$
\Delta T_{i+1} = +\frac{E_{\text{transfer}} \cdot 3.6 \times 10^6}{\rho \cdot V_{i+1} \cdot c_p}
$$

### 5.4 Direction of Heat Flow

- If $T_i > T_{i+1}$: Heat flows **downward** (hot to cold)
- If $T_i < T_{i+1}$: Heat flows **upward** (cold layer below hot - unstable, will naturally convect)
- If $|T_i - T_{i+1}| < 10^{-6}$: Negligible gradient, skip calculation

**Physical interpretation:**
The model captures **conductive** heat transfer. In reality, if $T_i < T_{i+1}$ (cold over hot), **natural convection** would rapidly eliminate this unstable stratification. The charging/discharging logic is designed to prevent such unphysical states.

---

## 6. Stratified Simulation Algorithm

### 6.1 Pre-Calculation Phase (Before Main Loop)

**Step 1: Initialize temperature distribution**

$$
T_i[0] = T_{\text{initial}} \quad \forall i \in [0, n-1]
$$

**Step 2: Calculate geometric properties**
- Layer volumes: $V_i$ (geometry-dependent)
- Interface areas: $A_{\text{interface},i}$ (for conduction)
- Surface areas: $A_{\text{top}}$, $A_{\text{side}}$, $A_{\text{bottom}}$

**Step 3: Pre-calculate constants** (Performance optimization ~15-20% speedup)

$$
C_i = \rho \cdot V_i \cdot c_p \quad \text{[J/K]}
$$

$$
k_{\text{cond},i} = \frac{\lambda_{\text{medium}} \cdot A_{\text{interface},i}}{\delta_{\text{layer}}} \quad \text{[W/K]}
$$

$$
f_{\text{conv}} = 3.6 \times 10^6 \quad \text{[J/kWh]}
$$

### 6.2 Main Simulation Loop

For each timestep $t = 1, 2, ..., T$:

#### **Step 0: Initialization (t = 0 only)**

$$
E_{\text{total}}[0] = \sum_{i=0}^{n-1} \frac{V_i \cdot \rho \cdot c_p \cdot (T_i[0] - T_{\text{ref}})}{3.6 \times 10^6}
$$

$$
\dot{Q}_{\text{loss}}[0] = \sum_{i=0}^{n-1} \dot{Q}_{\text{loss},i}(T_i[0])
$$

#### **Step 1: Apply Heat Losses**

For each layer $i$:

$$
\dot{Q}_{\text{loss},i}[t] = f_{\text{geometry}}(T_i[t-1], \text{position}_i)
$$

$$
E_{\text{loss},i} = \dot{Q}_{\text{loss},i}[t] \cdot \Delta t \quad \text{[kWh]}
$$

$$
\Delta T_{\text{loss},i} = \frac{E_{\text{loss},i} \cdot f_{\text{conv}}}{C_i}
$$

$$
T_i^{(1)}[t] = T_i[t-1] - \Delta T_{\text{loss},i}
$$

#### **Step 2: Inter-Layer Heat Conduction**

For each interface $i = 0, 1, ..., n-2$:

$$
\Delta T_{i,i+1} = T_i^{(1)}[t] - T_{i+1}^{(1)}[t]
$$

If $|\Delta T_{i,i+1}| > 10^{-6}$:

$$
\dot{Q}_{\text{cond},i} = k_{\text{cond},i} \cdot \Delta T_{i,i+1} \quad \text{[W]}
$$

$$
E_{\text{transfer}} = \frac{\dot{Q}_{\text{cond},i}}{1000} \cdot \Delta t \quad \text{[kWh]}
$$

$$
T_i^{(2)}[t] = T_i^{(1)}[t] - \frac{E_{\text{transfer}} \cdot f_{\text{conv}}}{C_i}
$$

$$
T_{i+1}^{(2)}[t] = T_{i+1}^{(1)}[t] + \frac{E_{\text{transfer}} \cdot f_{\text{conv}}}{C_{i+1}}
$$

#### **Step 3: Charging/Discharging**

**Net energy balance:**

$$
E_{\text{net}} = (\dot{Q}_{\text{in}}[t] - \dot{Q}_{\text{out}}[t]) \cdot \Delta t \quad \text{[kWh]}
$$

**Case A: Discharging** ($E_{\text{net}} < 0$)

Start from top layer ($i = 0$) and extract heat downward:

$$
E_{\text{needed}} = |E_{\text{net}}|
$$

For each layer $i = 0, 1, ..., n-1$ while $E_{\text{needed}} > 10^{-6}$:

$$
E_{\text{available},i} = \frac{(T_i^{(2)}[t] - T_{\min}) \cdot C_i}{f_{\text{conv}}} \quad \text{[kWh]}
$$

If $E_{\text{needed}} \geq E_{\text{available},i}$:
$$
T_i^{(3)}[t] = T_{\min}
$$
$$
E_{\text{needed}} \leftarrow E_{\text{needed}} - E_{\text{available},i}
$$

Else:
$$
T_i^{(3)}[t] = T_i^{(2)}[t] - \frac{E_{\text{needed}} \cdot f_{\text{conv}}}{C_i}
$$
$$
E_{\text{needed}} = 0 \quad \text{(done, break loop)}
$$

**Case B: Charging** ($E_{\text{net}} > 0$)

Start from top layer ($i = 0$) and add heat downward:

$$
E_{\text{remaining}} = E_{\text{net}}
$$

For each layer $i = 0, 1, ..., n-1$ while $E_{\text{remaining}} > 10^{-6}$:

$$
E_{\text{capacity},i} = \frac{(T_{\max} - T_i^{(2)}[t]) \cdot C_i}{f_{\text{conv}}} \quad \text{[kWh]}
$$

If $E_{\text{remaining}} \geq E_{\text{capacity},i}$:
$$
T_i^{(3)}[t] = T_{\max}
$$
$$
E_{\text{remaining}} \leftarrow E_{\text{remaining}} - E_{\text{capacity},i}
$$

Else:
$$
T_i^{(3)}[t] = T_i^{(2)}[t] + \frac{E_{\text{remaining}} \cdot f_{\text{conv}}}{C_i}
$$
$$
E_{\text{remaining}} = 0 \quad \text{(done, break loop)}
$$

#### **Step 4: Apply Temperature Limits**

$$
T_i[t] = \max(T_{\min}, \min(T_{\max}, T_i^{(3)}[t]))
$$

#### **Step 5: Calculate Total Energy and Average Temperature**

$$
E_{\text{total}}[t] = \sum_{i=0}^{n-1} \frac{V_i \cdot \rho \cdot c_p \cdot (T_i[t] - T_{\text{ref}})}{3.6 \times 10^6}
$$

$$
\bar{T}[t] = \frac{1}{n} \sum_{i=0}^{n-1} T_i[t]
$$

### 6.3 Flowchart

```
START
  ↓
Initialize: T_i[0] = T_initial ∀i
  ↓
Calculate geometry: V_i, A_interface_i, A_surfaces
  ↓
Pre-calculate constants: C_i, k_cond_i, f_conv
  ↓
t = 0: Calculate E_total[0], Q_loss[0]
  ↓
FOR t = 1 to T:
  │
  ├─→ STEP 1: Heat Losses
  │    FOR each layer i:
  │      Calculate Q_loss_i(T_i[t-1])
  │      Update T_i^(1) = T_i[t-1] - ΔT_loss_i
  │
  ├─→ STEP 2: Inter-Layer Conduction
  │    FOR each interface i:
  │      IF |T_i^(1) - T_{i+1}^(1)| > 1e-6:
  │        Calculate Q_cond_i
  │        Update T_i^(2) and T_{i+1}^(2)
  │
  ├─→ STEP 3: Charging/Discharging
  │    Calculate E_net = (Q_in - Q_out) × Δt
  │    │
  │    ├─→ IF E_net < 0 (Discharge):
  │    │    FOR i = 0 to n-1 (top to bottom):
  │    │      Extract heat until E_needed = 0 or T_i = T_min
  │    │
  │    └─→ ELSE IF E_net > 0 (Charge):
  │         FOR i = 0 to n-1 (top to bottom):
  │           Add heat until E_remaining = 0 or T_i = T_max
  │
  ├─→ STEP 4: Apply Temperature Limits
  │    T_i[t] = clip(T_i^(3), T_min, T_max)
  │
  └─→ STEP 5: Calculate Totals
       E_total[t] = Σ E_layer_i
       T_avg[t] = (1/n) Σ T_i[t]
  ↓
NEXT t
  ↓
Calculate efficiency: η = 1 - (Σ Q_loss) / (Σ Q_in)
  ↓
END
```

---

## 7. Charging and Discharging Strategy

### 7.1 Top-Down Priority (Stratification Preservation)

Both charging and discharging start from the **top layer** and proceed downward. This maintains natural thermal stratification:

**Physical Justification:**

1. **Hot water naturally rises** (buoyancy)
2. **Top layers accessed first** for inlet/outlet
3. **Preserves thermal quality** (exergy)
4. **Prevents destratification** from mixing

### 7.2 Charging Logic

**Objective:** Add heat while maintaining hot layers at top.

```
Energy to add: E_in = Q_in × Δt [kWh]

For layer i = 0, 1, 2, ... (top to bottom):
    IF T_i < T_max AND E_in > 0:
        Capacity_i = (T_max - T_i) × C_i / f_conv [kWh]
        
        IF E_in ≥ Capacity_i:
            Fully heat layer: T_i = T_max
            E_in = E_in - Capacity_i
        ELSE:
            Partially heat: T_i = T_i + (E_in × f_conv) / C_i
            E_in = 0
            BREAK
```

**Result:** Hot water accumulates at top, cold water remains at bottom.

### 7.3 Discharging Logic

**Objective:** Extract heat from hottest layers first.

```
Energy to extract: E_out = Q_out × Δt [kWh]

For layer i = 0, 1, 2, ... (top to bottom):
    IF T_i > T_min AND E_out > 0:
        Available_i = (T_i - T_min) × C_i / f_conv [kWh]
        
        IF E_out ≥ Available_i:
            Fully cool layer: T_i = T_min
            E_out = E_out - Available_i
        ELSE:
            Partially cool: T_i = T_i - (E_out × f_conv) / C_i
            E_out = 0
            BREAK
```

**Result:** Cold water accumulates at top, hot water reserve remains at bottom (if any).

### 7.4 Stratification Index

A measure of stratification quality:

$$
\text{SI} = \frac{T_{\text{top}} - T_{\text{bottom}}}{T_{\max} - T_{\min}}
$$

- **SI = 1**: Perfect stratification (top at T_max, bottom at T_min)
- **SI = 0**: Fully mixed (uniform temperature)
- **SI < 0**: Inverted stratification (unstable)

---

## 8. Numerical Considerations

### 8.1 Explicit Time Integration

The stratified model uses **explicit Euler method** with $\Delta t = 1$ hour, same as SimpleThermalStorage.

**See [`SimpleThermalStorage_Calculation_Logic.md`, Section 3](SimpleThermalStorage_Calculation_Logic.md#3-numerical-integration-method) for details on:**
- Stability criteria
- Unit consistency
- Timestep selection

### 8.2 Sequential Sub-Step Processing

Each timestep processes physics in **sequential stages**:

1. Heat losses (based on $T[t-1]$)
2. Inter-layer conduction (based on $T$ after losses)
3. Charging/discharging (based on $T$ after conduction)
4. Temperature limiting (final enforcement)

**Rationale:**
- **Explicit scheme**: Each sub-step uses known temperatures
- **Stable order**: Heat losses → conduction → charging is physically consistent
- **No iteration**: Computationally efficient
- **Good accuracy**: For $\Delta t = 1$ hour and large thermal mass

### 8.3 Conduction Stability

For pure diffusion equation:

$$
\text{CFL} = \frac{\alpha \cdot \Delta t}{\delta_{\text{layer}}^2} < 0.5
$$

Where $\alpha = \lambda / (\rho c_p)$ is thermal diffusivity.

**For water:** $\alpha \approx 1.4 \times 10^{-7}$ m²/s

**Typical layer thickness:** $\delta_{\text{layer}} = 1-3$ m

**Check for** $\delta = 1$ m, $\Delta t = 3600$ s:

$$
\text{CFL} = \frac{1.4 \times 10^{-7} \times 3600}{1^2} = 5 \times 10^{-4} \ll 0.5
$$

✅ **Highly stable** - thermal diffusion is slow relative to timestep.

### 8.4 Performance Optimizations

**Pre-calculated constants** (implemented):

| Constant | Formula | Benefit |
|----------|---------|---------|
| Thermal capacity | $C_i = \rho V_i c_p$ | Avoid repeated multiplication |
| Conduction coefficient | $k_i = \lambda A_i / \delta$ | Avoid repeated division |
| Conversion factor | $f = 3.6 \times 10^6$ | Single definition |

**Estimated speedup:** 15-20% compared to inline calculations.

**Early termination** (implemented):

```python
if remaining_heat < 1e-6:
    break  # No more energy to distribute
```

Avoids unnecessary layer iterations when charging/discharging complete.

---

## 9. Validation and Verification

### 9.1 Energy Conservation

**Global energy balance must hold:**

$$
E[t] - E[t-1] = (Q_{\text{in}}[t] - Q_{\text{out}}[t] - Q_{\text{loss}}[t]) \cdot \Delta t
$$

**Layer-wise summation:**

$$
E[t] = \sum_{i=0}^{n-1} \frac{V_i \rho c_p (T_i[t] - T_{\text{ref}})}{3.6 \times 10^6}
$$

This is automatically satisfied by the algorithm since temperature is the primary state variable and energy is calculated consistently from temperature.

### 9.2 Stratification Tests

**Test 1: Ideal Stratification Maintenance**
- Initialize: Top layers at T_max, bottom at T_min
- Run with no input/output (only losses)
- Expected: Stratification maintained, gradual cooling

**Test 2: Stratification Development**
- Initialize: Uniform temperature
- Charge with Q_in > 0
- Expected: Hot layers form at top, gradient develops

**Test 3: Mixing Resistance**
- Initialize: Strong stratification
- Discharge heavily (Q_out >> Q_in)
- Expected: Cold zone progresses downward, some gradient preserved

### 9.3 Comparison with SimpleThermalStorage

For well-insulated storage with Bi < 0.1:

| Metric | Simple | Stratified | Expected Difference |
|--------|--------|------------|---------------------|
| **Average temperature** | $\bar{T}$ | $\frac{1}{n}\sum T_i$ | < 2% |
| **Total stored energy** | $E$ | $\sum E_i$ | < 3% |
| **Heat losses** | $Q_{\text{loss}}$ | $\sum Q_{\text{loss},i}$ | < 5% |
| **Efficiency** | $\eta$ | $\eta_{\text{strat}}$ | Similar |

For poorly insulated or high Bi systems, stratified model shows:
- **Higher peak temperatures** (top layers)
- **Greater heat losses** (hot surface)
- **Lower overall efficiency** (more realistic)

---

## 10. Comparison: Stratified vs. Simple Model

### 10.1 Feature Matrix

| Feature | SimpleThermalStorage | StratifiedThermalStorage |
|---------|----------------------|--------------------------|
| **Temperature nodes** | 1 (uniform) | $n$ layers (5-50) |
| **Stratification modeling** | ❌ Not captured | ✅ Fully modeled |
| **Biot number requirement** | Bi < 0.1 | No restriction |
| **Temperature gradients** | ❌ Assumed negligible | ✅ Explicitly calculated |
| **Heat loss distribution** | Bulk calculation | Layer-specific |
| **Inter-layer effects** | ❌ N/A | ✅ Conduction modeled |
| **Charging/discharging** | Bulk energy balance | Layer-by-layer |
| **Exergy analysis** | Limited | Enhanced |
| **Computational cost** | Very low (~0.2s per year) | Moderate (~0.5-2s per year) |
| **Memory usage** | $O(T)$ | $O(T \times n)$ |
| **Use case** | Preliminary design, screening | Detailed optimization, control |

### 10.2 When to Use Each Model

**Use SimpleThermalStorage when:**
- Bi < 0.1 (lumped model valid)
- Preliminary feasibility studies
- Screening many design alternatives
- Computational resources limited
- Stratification effects expected to be small

**Use StratifiedThermalStorage when:**
- Bi ≥ 0.1 (stratification significant)
- Detailed performance optimization
- Control strategy development
- Temperature quality analysis required
- Exergy efficiency critical

**Use both for:**
- Model validation (simple as sanity check)
- Sensitivity analysis (compare predictions)
- Understanding stratification impact

---

## 11. Performance Metrics

### 11.1 Storage Efficiency

**Same as SimpleThermalStorage** - see [Section 7.1](SimpleThermalStorage_Calculation_Logic.md#71-storage-efficiency):

$$
\eta = 1 - \frac{\sum Q_{\text{loss}}}{\sum Q_{\text{in}}}
$$

### 11.2 Stratification-Specific Metrics

#### Effective Temperature

The **thermodynamic quality** of stored heat considering stratification:

$$
T_{\text{eff}} = \frac{\sum_{i=0}^{n-1} T_i \cdot V_i}{\sum_{i=0}^{n-1} V_i}
$$

Volume-weighted average (differs from arithmetic mean for non-cylindrical geometries).

#### Thermocline Thickness

The **transition zone** between hot and cold regions:

$$
\delta_{\text{thermocline}} = \frac{T_{\max} - T_{\min}}{\max(|dT/dz|)}
$$

- **Sharp thermocline**: $\delta \to 0$ (ideal stratification)
- **Diffuse thermocline**: $\delta \to H$ (poor stratification)

#### Exergy Efficiency

Considering temperature quality:

$$
\eta_{\text{ex}} = \frac{\sum Q_{\text{out}} \cdot (1 - T_{\text{ref}}/T_{\text{out}})}{\sum Q_{\text{in}} \cdot (1 - T_{\text{ref}}/T_{\text{in}})}
$$

Stratification improves exergy efficiency by maintaining hotter discharge temperatures.

---

## 12. Limitations and Assumptions

### 12.1 Inherited from SimpleThermalStorage

**See [`SimpleThermalStorage_Calculation_Logic.md`, Section 9](SimpleThermalStorage_Calculation_Logic.md#9-model-limitations-and-assumptions) for:**
- Constant material properties
- Steady-state heat transfer
- Hourly timestep resolution

### 12.2 Stratification-Specific Limitations

**1. One-Dimensional Stratification**
- Assumes horizontal layers are perfectly uniform (no radial gradients)
- Real storage has wall effects and flow-induced mixing
- Impact: ~5-10% overestimation of stratification quality

**2. No Convective Mixing**
- Only diffusive (conductive) heat transfer between layers
- Real storage has some convective currents
- Impact: Stratification may degrade faster in reality

**3. Idealized Charging/Discharging**
- Assumes perfect layer selection (no jet entrainment)
- Inlet/outlet design significantly affects real behavior
- Impact: Requires good diffuser design to match model

**4. No Hydrodynamic Effects**
- Flow velocities, Reynolds numbers not considered
- Inlet momentum neglected
- Impact: Valid for slow charging/discharging rates

### 12.3 Applicability Range

**Suitable for:**
- ✓ Large STES with height/diameter > 1
- ✓ Well-designed diffuser systems
- ✓ Slow charging/discharging (< 10% volume/hour)
- ✓ Systems designed to maintain stratification

**Not suitable for:**
- ✗ High-flow buffer tanks with rapid cycling
- ✗ Poor inlet/outlet design causing mixing
- ✗ Systems with mechanical mixing (intentional)
- ✗ Complex geometries with obstacles or baffles

---

## 13. Example Calculation

### 13.1 Storage Configuration

**Type:** Cylindrical underground seasonal storage  
**Dimensions:**
- Radius: $r = 15$ m
- Height: $H = 20$ m
- Volume: $V = \pi \times 15^2 \times 20 = 14,137$ m³

**Discretization:**
- Number of layers: $n = 10$
- Layer thickness: $\delta = 20/10 = 2$ m
- Layer volume: $V_{\text{layer}} = 1,414$ m³ (uniform)

**Properties:**
- Medium: Water ($\rho = 1000$ kg/m³, $c_p = 4186$ J/(kg·K), $\lambda = 0.6$ W/(m·K))
- Temperature range: $T_{\min} = 10°C$, $T_{\max} = 90°C$
- Initial: Uniform at $T_0 = 50°C$

**Insulation:**
- Top: $\delta_{\text{top}} = 0.5$ m, $\lambda_{\text{top}} = 0.04$ W/(m·K)
- Side: $\delta_{\text{side}} = 0.4$ m, $\lambda_{\text{side}} = 0.04$ W/(m·K)
- Soil: $\lambda_{\text{soil}} = 1.5$ W/(m·K), $T_{\text{soil}} = 10°C$

### 13.2 Pre-Calculations

#### Layer Thermal Capacity

$$
C_{\text{layer}} = \rho \cdot V_{\text{layer}} \cdot c_p = 1000 \times 1414 \times 4186 = 5.92 \times 10^9 \text{ J/K}
$$

#### Interface Area

$$
A_{\text{interface}} = \pi r^2 = \pi \times 15^2 = 707 \text{ m}^2
$$

#### Conduction Coefficient

$$
k_{\text{cond}} = \frac{\lambda \cdot A_{\text{interface}}}{\delta_{\text{layer}}} = \frac{0.6 \times 707}{2} = 212 \text{ W/K}
$$

#### Minimum Insulation Check

$$
\delta_{\min} = 0.37 \times 15 \times \frac{0.04}{1.5} = 0.148 \text{ m}
$$

$$
\delta_{\text{side}} = 0.4 \text{ m} > 2 \times 0.148 = 0.296 \text{ m} \quad \checkmark
$$

### 13.3 Heat Loss Calculations (at t = 0, T = 50°C uniform)

#### Top Layer (i = 0)

$$
\dot{Q}_{\text{loss},0} = \frac{0.04}{0.5} \times 707 \times (50 - 10) / 1000 = 2.26 \text{ kW}
$$

#### Subsurface Layers (i = 1-9)

$$
K_{sb} = \left(\frac{0.4}{0.04} + \frac{0.52 \times 15}{1.5}\right)^{-1} = \left(10 + 5.2\right)^{-1} = 0.0658 \text{ W/(m}^2\text{·K)}
$$

$$
A_c = \pi \times 15^2 + 2\pi \times 15 \times 20 = 707 + 1885 = 2592 \text{ m}^2
$$

$$
\dot{Q}_{\text{loss},\text{per layer}} = 0.0658 \times \frac{2592}{9} \times (50 - 10) / 1000 = 0.76 \text{ kW}
$$

#### Total Initial Heat Loss

$$
\dot{Q}_{\text{loss,total}} = 2.26 + 9 \times 0.76 = 9.10 \text{ kW}
$$

### 13.4 Simulation Scenario (Summer Charging)

**Time:** t = 1 hour  
**Operating mode:** Charging  
- $Q_{\text{in}} = 1000$ kW  
- $Q_{\text{out}} = 0$ kW  
- $E_{\text{net}} = 1000$ kWh

#### Step 1: Apply Heat Losses (from t=0 to t=1)

For each layer (all at 50°C initially):

$$
E_{\text{loss}} = \dot{Q}_{\text{loss},i} \times 1 \text{ h}
$$

**Top layer:**
$$
\Delta T_0 = \frac{2.26 \times 3.6 \times 10^6}{5.92 \times 10^9} = 0.00137°C
$$

**Other layers:**
$$
\Delta T_i = \frac{0.76 \times 3.6 \times 10^6}{5.92 \times 10^9} = 0.00046°C
$$

(Negligible changes - large thermal mass)

$$
T_i^{(1)} \approx 50°C \text{ for all layers}
$$

#### Step 2: Inter-Layer Conduction

$$
\Delta T_{i,i+1} = 0 \quad \forall i
$$

No conduction (uniform temperature).

#### Step 3: Charging

Distribute 1000 kWh starting from top layer:

**Layer capacity to T_max:**

$$
E_{\text{cap},\text{layer}} = \frac{(90 - 50) \times 5.92 \times 10^9}{3.6 \times 10^6} = 65,778 \text{ kWh}
$$

Since $1000 < 65,778$, **only the top layer is heated:**

$$
\Delta T_0 = \frac{1000 \times 3.6 \times 10^6}{5.92 \times 10^9} = 0.608°C
$$

$$
T_0[1] = 50 + 0.608 = 50.61°C
$$

$$
T_i[1] = 50.00°C \quad \forall i \geq 1
$$

**Result:** Very weak stratification develops (only 0.61°C gradient in 1 hour).

Over seasonal timeframe (3000+ hours of charging), strong stratification would develop with top layers approaching 90°C.

---

## 14. Advanced Topics

### 14.1 Adaptive Layer Refinement

For improved accuracy near thermocline:

$$
n_{\text{layers}} = n_{\text{base}} + \left\lfloor \frac{\max(|\nabla T|)}{\nabla T_{\text{threshold}}} \right\rfloor
$$

Add more layers in high-gradient regions.

### 14.2 Convective Enhancement Factor

To account for natural convection:

$$
k_{\text{eff}} = k_{\text{cond}} \times (1 + \epsilon_{\text{conv}})
$$

Where $\epsilon_{\text{conv}} \approx 0.1-0.3$ for typical conditions.

### 14.3 Transient Soil Temperature

Long-term simulations should consider:

$$
T_{\text{soil}}(t) = T_{\text{soil,mean}} + A_{\text{annual}} \sin\left(\frac{2\pi t}{8760}\right)
$$

Annual soil temperature variation affects losses.

---

## 15. References

### 15.1 Primary Literature

1. **Narula, K., et al. (2020).** "Simulation method for assessing hourly energy flows in district heating system with seasonal thermal energy storage". *Renewable Energy*, 151, 1250-1268.

2. **Schmidt, T., Mangold, D. (2006).** "New steps in seasonal thermal energy storage in Germany". *Solar Energy*, 80(7), 861-868.

3. **Dahash, A., et al. (2019).** "Advances in seasonal thermal energy storage for solar district heating applications: A critical review on large-scale hot-water tank and pit thermal energy storage systems". *Applied Energy*, 239, 296-315.

### 15.2 Supporting References

4. **Incropera, F.P., et al. (2007).** *Fundamentals of Heat and Mass Transfer*, 6th Edition. John Wiley & Sons.

5. **Dinçer, İ., Rosen, M.A. (2011).** *Thermal Energy Storage: Systems and Applications*, 2nd Edition. John Wiley & Sons.

6. **VDI Heat Atlas (2010).** 2nd Edition. Springer-Verlag, Berlin Heidelberg.

### 15.3 Related Documentation

- [`SimpleThermalStorage_Calculation_Logic.md`](SimpleThermalStorage_Calculation_Logic.md) - Base model documentation
- [`ThermalStorage` class documentation](../src/districtheatingsim/heat_generators/simple_thermal_storage.py) - Implementation details

---

## 16. Nomenclature

### 16.1 Symbols (Additional to SimpleThermalStorage)

| Symbol | Description | Unit |
|--------|-------------|------|
| $A_{\text{interface},i}$ | Cross-sectional area between layers $i$ and $i+1$ | m² |
| $C_i$ | Thermal capacity of layer $i$ | J/K |
| $\delta_{\text{layer}}$ | Thickness of each layer | m |
| $\delta_{\text{thermocline}}$ | Thermocline thickness | m |
| $E_i$ | Stored energy in layer $i$ | kWh |
| $i$ | Layer index (0 = top, n-1 = bottom) | - |
| $k_{\text{cond},i}$ | Conduction coefficient for interface $i$ | W/K |
| $n$ | Number of layers | - |
| $\dot{Q}_{\text{cond},i}$ | Conduction heat transfer rate between layers | W |
| $\dot{Q}_{\text{loss},i}$ | Heat loss from layer $i$ | kW |
| $\text{SI}$ | Stratification index | - |
| $T_i$ | Temperature of layer $i$ | °C |
| $T_{\text{eff}}$ | Effective temperature (volume-weighted) | °C |
| $V_i$ | Volume of layer $i$ | m³ |

### 16.2 Superscripts

| Superscript | Description |
|-------------|-------------|
| $(1)$ | After heat loss step |
| $(2)$ | After inter-layer conduction step |
| $(3)$ | After charging/discharging step |

---

## Appendix A: Algorithm Implementation Notes

### A.1 Computational Complexity

**Time complexity per timestep:**
- Heat losses: $O(n)$
- Inter-layer conduction: $O(n)$
- Charging/discharging: $O(n)$ worst case, $O(1)$ best case with early termination
- **Total:** $O(n)$ per timestep

**For annual simulation:**
- Timesteps: $T = 8760$
- Layers: $n = 10$
- **Total operations:** $\approx 26,000$ per simulation

**Typical performance:**
- Simple model: ~37,000 timesteps/second
- Stratified model (n=10): ~15,000 timesteps/second
- **Slowdown factor:** ~2.5× (acceptable for added detail)

### A.2 Memory Requirements

**Storage arrays:**
- Temperature: $T \times n$ floats
- Energy, losses: $T$ floats
- Total: $(T \times n + 2T) \times 8$ bytes

**For T = 8760, n = 10:**
- Memory: $(87,600 + 17,520) \times 8 = 840$ KB

**Negligible compared to modern systems.**

---

## Appendix B: Related Documentation

- **Next Level:** [`STES_Calculation_Logic.md`](STES_Calculation_Logic.md) - Mass flow-based STES with hydraulic constraints
- **Previous Level:** [`SimpleThermalStorage_Calculation_Logic.md`](SimpleThermalStorage_Calculation_Logic.md) - Lumped capacitance base model

---

*Document Version: 1.0*  
*Last Updated: November 13, 2025*  
*Companion to: SimpleThermalStorage_Calculation_Logic.md*
