"""
Simple Thermal Storage Module
=============================

Seasonal Thermal Energy Storage (STES) modeling with various geometries.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

.. note:: Based on Narula et al., Renewable Energy 151 (2020), DOI: 10.1016/j.renene.2019.11.121
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Dict, Any, List, Optional, Union

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator

class ThermalStorage(BaseHeatGenerator):
    """
    Base thermal energy storage system.

    :param name: Unique identifier
    :type name: str
    :param storage_type: Geometry ("cylindrical", "truncated_cone", "truncated_trapezoid")
    :type storage_type: str
    :param dimensions: Geometric dimensions tuple
    :type dimensions: tuple
    :param rho: Storage medium density [kg/m³]
    :type rho: float
    :param cp: Specific heat capacity [J/(kg·K)]
    :type cp: float
    :param T_ref: Reference temperature [°C]
    :type T_ref: float

    .. note::
       Supports cylindrical, cone and trapezoid geometries with insulation modeling.
    """

    def __init__(self, name: str, storage_type: str, dimensions: Tuple[float, ...], 
                 rho: float, cp: float, T_ref: float, lambda_top: float, 
                 lambda_side: float, lambda_bottom: float, lambda_soil: float, 
                 T_amb: float, T_soil: float, T_max: float, T_min: float, 
                 initial_temp: float, dt_top: float, ds_side: float, 
                 db_bottom: float, hours: int = 8760, num_layers: int = 5, 
                 thermal_conductivity: float = 0.6):
        super().__init__(name)
        self.storage_type = storage_type
        self.dimensions = dimensions
        self.rho = rho
        self.cp = cp
        self.T_ref = T_ref
        self.lambda_top = lambda_top
        self.lambda_side = lambda_side
        self.lambda_bottom = lambda_bottom
        self.lambda_soil = lambda_soil
        self.T_amb = T_amb
        self.T_soil = T_soil
        self.T_max = T_max
        self.T_min = T_min
        self.dt_top = dt_top
        self.ds_side = ds_side
        self.db_bottom = db_bottom
        self.hours = hours
        self.num_layers = num_layers
        self.thermal_conductivity = thermal_conductivity
        self.Q_sto = np.zeros(hours)
        self.Q_loss = np.zeros(hours)
        self.T_sto = np.zeros(hours)
        self.T_sto[0] = initial_temp
        
        # Calculate geometry-dependent properties
        if storage_type == "cylindrical":
            self.volume, self.S_top, self.S_side, self.S_bottom = self.calculate_cylindrical_geometry(dimensions)
        elif storage_type == "truncated_cone":
            self.volume, self.S_top, self.S_side, self.S_bottom = self.calculate_truncated_cone_geometry(dimensions)
        elif storage_type == "truncated_trapezoid":
            self.volume, self.S_top, self.S_side, self.S_bottom = self.calculate_truncated_trapezoid_geometry(dimensions)
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")

        self.colorbar_exists = False
        self.labels_exist = False

    def calculate_cylindrical_geometry(self, dimensions: Tuple[float, float]) -> Tuple[float, float, float, float]:
        """
        Calculate volume and surface areas for cylindrical storage tanks.

        :param dimensions: Tank dimensions (radius[m], height[m])
        :type dimensions: Tuple[float, float]
        :return: (volume[m³], S_top[m²], S_side[m²], S_bottom[m²])
        :rtype: Tuple[float, float, float, float]

        .. note::
           Suitable for short-term and medium-term thermal storage in district heating systems.
        """
        radius, height = dimensions
        volume = np.pi * radius**2 * height
        S_top = np.pi * radius**2
        S_side = 2 * np.pi * radius * height
        S_bottom = S_top  # Same as top for cylinder
        return volume, S_top, S_side, S_bottom

    def calculate_truncated_cone_geometry(self, dimensions: Tuple[float, float, float]) -> Tuple[float, float, float, float]:
        """
        Calculate volume and surface areas for conical pit thermal energy storage (PTES).

        :param dimensions: Cone dimensions (top_radius[m], bottom_radius[m], height[m])
        :type dimensions: Tuple[float, float, float]
        :return: (volume[m³], S_top[m²], S_side[m²], S_bottom[m²])
        :rtype: Tuple[float, float, float, float]

        .. note::
           Widely used for large-scale seasonal thermal energy storage with excellent stratification.
        """
        top_radius, bottom_radius, height = dimensions
        
        # Volume using truncated cone formula
        volume = (1/3) * np.pi * height * (top_radius**2 + bottom_radius**2 + top_radius * bottom_radius)
        
        # Surface areas
        S_top = np.pi * top_radius**2
        S_bottom = np.pi * bottom_radius**2
        
        # Slant height for lateral surface area
        slant_height = np.sqrt((bottom_radius - top_radius)**2 + height**2)
        S_side = np.pi * (top_radius + bottom_radius) * slant_height
        
        return volume, S_top, S_side, S_bottom

    def calculate_truncated_trapezoid_geometry(self, dimensions: Tuple[float, float, float, float, float]) -> Tuple[float, float, float, float]:
        """
        Calculate volume and surface areas for trapezoidal pit thermal energy storage (PTES).

        :param dimensions: Trapezoid dimensions (top_length[m], top_width[m], bottom_length[m], bottom_width[m], height[m])
        :type dimensions: Tuple[float, float, float, float, float]
        :return: (volume[m³], S_top[m²], S_side[m²], S_bottom[m²])
        :rtype: Tuple[float, float, float, float]

        .. note::
           Flexible geometry for adaptation to site constraints and irregular plot geometries.
        """
        top_length, top_width, bottom_length, bottom_width, height = dimensions
        
        # Calculate areas of top and bottom rectangles
        A_top = top_length * top_width
        A_bottom = bottom_length * bottom_width
        
        # Volume using truncated pyramid formula
        volume = (height / 3) * (A_top + A_bottom + np.sqrt(A_top * A_bottom))
        
        # Surface areas
        S_top = A_top
        S_bottom = A_bottom
        
        # Side surface areas (four trapezoidal faces)
        # Length faces (2 faces)
        side_length_slant = np.sqrt(((bottom_length - top_length) / 2)**2 + height**2)
        S_side_length = 2 * ((top_length + bottom_length) / 2) * side_length_slant
        
        # Width faces (2 faces)  
        side_width_slant = np.sqrt(((bottom_width - top_width) / 2)**2 + height**2)
        S_side_width = 2 * ((top_width + bottom_width) / 2) * side_width_slant
        
        # Total side surface area
        S_side = S_side_length + S_side_width
        
        return volume, S_top, S_side, S_bottom

    def calculate_efficiency(self, Q_in: np.ndarray) -> None:
        """
        Calculate overall storage efficiency as ratio of output to input accounting for losses.

        :param Q_in: Energy input time series [kWh/h]
        :type Q_in: numpy.ndarray

        .. note::
           Efficiency η = 1 - (E_losses / E_input). Typical values: 85-95% (short-term), 70-85% (medium-term), 50-70% (seasonal).
        """
        total_input = np.sum(Q_in)
        self.total_energy_loss_kWh = np.sum(self.Q_loss)
        
        if total_input > 0:
            self.efficiency = 1 - (self.total_energy_loss_kWh / total_input)
        else:
            self.efficiency = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert storage object to dictionary for serialization.

        :return: Dictionary with all serializable attributes
        :rtype: Dict[str, Any]
        """
        data = self.__dict__.copy()
        data.pop('scene_item', None)
        print("Storage saved")
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThermalStorage':
        """
        Create storage object from dictionary.

        :param data: Dictionary with storage attributes
        :type data: Dict[str, Any]
        :return: Reconstructed storage object
        :rtype: ThermalStorage
        """
        obj = cls.__new__(cls)
        obj.__dict__.update(data)
        print("Storage loaded")
        return obj
    
    def __deepcopy__(self, memo: Dict[int, Any]) -> 'ThermalStorage':
        """
        Create deep copy of storage object.

        :param memo: Memoization dictionary for deepcopy
        :type memo: Dict[int, Any]
        :return: Deep copy of storage object
        :rtype: ThermalStorage
        """
        return self.from_dict(self.to_dict())

