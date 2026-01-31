"""
Stratified Thermal Storage Module
==================================

Stratified STES with multi-layer temperature distribution modeling.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

.. note:: Based on Narula et al., Renewable Energy 151 (2020), DOI: 10.1016/j.renene.2019.11.121
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Dict, Any, List, Optional, Union

from districtheatingsim.heat_generators.simple_thermal_storage import ThermalStorage

class StratifiedThermalStorage(ThermalStorage):
    """
    Stratified thermal storage with multi-layer temperature modeling.

    .. note::
       Extends ThermalStorage with layer-specific heat losses and thermal gradients.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize stratified thermal storage with layer geometry calculations.

        .. note::
           Extends ThermalStorage with stratification-specific setup and visualization flags.
        """
        super().__init__(*args, **kwargs)
        self.calculate_layer_thickness()
        
        # Initialize visualization flags
        self.labels_exist = False
        self.colorbar_exists = False

    def calculate_layer_thickness(self) -> None:
        """
        Calculate thickness and volume of each stratification layer based on storage geometry.

        :raises ValueError: If storage_type unsupported for layer calculations
        :raises IndexError: If dimensions array lacks required geometric parameters

        .. note::
           Uniform layer thickness for all geometries. Variable volumes for non-cylindrical shapes (frustum/prismoidal formulas).
        """
        # Extract height dimension (common for all non-cylindrical geometries)
        if self.storage_type == "cylindrical":
            height = self.dimensions[1]  # radius, height
        else:
            height = self.dimensions[2]  # Common for cone and trapezoid: ..., height
            
        # Calculate uniform layer thickness
        self.layer_thickness = height / self.num_layers
        
        if self.storage_type == "cylindrical":
            # Cylindrical storage: uniform volume per layer
            self.layer_volume = np.full(self.num_layers, self.volume / self.num_layers)

        elif self.storage_type == "truncated_cone":
            # Truncated cone: calculate individual layer volumes using frustum formula
            r1, r2 = self.dimensions[0], self.dimensions[1]  # Top and bottom radii
            layer_volumes = []
            
            for i in range(self.num_layers):
                # Linear interpolation of radii for each layer
                r_top = r1 + (r2 - r1) * (i / self.num_layers)
                r_bottom = r1 + (r2 - r1) * ((i + 1) / self.num_layers)
                
                # Frustum volume formula: V = (π × h / 3) × (r1² + r2² + r1×r2)
                layer_volume = (np.pi * self.layer_thickness / 3) * (
                    r_top**2 + r_bottom**2 + r_top * r_bottom
                )
                layer_volumes.append(layer_volume)

            self.layer_volume = np.array(layer_volumes)

        elif self.storage_type == "truncated_trapezoid":
            # Truncated trapezoid: calculate individual layer volumes using prismoidal formula
            a1, b1 = self.dimensions[0], self.dimensions[1]  # Top length and width
            a2, b2 = self.dimensions[2], self.dimensions[3]  # Bottom length and width
            layer_volumes = []
            
            for i in range(self.num_layers):
                # Linear interpolation of dimensions for each layer
                a_top = a1 + (a2 - a1) * (i / self.num_layers)
                b_top = b1 + (b2 - b1) * (i / self.num_layers)
                a_bottom = a1 + (a2 - a1) * ((i + 1) / self.num_layers)
                b_bottom = b1 + (b2 - b1) * ((i + 1) / self.num_layers)
                
                # Calculate cross-sectional areas
                A_top = a_top * b_top
                A_bottom = a_bottom * b_bottom
                
                # Prismoidal volume formula: V = (h/3) × (A1 + A2 + √(A1×A2))
                layer_volume = (self.layer_thickness / 3) * (
                    A_top + A_bottom + np.sqrt(A_top * A_bottom)
                )
                layer_volumes.append(layer_volume)
            
            self.layer_volume = np.array(layer_volumes)

        else:
            raise ValueError(f"Unsupported storage type '{self.storage_type}' for layer thickness calculation")

    def calculate_stratified_heat_loss(self, T_sto_layers: np.ndarray) -> float:
        """
        Calculate layer-specific heat losses in stratified storage system.

        :param T_sto_layers: Temperature array for each storage layer (°C)
        :type T_sto_layers: numpy.ndarray
        :return: Total heat loss from all layers (kW)
        :rtype: float
        :raises ValueError: If insulation thickness below minimum for underground storage
        :raises IndexError: If T_sto_layers length doesn't match num_layers

        .. note::
           Accounts for geometry, insulation, and boundary conditions (above-ground vs underground). Stores layer-specific losses in Q_loss_layers.
        """
        # Initialize heat loss array for each layer
        self.Q_loss_layers = np.zeros(len(T_sto_layers))
        
        # Calculate layer-specific heat losses based on storage configuration
        for i, T_layer in enumerate(T_sto_layers):
            
            if self.storage_type == "cylindrical_overground":
                # Above-ground cylindrical storage heat losses
                if i == 0:  # Top layer - atmospheric exposure
                    Q_loss_top = (self.lambda_top / self.dt_top) * self.S_top * (T_layer - self.T_amb) / 1000
                    self.Q_loss_layers[i] = Q_loss_top
                    
                elif i == len(T_sto_layers) - 1:  # Bottom layer - enhanced soil resistance
                    # Enhanced soil thermal resistance for bottom contact
                    R_soil_enhanced = 4 * self.dimensions[0] / (3 * np.pi * self.lambda_soil)
                    R_total = self.db_bottom / self.lambda_bottom + R_soil_enhanced
                    Q_loss_bottom = (1 / R_total) * self.S_bottom * (T_layer - self.T_amb) / 1000
                    self.Q_loss_layers[i] = Q_loss_bottom
                    
                else:  # Side layers - distributed wall losses
                    Q_loss_side = (self.lambda_side / self.ds_side) * (T_layer - self.T_amb) * self.S_side / len(T_sto_layers) / 1000
                    self.Q_loss_layers[i] = Q_loss_side

            elif self.storage_type == "cylindrical_underground":
                # Underground cylindrical storage heat losses
                R = self.dimensions[0]  # Radius
                H = self.dimensions[1]  # Height
                
                # Minimum insulation thickness validation
                d_min = (self.lambda_side / self.lambda_soil) * R * 0.37
                if self.ds_side <= 2 * d_min:
                    raise ValueError(f"Insulation thickness {self.ds_side:.3f}m too small. "
                                   f"Minimum required: {2*d_min:.3f}m")
                
                # Combined thermal resistance for underground portions
                K_sb = (self.ds_side / self.lambda_side + 0.52 * R / self.lambda_soil)**(-1)
                S_c = np.pi * R**2 + 2 * np.pi * R * H  # Total underground surface area

                if i == 0:  # Top layer - atmospheric exposure
                    Q_loss_top = (self.lambda_top / self.dt_top) * self.S_top * (T_layer - self.T_amb) / 1000
                    self.Q_loss_layers[i] = Q_loss_top
                else:  # Underground layers - combined side and bottom resistance
                    Q_loss_sb = K_sb * S_c * (T_layer - self.T_soil) / len(T_sto_layers) / 1000
                    self.Q_loss_layers[i] = Q_loss_sb

            elif self.storage_type == "truncated_cone" or self.storage_type == "truncated_trapezoid":
                # PTES heat losses with geometry-dependent soil thermal resistance
                H = self.dimensions[2]  # Storage height
                
                # Side thermal resistance calculation
                a = self.ds_side / self.lambda_side + np.pi * H / (2 * self.lambda_soil)
                b = np.pi / self.lambda_soil
                K_s = (1 / (b * H)) * np.log((a + b * H) / a)
                
                # Bottom thermal resistance calculation
                bottom_radius = self.dimensions[1] if self.storage_type == "truncated_cone" else np.sqrt(self.dimensions[2] * self.dimensions[3] / np.pi)
                c = self.db_bottom / self.lambda_bottom + np.pi * H / (2 * self.lambda_soil)
                K_b = (1 / (2 * b * bottom_radius)) * np.log((c + b * bottom_radius) / c)

                if i == 0:  # Top layer - atmospheric exposure
                    Q_loss_top = (self.lambda_top / self.dt_top) * self.S_top * (T_layer - self.T_amb) / 1000
                    self.Q_loss_layers[i] = Q_loss_top
                    
                elif i == len(T_sto_layers) - 1:  # Bottom layer - enhanced soil resistance
                    Q_loss_bottom = K_b * self.S_bottom * (T_layer - self.T_soil) / 1000
                    self.Q_loss_layers[i] = Q_loss_bottom
                    
                else:  # Side layers - distributed soil contact losses
                    Q_loss_side = K_s * self.S_side * (T_layer - self.T_soil) / len(T_sto_layers) / 1000
                    self.Q_loss_layers[i] = Q_loss_side

        return np.sum(self.Q_loss_layers)

    def simulate_stratified(self, Q_in: np.ndarray, Q_out: np.ndarray) -> None:
        """
        Simulate stratified thermal storage with multi-layer temperature dynamics.

        :param Q_in: Heat input power time series (kW)
        :type Q_in: numpy.ndarray
        :param Q_out: Heat output power time series (kW)
        :type Q_out: numpy.ndarray
        :raises ValueError: If Q_in and Q_out have different lengths or invalid values
        :raises RuntimeError: If simulation encounters numerical instability

        .. note::
           Includes thermal stratification effects, layer-specific heat losses, inter-layer conduction, and realistic charging/discharging. Top-down charging and discharging with temperature constraints.
        """
        # Store input arrays and validate dimensions
        self.Q_in = np.asarray(Q_in)
        self.Q_out = np.asarray(Q_out)
        
        if len(self.Q_in) != len(self.Q_out):
            raise ValueError("Q_in and Q_out must have the same length")
        
        # Initialize simulation arrays
        self.T_sto_layers = np.full((self.hours, self.num_layers), self.initial_temp)
        heat_stored_per_layer = np.zeros(self.num_layers)

        # Main simulation loop
        for t in range(self.hours):
            # Calculate heat losses based on current layer temperatures
            if t == 0:
                self.Q_loss[t] = self.calculate_stratified_heat_loss(self.T_sto_layers[t])
            else:
                self.Q_loss[t] = self.calculate_stratified_heat_loss(self.T_sto_layers[t-1])
            
            if t == 0:
                # Initialize stored energy distribution
                self.Q_sto[t] = self.volume * self.rho * self.cp * (self.initial_temp - self.T_ref) / 3.6e6
                heat_stored_per_layer[:] = self.Q_sto[t] / self.num_layers

            else:
                # Apply heat losses to each layer
                for i in range(self.num_layers):
                    Q_loss_layer = self.Q_loss_layers[i]  # Heat loss in kW
                    heat_stored_per_layer[i] -= Q_loss_layer / 1000  # Convert to kWh
                    
                    # Update temperature based on heat loss
                    if self.layer_volume[i] > 0:
                        delta_T = (Q_loss_layer * 3.6e6) / (self.layer_volume[i] * self.rho * self.cp)
                        self.T_sto_layers[t, i] = self.T_sto_layers[t-1, i] - delta_T
                    else:
                        self.T_sto_layers[t, i] = self.T_sto_layers[t-1, i]

                # Calculate inter-layer heat conduction
                for i in range(self.num_layers - 1):
                    delta_T = self.T_sto_layers[t-1, i] - self.T_sto_layers[t-1, i+1]
                    if abs(delta_T) > 1e-6:  # Avoid numerical issues
                        heat_transfer = (self.thermal_conductivity * self.S_side * delta_T / 
                                       self.layer_thickness)  # W
                        heat_transfer_kWh = heat_transfer / 1000  # kWh per hour
                        
                        # Transfer heat between layers
                        heat_stored_per_layer[i] -= heat_transfer_kWh
                        heat_stored_per_layer[i+1] += heat_transfer_kWh

                # Calculate net energy balance for this timestep
                remaining_heat = self.Q_in[t] - self.Q_out[t]  # Net energy [kW]

                # Discharge logic (negative remaining_heat)
                if remaining_heat < 0:
                    heat_needed = abs(remaining_heat)
                    for i in range(self.num_layers):  # Discharge from top to bottom
                        if heat_needed > 1e-6 and self.T_sto_layers[t, i] > self.T_min:
                            available_heat = ((self.T_sto_layers[t, i] - self.T_min) * 
                                            self.layer_volume[i] * self.rho * self.cp / 3.6e6)
                            
                            if heat_needed >= available_heat:
                                # Fully discharge this layer
                                heat_stored_per_layer[i] -= available_heat
                                self.T_sto_layers[t, i] = self.T_min
                                heat_needed -= available_heat
                            else:
                                # Partially discharge this layer
                                heat_stored_per_layer[i] -= heat_needed
                                temp_drop = (heat_needed * 3.6e6) / (self.layer_volume[i] * self.rho * self.cp)
                                self.T_sto_layers[t, i] -= temp_drop
                                heat_needed = 0

                # Charge logic (positive remaining_heat)
                elif remaining_heat > 0:
                    for i in range(self.num_layers):  # Charge from top to bottom
                        if remaining_heat > 1e-6 and self.T_sto_layers[t, i] < self.T_max:
                            max_heat_capacity = ((self.T_max - self.T_sto_layers[t, i]) * 
                                               self.layer_volume[i] * self.rho * self.cp / 3.6e6)
                            
                            if remaining_heat >= max_heat_capacity:
                                # Fully charge this layer
                                heat_stored_per_layer[i] += max_heat_capacity
                                self.T_sto_layers[t, i] = self.T_max
                                remaining_heat -= max_heat_capacity
                            else:
                                # Partially charge this layer
                                heat_stored_per_layer[i] += remaining_heat
                                temp_rise = (remaining_heat * 3.6e6) / (self.layer_volume[i] * self.rho * self.cp)
                                self.T_sto_layers[t, i] += temp_rise
                                remaining_heat = 0

                # Final inter-layer heat conduction after charging/discharging
                for i in range(self.num_layers - 1):
                    delta_T = self.T_sto_layers[t, i] - self.T_sto_layers[t, i+1]
                    if abs(delta_T) > 1e-6:
                        heat_transfer = (self.thermal_conductivity * self.S_side * delta_T / 
                                       self.layer_thickness)  # W
                        heat_transfer_kWh = heat_transfer / 1000  # kWh per hour
                        
                        # Apply heat transfer with temperature update
                        heat_stored_per_layer[i] -= heat_transfer_kWh
                        heat_stored_per_layer[i+1] += heat_transfer_kWh
                        
                        # Update temperatures based on new energy content
                        if self.layer_volume[i] > 0:
                            self.T_sto_layers[t, i] = ((heat_stored_per_layer[i] * 3.6e6) / 
                                                     (self.layer_volume[i] * self.rho * self.cp) + self.T_ref)
                        if self.layer_volume[i+1] > 0:
                            self.T_sto_layers[t, i+1] = ((heat_stored_per_layer[i+1] * 3.6e6) / 
                                                       (self.layer_volume[i+1] * self.rho * self.cp) + self.T_ref)

                # Enforce temperature limits
                self.T_sto_layers[t, :] = np.clip(self.T_sto_layers[t, :], self.T_min, self.T_max)

                # Calculate total stored energy
                self.Q_sto[t] = np.sum(heat_stored_per_layer)

            # Update average storage temperature
            self.T_sto[t] = np.average(self.T_sto_layers[t])

        # Calculate overall efficiency
        self.calculate_efficiency(self.Q_in)

    def plot_3d_temperature_distribution(self, ax, time_step: int) -> None:
        """
        Visualize 3D temperature stratification in thermal storage system.

        :param ax: 3D matplotlib axes object (projection='3d')
        :type ax: matplotlib.axes.Axes3D
        :param time_step: Simulation time step for visualization (0 to hours-1)
        :type time_step: int
        :raises ValueError: If storage_type unsupported for 3D visualization
        :raises IndexError: If time_step outside valid simulation range

        .. note::
           Color-coded temperature layers (coolwarm colormap: blue=cold, red=hot). Supports cylindrical, truncated cone, and truncated trapezoid geometries.
        """
        # Validate time step
        if time_step >= len(self.T_sto_layers):
            raise IndexError(f"time_step {time_step} exceeds simulation length {len(self.T_sto_layers)}")

        if self.storage_type == "cylindrical":
            self._plot_cylindrical_3d(ax, time_step)
        elif self.storage_type == "truncated_cone":
            self._plot_cone_3d(ax, time_step)
        elif self.storage_type == "truncated_trapezoid":
            self._plot_trapezoid_3d(ax, time_step)
        else:
            raise ValueError(f"Unsupported storage type '{self.storage_type}' for 3D visualization")

        # Add labels and colorbar only once
        if not hasattr(self, 'labels_exist') or not self.labels_exist:
            ax.set_title(f'Temperature Distribution (Time Step {time_step})')
            ax.set_xlabel('X (m)')
            ax.set_ylabel('Y (m)')
            ax.set_zlabel('Z (m)')
            self.labels_exist = True

        if not hasattr(self, 'colorbar_exists') or not self.colorbar_exists:
            # Create temperature colorbar
            mappable = plt.cm.ScalarMappable(cmap=plt.cm.coolwarm)
            mappable.set_array([self.T_min, self.T_max])
            cbar = plt.colorbar(mappable, ax=ax, shrink=0.5, aspect=5)
            cbar.set_label('Temperature (°C)')
            self.colorbar_exists = True

    def _plot_cylindrical_3d(self, ax, time_step: int) -> None:
        """
        Plot cylindrical storage 3D visualization with temperature-coded layers.

        :param ax: 3D matplotlib axes object
        :param time_step: Simulation time step
        :type ax: matplotlib.axes.Axes3D
        :type time_step: int
        """
        radius, height = self.dimensions
        z_layers = np.linspace(0, height, self.num_layers + 1)
        theta = np.linspace(0, 2 * np.pi, 50)
        
        # Flip coordinates for hot-top visualization
        z_layers = np.flip(z_layers)
        T_layers_flipped = np.flip(self.T_sto_layers[time_step])
        
        for i in range(self.num_layers):
            # Generate cylindrical coordinates
            theta_grid, z_grid = np.meshgrid(theta, z_layers[i:i+2])
            x_grid = radius * np.cos(theta_grid)
            y_grid = radius * np.sin(theta_grid)
            
            # Color based on temperature
            color_value = (T_layers_flipped[i] - self.T_min) / (self.T_max - self.T_min)
            color = plt.cm.coolwarm(color_value)
            facecolors = np.tile(color[:3], (x_grid.shape[0], x_grid.shape[1], 1))
            
            # Plot layer surfaces
            ax.plot_surface(x_grid, y_grid, z_grid, facecolors=facecolors, 
                          rstride=1, cstride=1, alpha=0.7)

    def _plot_cone_3d(self, ax, time_step: int) -> None:
        """
        Plot truncated cone PTES 3D visualization with temperature-coded layers.

        :param ax: 3D matplotlib axes object
        :param time_step: Simulation time step
        :type ax: matplotlib.axes.Axes3D
        :type time_step: int
        """
        top_radius, bottom_radius, height = self.dimensions
        z_layers = np.linspace(0, height, self.num_layers + 1)
        theta = np.linspace(0, 2 * np.pi, 50)
        
        # Calculate radius progression
        radii = np.linspace(bottom_radius, top_radius, len(z_layers))
        T_layers_flipped = np.flip(self.T_sto_layers[time_step])
        
        for i in range(self.num_layers):
            # Generate conical coordinates
            theta_grid, z_grid = np.meshgrid(theta, z_layers[i:i+2])
            x_grid = np.outer(np.cos(theta), radii[i:i+2])
            y_grid = np.outer(np.sin(theta), radii[i:i+2])
            
            # Color based on temperature
            color_value = (T_layers_flipped[i] - self.T_min) / (self.T_max - self.T_min)
            color = plt.cm.coolwarm(color_value)
            facecolors = np.tile(color[:3], (x_grid.shape[0], x_grid.shape[1], 1))
            
            # Plot layer surface
            ax.plot_surface(x_grid, y_grid, np.transpose(z_grid), 
                          facecolors=facecolors, rstride=1, cstride=1, alpha=0.7)

    def _plot_trapezoid_3d(self, ax, time_step: int) -> None:
        """
        Plot truncated trapezoid PTES 3D visualization with temperature-coded layers.

        :param ax: 3D matplotlib axes object
        :param time_step: Simulation time step
        :type ax: matplotlib.axes.Axes3D
        :type time_step: int
        """
        bottom_length, bottom_width, top_length, top_width, height = self.dimensions
        z_layers = np.linspace(0, height, self.num_layers + 1)
        
        # Calculate dimension progression
        lengths = np.linspace(bottom_length, top_length, len(z_layers))
        widths = np.linspace(bottom_width, top_width, len(z_layers))
        T_layers_flipped = np.flip(self.T_sto_layers[time_step])
        
        for i in range(self.num_layers):
            # Layer coordinates
            x_coords = [-lengths[i]/2, lengths[i]/2, lengths[i+1]/2, -lengths[i+1]/2]
            y_coords = [-widths[i]/2, -widths[i]/2, widths[i+1]/2, widths[i+1]/2]
            z_bottom, z_top = z_layers[i], z_layers[i+1]
            
            # Color based on temperature
            color_value = (T_layers_flipped[i] - self.T_min) / (self.T_max - self.T_min)
            color = plt.cm.coolwarm(color_value)
            
            # Plot layer surfaces (simplified representation)
            vertices = [
                [[x_coords[j], y_coords[j], z_bottom] for j in range(4)],
                [[x_coords[j], y_coords[j], z_top] for j in range(4)]
            ]
            
            for vertex_set in vertices:
                xs, ys, zs = zip(*vertex_set)
                ax.plot_trisurf(xs + xs[:1], ys + ys[:1], zs + zs[:1], 
                              color=color[:3], alpha=0.7)

    def plot_results(self) -> None:
        """
        Generate comprehensive multi-panel visualization of stratified storage simulation results.

        .. note::
           Six panels: heat input/output, average temperature, heat losses, stored energy, layer temperatures, and 3D temperature distribution.
        """
        fig = plt.figure(figsize=(16, 10))
        
        # Create subplot layout
        ax1 = fig.add_subplot(2, 3, 1)
        ax2 = fig.add_subplot(2, 3, 2)
        ax3 = fig.add_subplot(2, 3, 3)
        ax4 = fig.add_subplot(2, 3, 4)
        ax5 = fig.add_subplot(2, 3, 5)
        ax6 = fig.add_subplot(2, 3, 6, projection='3d')

        # Panel 1: Heat Input and Output
        ax1.plot(self.Q_in, label='Heat Input', color='red', linewidth=1.5)
        ax1.plot(self.Q_out, label='Heat Output', color='blue', linewidth=1.5)
        ax1.set_ylabel('Power (kW)')
        ax1.set_title('Heat Input and Output over Time')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Panel 2: Average Storage Temperature
        ax2.plot(self.T_sto, label='Storage Temperature', color='darkgreen', linewidth=1.5)
        ax2.axhline(y=self.T_max, color='red', linestyle='--', alpha=0.7, label=f'T_max ({self.T_max}°C)')
        ax2.axhline(y=self.T_min, color='blue', linestyle='--', alpha=0.7, label=f'T_min ({self.T_min}°C)')
        ax2.set_ylabel('Temperature (°C)')
        ax2.set_title(f'Storage Temperature ({self.storage_type.replace("_", " ").title()})')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Panel 3: Heat Loss Analysis
        ax3.plot(self.Q_loss, label='Heat Loss', color='orange', linewidth=1.5)
        ax3.set_ylabel('Heat Loss (kW)')
        ax3.set_title('Heat Loss over Time')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Panel 4: Stored Energy Content
        ax4.plot(self.Q_sto, label='Stored Energy', color='green', linewidth=1.5)
        ax4.set_ylabel('Stored Energy (kWh)')
        ax4.set_title('Stored Energy over Time')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        # Panel 5: Stratified Layer Temperatures
        colors = plt.cm.viridis(np.linspace(0, 1, self.num_layers))
        for i in range(self.num_layers):
            ax5.plot(self.T_sto_layers[:, i], label=f'Layer {i+1}', 
                    color=colors[i], linewidth=1.2)
        ax5.set_xlabel('Time (hours)')
        ax5.set_ylabel('Temperature (°C)')
        ax5.set_title('Stratified Layer Temperatures')
        ax5.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax5.grid(True, alpha=0.3)

        # Panel 6: 3D Temperature Distribution
        visualization_time = min(6000, len(self.T_sto_layers) - 1)  # Safe time selection
        self.plot_3d_temperature_distribution(ax6, visualization_time)

        plt.tight_layout()