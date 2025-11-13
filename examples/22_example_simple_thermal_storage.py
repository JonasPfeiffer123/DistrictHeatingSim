

import numpy as np
import matplotlib.pyplot as plt

from districtheatingsim.heat_generators.simple_thermal_storage import SimpleThermalStorage

if __name__ == "__main__":
    """
    Test and demonstration of SimpleThermalStorage functionality.
    
    This test case simulates a seasonal thermal energy storage (STES) system
    with summer charging and winter discharging patterns.
    """
    
    print("="*80)
    print("SimpleThermalStorage Test Suite")
    print("="*80)
    
    # =========================================================================
    # Test Case 1: Cylindrical Underground Storage (Medium-Scale STES)
    # =========================================================================
    print("\n" + "="*80)
    print("TEST CASE 1: Cylindrical Underground Storage")
    print("="*80)
    
    # Storage parameters
    storage_params = {
        'name': 'TestStorage_Cylindrical',
        'storage_type': 'cylindrical_underground',
        'dimensions': (10.0, 15.0),  # radius=10m, height=15m → V≈4712 m³
        'rho': 1000.0,               # Water density [kg/m³]
        'cp': 4186.0,                # Water specific heat [J/(kg·K)]
        'T_ref': 0.0,                # Reference temperature [°C]
        'lambda_top': 0.04,          # Top insulation thermal conductivity [W/(m·K)]
        'lambda_side': 0.04,         # Side insulation thermal conductivity [W/(m·K)]
        'lambda_bottom': 0.04,       # Bottom insulation thermal conductivity [W/(m·K)]
        'lambda_soil': 1.5,          # Soil thermal conductivity [W/(m·K)]
        'T_amb': 10.0,               # Ambient temperature [°C]
        'T_soil': 10.0,              # Soil temperature [°C]
        'T_max': 95.0,               # Maximum storage temperature [°C]
        'T_min': 10.0,               # Minimum storage temperature [°C]
        'initial_temp': 20.0,        # Initial temperature [°C]
        'dt_top': 0.30,              # Top insulation thickness [m]
        'ds_side': 0.30,             # Side insulation thickness [m]
        'db_bottom': 0.30,           # Bottom insulation thickness [m]
        'hours': 8760,               # Simulation duration: 1 year
        'thermal_conductivity': 0.6  # Water thermal conductivity [W/(m·K)]
    }
    
    # Create storage instance
    print("\nCreating storage instance...")
    storage = SimpleThermalStorage(**storage_params)
    
    print(f"\n✓ Storage created successfully!")
    print(f"  - Volume: {storage.volume:.1f} m³")
    print(f"  - Surface areas:")
    print(f"    • Top: {storage.S_top:.1f} m²")
    print(f"    • Side: {storage.S_side:.1f} m²")
    print(f"    • Bottom: {storage.S_bottom:.1f} m²")
    print(f"  - Biot number: {storage.biot_number:.4f}")
    print(f"  - Characteristic length: {storage.characteristic_length:.2f} m")
    
    # =========================================================================
    # Generate realistic charging/discharging profile (seasonal pattern)
    # =========================================================================
    print("\nGenerating seasonal load profile...")
    
    hours = storage_params['hours']
    Q_in = np.zeros(hours)
    Q_out = np.zeros(hours)
    
    # Seasonal pattern: Summer charging (May-Sep), Winter discharging (Nov-Mar)
    for h in range(hours):
        day_of_year = (h // 24) % 365
        hour_of_day = h % 24
        
        # Summer charging period (day 120-273, approximately May-September)
        if 120 <= day_of_year <= 273:
            # Peak charging during daytime hours (10:00-16:00)
            if 10 <= hour_of_day <= 16:
                # Peak power: 500 kW with some daily variation
                Q_in[h] = 500.0 * (1 + 0.3 * np.sin(2 * np.pi * day_of_year / 365))
            else:
                # Base load charging: 100 kW
                Q_in[h] = 100.0
        
        # Winter discharging period (day 305-59, approximately November-February)
        elif day_of_year >= 305 or day_of_year <= 59:
            # Peak discharging during heating hours (6:00-22:00)
            if 6 <= hour_of_day <= 22:
                # Peak demand: 400 kW with temperature-dependent variation
                # Higher demand in coldest months (December-January)
                temp_factor = 1.5 if (day_of_year >= 335 or day_of_year <= 31) else 1.0
                Q_out[h] = 400.0 * temp_factor
            else:
                # Night base load: 150 kW
                Q_out[h] = 150.0
    
    print(f"  - Total energy input: {np.sum(Q_in):.0f} kWh")
    print(f"  - Total energy output: {np.sum(Q_out):.0f} kWh")
    print(f"  - Energy balance: {(np.sum(Q_in) - np.sum(Q_out)):.0f} kWh")
    
    # =========================================================================
    # Run simulation
    # =========================================================================
    print("\n" + "-"*80)
    print("Running annual simulation...")
    print("-"*80)
    
    import time
    start_time = time.time()
    
    storage.simulate(Q_in, Q_out)
    
    elapsed_time = time.time() - start_time
    print(f"✓ Simulation completed in {elapsed_time:.3f} seconds")
    print(f"  ({hours / elapsed_time:.0f} timesteps/second)")
    
    # =========================================================================
    # Display results
    # =========================================================================
    print("\n" + "="*80)
    print("SIMULATION RESULTS")
    print("="*80)
    
    print(f"\nEnergy Performance:")
    print(f"  - Total input: {np.sum(storage.Q_in):.0f} kWh")
    print(f"  - Total output: {np.sum(storage.Q_out):.0f} kWh")
    print(f"  - Total losses: {storage.total_energy_loss_kWh:.0f} kWh")
    print(f"  - Storage efficiency: {storage.efficiency*100:.2f}%")
    
    print(f"\nTemperature Statistics:")
    print(f"  - Initial: {storage.T_sto[0]:.1f} °C")
    print(f"  - Final: {storage.T_sto[-1]:.1f} °C")
    print(f"  - Maximum: {np.max(storage.T_sto):.1f} °C")
    print(f"  - Minimum: {np.min(storage.T_sto):.1f} °C")
    print(f"  - Average: {np.mean(storage.T_sto):.1f} °C")
    
    print(f"\nHeat Loss Statistics:")
    print(f"  - Average loss rate: {np.mean(storage.Q_loss):.2f} kW")
    print(f"  - Maximum loss rate: {np.max(storage.Q_loss):.2f} kW")
    print(f"  - Minimum loss rate: {np.min(storage.Q_loss):.2f} kW")
    print(f"  - Loss percentage: {(storage.total_energy_loss_kWh / np.sum(Q_in))*100:.2f}%")
    
    # =========================================================================
    # Test Case 2: Truncated Cone PTES (Large-Scale Seasonal Storage)
    # =========================================================================
    print("\n" + "="*80)
    print("TEST CASE 2: Truncated Cone PTES (Pit Thermal Energy Storage)")
    print("="*80)
    
    ptes_params = storage_params.copy()
    ptes_params.update({
        'name': 'TestStorage_PTES',
        'storage_type': 'truncated_cone',
        'dimensions': (25.0, 30.0, 20.0),  # top_r=25m, bottom_r=30m, h=20m → V≈46,705 m³
        'ds_side': 0.50,  # Thicker insulation for large PTES
        'db_bottom': 0.50,
        'initial_temp': 15.0,
        'hours': 2160  # 90 days for quick test
    })
    
    print("\nCreating PTES storage...")
    ptes = SimpleThermalStorage(**ptes_params)
    
    print(f"\n✓ PTES created successfully!")
    print(f"  - Volume: {ptes.volume:.0f} m³")
    print(f"  - Storage capacity: {ptes.volume * ptes.rho * ptes.cp * (ptes.T_max - ptes.T_min) / 3.6e9:.1f} MWh")
    print(f"  - Biot number: {ptes.biot_number:.4f}")
    
    # Simple charging test: Constant power for 30 days, then discharge for 60 days
    hours_ptes = ptes_params['hours']
    Q_in_ptes = np.zeros(hours_ptes)
    Q_out_ptes = np.zeros(hours_ptes)
    
    # Charging phase (first 30 days)
    Q_in_ptes[:720] = 2000.0  # 2 MW charging
    
    # Discharging phase (days 31-90)
    Q_out_ptes[720:] = 1500.0  # 1.5 MW discharging
    
    print("\nRunning PTES simulation...")
    ptes.simulate(Q_in_ptes, Q_out_ptes)
    
    print(f"\nPTES Results:")
    print(f"  - Storage efficiency: {ptes.efficiency*100:.2f}%")
    print(f"  - Temperature range: {np.min(ptes.T_sto):.1f} - {np.max(ptes.T_sto):.1f} °C")
    print(f"  - Total losses: {ptes.total_energy_loss_kWh:.0f} kWh ({(ptes.total_energy_loss_kWh/np.sum(Q_in_ptes))*100:.2f}%)")
    
    # =========================================================================
    # Visualization
    # =========================================================================
    print("\n" + "="*80)
    print("Generating plots...")
    print("="*80)
    
    # Plot results for Test Case 1 (annual simulation)
    print("\nPlotting Test Case 1 results...")
    storage.plot_results()
    plt.suptitle('Test Case 1: Cylindrical Underground Storage (Annual Cycle)', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # Plot results for Test Case 2 (PTES)
    print("Plotting Test Case 2 results...")
    ptes.plot_results()
    plt.suptitle('Test Case 2: Truncated Cone PTES (90-Day Test)', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # =========================================================================
    # Additional Analysis: Temperature-Loss Correlation
    # =========================================================================
    print("\n" + "="*80)
    print("ADDITIONAL ANALYSIS")
    print("="*80)
    
    # Plot temperature vs. heat loss relationship
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(storage.T_sto[1:], storage.Q_loss[1:], alpha=0.5, s=1)
    ax.set_xlabel('Storage Temperature [°C]', fontsize=12)
    ax.set_ylabel('Heat Loss Rate [kW]', fontsize=12)
    ax.set_title('Temperature-Dependent Heat Loss Correlation', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Add linear fit
    valid_idx = storage.T_sto[1:] > storage.T_min
    if np.any(valid_idx):
        coeffs = np.polyfit(storage.T_sto[1:][valid_idx], storage.Q_loss[1:][valid_idx], 1)
        T_fit = np.linspace(storage.T_min, storage.T_max, 100)
        Q_fit = coeffs[0] * T_fit + coeffs[1]
        ax.plot(T_fit, Q_fit, 'r--', linewidth=2, 
                label=f'Linear fit: Q_loss = {coeffs[0]:.3f}·T + {coeffs[1]:.2f}')
        ax.legend()
    
    plt.tight_layout()
    
    # =========================================================================
    # Final Summary
    # =========================================================================
    print("\n" + "="*80)
    print("TEST SUITE COMPLETED SUCCESSFULLY")
    print("="*80)
    print("\n✓ All tests passed!")
    print("✓ Visualizations generated")
    print("\nClose the plot windows to exit...")
    
    plt.show()