class SimpleThermalStorage(ThermalStorage):
    """
    Simplified thermal storage with lumped capacitance model.

    .. note::
       Single temperature node without stratification effects.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def calculate_heat_loss(self, T_sto_last: float) -> float:
        """
        Calculate temperature-dependent heat losses using thermal resistance networks.

        :param T_sto_last: Storage temperature from previous time step [°C]
        :type T_sto_last: float
        :return: Total heat loss rate [kW]
        :rtype: float
        :raises ValueError: If insulation thickness insufficient for underground storage

        .. note::
           Supports cylindrical (overground/underground), truncated_cone, and truncated_trapezoid geometries.
        """
        if self.storage_type == "cylindrical_overground":
            # Heat loss from top to ambient air
            Q_t = (T_sto_last - self.T_amb) * (self.lambda_top / self.dt_top) * self.S_top
            
            # Heat loss from sides to ambient air
            Q_s = (T_sto_last - self.T_amb) * (self.lambda_side / self.ds_side) * self.S_side
            
            # Heat loss from bottom through insulation and soil
            R_bottom_insulation = self.db_bottom / self.lambda_bottom
            R_soil = 4 * self.dimensions[0] / (3 * np.pi * self.lambda_soil)
            R_total_bottom = R_bottom_insulation + R_soil
            Q_b = (T_sto_last - self.T_amb) / R_total_bottom * self.S_bottom
            
            return (Q_t + Q_s + Q_b) / 1000  # Convert W to kW

        elif self.storage_type == "cylindrical_underground":
            # Underground cylindrical storage - combined side and bottom losses
            R = self.dimensions[0]  # Radius
            H = self.dimensions[1]  # Height
            
            # Minimum insulation thickness requirement
            d_min = (self.lambda_side / self.lambda_soil) * R * 0.37
            
            if self.ds_side > 2 * d_min:
                # Thermal conductance for combined side and bottom
                K_sb = 1 / (self.ds_side / self.lambda_side + 0.52 * R / self.lambda_soil)
                
                # Combined surface area (cylindrical surface + bottom)
                S_c = np.pi * R**2 + 2 * np.pi * R * H
                
                Q_sb = (T_sto_last - self.T_soil) * K_sb * S_c
                return Q_sb / 1000  # Convert W to kW
            else:
                raise ValueError(f"Insulation thickness {self.ds_side:.3f}m too small. "
                               f"Minimum required: {2*d_min:.3f}m")

        elif self.storage_type in ["truncated_cone", "truncated_trapezoid"]:
            # Pit thermal energy storage heat loss calculations
            H = self.dimensions[2]  # Height/depth
            
            # Side heat loss calculation
            a = self.ds_side / self.lambda_side + np.pi * H / (2 * self.lambda_soil)
            b = np.pi / self.lambda_soil
            
            if (a + b * H) > a and a > 0:
                K_s = (1 / (b * H)) * np.log((a + b * H) / a)
                Q_s = (T_sto_last - self.T_soil) * K_s * self.S_side
            else:
                Q_s = 0

            # Bottom heat loss calculation  
            if self.storage_type == "truncated_cone":
                bottom_characteristic_length = self.dimensions[1]  # Bottom radius
            else:  # truncated_trapezoid
                bottom_characteristic_length = min(self.dimensions[2], self.dimensions[3])  # Min of bottom dimensions
            
            c = self.db_bottom / self.lambda_bottom + np.pi * H / (2 * self.lambda_soil)
            
            if (c + b * bottom_characteristic_length) > c and c > 0:
                K_b = (1 / (2 * b * bottom_characteristic_length)) * np.log((c + b * bottom_characteristic_length) / c)
                Q_b = (T_sto_last - self.T_soil) * K_b * self.S_bottom
            else:
                Q_b = 0

            return (Q_s + Q_b) / 1000  # Convert W to kW
        
        else:
            raise ValueError(f"Unsupported storage type for heat loss calculation: {self.storage_type}")

    def simulate(self, Q_in: np.ndarray, Q_out: np.ndarray) -> None:
        """
        Execute hour-by-hour thermal simulation solving energy balance equations.

        :param Q_in: Heat input time series [kWh/h]
        :type Q_in: numpy.ndarray
        :param Q_out: Heat output time series [kWh/h]
        :type Q_out: numpy.ndarray

        .. note::
           Solves dE/dt = Q_in - Q_out - Q_loss with temperature limits T_min and T_max enforced.
        """
        self.Q_in = Q_in
        self.Q_out = Q_out

        for t in range(self.hours):
            # Calculate heat loss based on previous time step temperature
            if t == 0:
                # Use initial temperature for first time step loss calculation
                self.Q_loss[t] = self.calculate_heat_loss(self.T_sto[0])
                
                # Calculate initial stored energy relative to reference temperature
                initial_energy_J = self.volume * self.rho * self.cp * (self.T_sto[0] - self.T_ref)
                self.Q_sto[t] = initial_energy_J / 3.6e6  # Convert J to kWh
            else:
                # Use previous time step temperature for heat loss
                self.Q_loss[t] = self.calculate_heat_loss(self.T_sto[t-1])
                
                # Energy balance: Q_stored(t) = Q_stored(t-1) + Q_in - Q_out - Q_loss
                # All terms in kWh (Q_in and Q_out are kWh/h, Q_loss converted to kW and multiplied by 1h)
                self.Q_sto[t] = self.Q_sto[t-1] + (Q_in[t] - Q_out[t] - self.Q_loss[t])

            # Convert stored energy back to temperature
            if t > 0:
                stored_energy_J = self.Q_sto[t] * 3.6e6  # Convert kWh to J
                self.T_sto[t] = (stored_energy_J / (self.volume * self.rho * self.cp)) + self.T_ref

            # Apply temperature limits
            if self.T_sto[t] > self.T_max:
                self.T_sto[t] = self.T_max
                # Recalculate stored energy based on limited temperature
                limited_energy_J = self.volume * self.rho * self.cp * (self.T_max - self.T_ref)
                self.Q_sto[t] = limited_energy_J / 3.6e6
                
            elif self.T_sto[t] < self.T_min:
                self.T_sto[t] = self.T_min
                # Recalculate stored energy based on limited temperature
                limited_energy_J = self.volume * self.rho * self.cp * (self.T_min - self.T_ref)
                self.Q_sto[t] = limited_energy_J / 3.6e6
        
        # Calculate overall storage efficiency
        self.calculate_efficiency(Q_in)

    def plot_results(self) -> None:
        """
        Generate multi-panel plot of simulation results (input/output, stored energy, temperature, heat loss).

        .. note::
           Creates 2x2 subplot grid with professional matplotlib styling and clear axis labels.
        """
        fig = plt.figure(figsize=(16, 10))
        
        # Create subplot grid
        axs1 = fig.add_subplot(2, 2, 1)
        axs2 = fig.add_subplot(2, 2, 2)
        axs3 = fig.add_subplot(2, 2, 3)
        axs4 = fig.add_subplot(2, 2, 4)
        
        # Time axis (assuming hourly data)
        time_hours = np.arange(len(self.Q_in))
        
        # Plot 1: Heat Input and Output
        axs1.plot(time_hours, self.Q_in, label='Heat Input (kW)', color='red', linewidth=1.5)
        axs1.plot(time_hours, self.Q_out, label='Heat Output (kW)', color='blue', linewidth=1.5)
        axs1.set_title('Heat Input and Output', fontsize=14, fontweight='bold')
        axs1.set_xlabel('Time [hours]')
        axs1.set_ylabel('Power [kW]')
        axs1.legend()
        axs1.grid(True, alpha=0.3)

        # Plot 2: Stored Heat
        axs2.plot(time_hours, self.Q_sto, label='Stored Heat (kWh)', color='green', linewidth=2)
        axs2.set_title('Stored Thermal Energy', fontsize=14, fontweight='bold')
        axs2.set_xlabel('Time [hours]')
        axs2.set_ylabel('Stored Energy [kWh]')
        axs2.legend()
        axs2.grid(True, alpha=0.3)

        # Plot 3: Storage Temperature
        axs3.plot(time_hours, self.T_sto, label='Storage Temperature (°C)', color='orange', linewidth=2)
        # Add temperature limits as horizontal lines
        axs3.axhline(y=self.T_max, color='red', linestyle='--', alpha=0.7, label=f'T_max ({self.T_max}°C)')
        axs3.axhline(y=self.T_min, color='blue', linestyle='--', alpha=0.7, label=f'T_min ({self.T_min}°C)')
        axs3.set_title('Storage Temperature Profile', fontsize=14, fontweight='bold')
        axs3.set_xlabel('Time [hours]')
        axs3.set_ylabel('Temperature [°C]')
        axs3.legend()
        axs3.grid(True, alpha=0.3)

        # Plot 4: Heat Loss
        axs4.plot(time_hours, self.Q_loss, label='Heat Loss (kW)', color='purple', linewidth=2)
        axs4.set_title('Heat Loss Rate', fontsize=14, fontweight='bold')
        axs4.set_xlabel('Time [hours]')
        axs4.set_ylabel('Heat Loss [kW]')
        axs4.legend()
        axs4.grid(True, alpha=0.3)

        # Plot 3D geometry
        #self.plot_3d_temperature_distribution(axs6, 3000)

        # Adjust layout for better spacing
        plt.tight_layout()