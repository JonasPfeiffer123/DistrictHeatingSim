"""
Solar Thermal Collector System Module
=====================================

Solar thermal collector modeling with flat-plate and vacuum tube technologies.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

.. note::
    Based on Scenocalc 2.0 solar thermal model (https://www.scfw.de)
"""

import numpy as np
from math import pi, exp, log, sqrt
from typing import Dict, Tuple, List, Optional, Union, Any

from districtheatingsim.heat_generators.solar_radiation import calculate_solar_radiation
from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy

class SolarThermal(BaseHeatGenerator):
    """
    Solar thermal collector system with storage.

    :param name: Unique identifier
    :type name: str
    :param bruttofläche_STA: Gross collector area [m²]
    :type bruttofläche_STA: float
    :param vs: Storage volume [m³]
    :type vs: float
    :param Typ: Collector type ("Flachkollektor" or "Vakuumröhrenkollektor")
    :type Typ: str
    :param kosten_speicher_spez: Storage costs [€/m³], defaults to 750
    :type kosten_speicher_spez: float, optional
    :param kosten_fk_spez: Flat-plate costs [€/m²], defaults to 430
    :type kosten_fk_spez: float, optional

    .. note::
       Includes detailed solar radiation calculations and efficiency modeling.
    """

    def __init__(self, name: str, bruttofläche_STA: float, vs: float, Typ: str, 
                 kosten_speicher_spez: float = 750, kosten_fk_spez: float = 430, 
                 kosten_vrk_spez: float = 590, Tsmax: float = 90, Longitude: float = -14.4222, 
                 STD_Longitude: float = -15, Latitude: float = 51.1676, 
                 East_West_collector_azimuth_angle: float = 0, Collector_tilt_angle: float = 36, 
                 Tm_rl: float = 60, Qsa: float = 0, Vorwärmung_K: float = 8, 
                 DT_WT_Solar_K: float = 5, DT_WT_Netz_K: float = 5, 
                 opt_volume_min: float = 0, opt_volume_max: float = 200, 
                 opt_area_min: float = 0, opt_area_max: float = 2000, active: bool = True):
        """
        Initialize solar thermal collector system with technical and economic parameters.

        :param name: Unique identifier
        :type name: str
        :param bruttofläche_STA: Gross collector area [m²]
        :type bruttofläche_STA: float
        :param vs: Storage volume [m³]
        :type vs: float
        :param Typ: Collector type ("Flachkollektor" or "Vakuumröhrenkollektor")
        :type Typ: str
        :param kosten_speicher_spez: Storage costs [€/m³], defaults to 750
        :type kosten_speicher_spez: float
        :param kosten_fk_spez: Flat-plate costs [€/m²], defaults to 430
        :type kosten_fk_spez: float
        :param kosten_vrk_spez: Vacuum tube costs [€/m²], defaults to 590
        :type kosten_vrk_spez: float
        """
        super().__init__(name)
        self.bruttofläche_STA = bruttofläche_STA
        self.vs = vs
        self.Typ = Typ
        self.kosten_speicher_spez = kosten_speicher_spez
        self.kosten_fk_spez = kosten_fk_spez
        self.kosten_vrk_spez = kosten_vrk_spez
        self.Tsmax = Tsmax
        self.Longitude = Longitude
        self.STD_Longitude = STD_Longitude
        self.Latitude = Latitude
        self.East_West_collector_azimuth_angle = East_West_collector_azimuth_angle
        self.Collector_tilt_angle = Collector_tilt_angle
        self.Tm_rl = Tm_rl
        self.Qsa = Qsa
        self.Vorwärmung_K = Vorwärmung_K
        self.DT_WT_Solar_K = DT_WT_Solar_K
        self.DT_WT_Netz_K = DT_WT_Netz_K
        self.opt_volume_min = opt_volume_min
        self.opt_volume_max = opt_volume_max
        self.opt_area_min = opt_area_min
        self.opt_area_max = opt_area_max
        self.active = active

        # Technology-specific cost structure
        self.kosten_pro_typ = {
            # Viessmann Flachkollektor Vitosol 200-FM, 2,56 m²: 697,9 € (brutto); 586,5 € (netto) -> 229 €/m²
            # + 200 €/m² Installation/Zubehör
            "Flachkollektor": self.kosten_fk_spez,
            # Ritter Vakuumröhrenkollektor CPC XL1921 (4,99m²): 2299 € (brutto); 1932 € (Netto) -> 387 €/m²
            # + 200 €/m² Installation/Zubehör
            "Vakuumröhrenkollektor": self.kosten_vrk_spez
        }

        self.Kosten_STA_spez = self.kosten_pro_typ[self.Typ]  # €/m²
        self.Nutzungsdauer = 20  # Jahre
        self.f_Inst, self.f_W_Insp, self.Bedienaufwand = 0.5, 1, 0
        self.Anteil_Förderung_BEW = 0.4
        self.Betriebskostenförderung_BEW = 10  # €/MWh 10 Jahre
        self.co2_factor_solar = 0.0  # tCO2/MWh heat is 0
        self.primärenergiefaktor = 0.0

        self.strategy = SolarThermalStrategy(charge_on=0, charge_off=0)

        self.init_calculation_constants()
        self.init_operation(8760)

    def init_calculation_constants(self) -> None:
        """
        Initialize technology-specific calculation constants for collector performance modeling.

        .. note::
           Sets efficiency parameters, heat loss coefficients, IAM data, and geometric factors based on collector type.
           Flat-plate: η0=0.763, c1=1.969 W/(m²·K). Vacuum tube: η0=0.693, c1=0.583 W/(m²·K).
        """
        # Environmental parameters
        self.Albedo = 0.2  # Ground reflection coefficient
        self.wcorr = 0.5   # Wind speed correction factor

        if self.Typ == "Flachkollektor":
            # Flat-plate collector parameters (Vitosol 200-F XL13)
            # Gross area is reference area
            self.Eta0b_neu = 0.763
            self.Kthetadiff = 0.931
            self.Koll_c1 = 1.969
            self.Koll_c2 = 0.015
            self.Koll_c3 = 0
            self.KollCeff_A = 9.053
            self.KollAG = 13.17
            self.KollAAp = 12.35

            self.Aperaturfläche = self.bruttofläche_STA * (self.KollAAp / self.KollAG)
            self.Bezugsfläche = self.bruttofläche_STA

            self.IAM_W = {0: 1, 10: 1, 20: 0.99, 30: 0.98, 40: 0.96, 50: 0.91, 60: 0.82, 70: 0.53, 80: 0.27, 90: 0.0}
            self.IAM_N = {0: 1, 10: 1, 20: 0.99, 30: 0.98, 40: 0.96, 50: 0.91, 60: 0.82, 70: 0.53, 80: 0.27, 90: 0.0}

        elif self.Typ == "Vakuumröhrenkollektor":
            # Vacuum tube collector parameters
            # Aperture area is reference area
            self.Eta0hem = 0.688
            self.a1 = 0.583
            self.a2 = 0.003
            self.KollCeff_A = 8.78
            self.KollAG = 4.94
            self.KollAAp = 4.5

            self.Koll_c1 = self.a1
            self.Koll_c2 = self.a2
            self.Koll_c3 = 0
            self.Eta0b_neu = 0.693
            self.Kthetadiff = 0.951

            self.Aperaturfläche = self.bruttofläche_STA * (self.KollAAp / self.KollAG)
            self.Bezugsfläche = self.Aperaturfläche

            self.IAM_W = {0: 1, 10: 1.02, 20: 1.03, 30: 1.03, 40: 1.03, 50: 0.96, 60: 1.07, 70: 1.19, 80: 0.595, 90: 0.0}
            self.IAM_N = {0: 1, 10: 1, 20: 0.99, 30: 0.96, 40: 0.93, 50: 0.9, 60: 0.87, 70: 0.86, 80: 0.43, 90: 0.0}

        # Storage system parameters
        self.QSmax = 1.16 * self.vs * (self.Tsmax - self.Tm_rl)

    def init_operation(self, hours: int) -> None:
        """
        Initialize operational arrays for annual simulation.

        :param hours: Number of simulation hours (typically 8760)
        :type hours: int
        """
        self.betrieb_mask = np.array([False] * hours)
        self.Wärmeleistung_kW = np.zeros(hours, dtype=float)
        self.Speicherinhalt = np.zeros(hours, dtype=float)
        self.Speicherfüllstand = np.zeros(hours, dtype=float)
        self.Wärmemenge_MWh = 0
        self.Anzahl_Starts = 0
        self.Betriebsstunden = 0
        self.Betriebsstunden_pro_Start = 0

        self.calculated = False  # Flag to indicate if calculation is complete

        # Initialize detailed calculation arrays
        self.Tm_a_L = np.zeros(hours, dtype=float)
        self.Pkoll_a_L = np.zeros(hours, dtype=float)
        self.Pkoll_b_L = np.zeros(hours, dtype=float)
        self.T_koll_a_L = np.zeros(hours, dtype=float)
        self.T_koll_b_L = np.zeros(hours, dtype=float)
        self.Tgkoll_a_L = np.zeros(hours, dtype=float)
        self.Tgkoll_L = np.zeros(hours, dtype=float)
        self.Tm_koll_L = np.zeros(hours, dtype=float)
        self.Tm_L = np.zeros(hours, dtype=float)
        self.Kollektorfeldertrag_L = np.zeros(hours, dtype=float)
        self.Zieltemperatur_Solaranlage_L = np.zeros(hours, dtype=float)
        self.TRL_Solar_L = np.zeros(hours, dtype=float)
        self.TS_unten_L = np.zeros(hours, dtype=float)
        self.Verlustwärmestrom_Speicher_L = np.zeros(hours, dtype=float)
        self.Stagnation_L = np.zeros(hours, dtype=float)

    def calculate_heat_generation_costs(self, economic_parameters: Dict) -> float:
        """
        Calculate levelized heat generation costs with subsidy integration.

        :param economic_parameters: Economic parameters (interest_rate, inflation_rate, subsidy_eligibility, etc.)
        :type economic_parameters: Dict
        :return: Heat generation cost [€/MWh]
        :rtype: float

        .. note::
           Includes BEW program: 40% investment cost reduction and 10 €/MWh operational incentive for 10 years.
        """
        self.Strompreis = economic_parameters['electricity_price']
        self.Gaspreis = economic_parameters['gas_price']
        self.Holzpreis = economic_parameters['wood_price']
        self.q = economic_parameters['capital_interest_rate']
        self.r = economic_parameters['inflation_rate']
        self.T = economic_parameters['time_period']
        self.BEW = economic_parameters['subsidy_eligibility']
        self.stundensatz = economic_parameters['hourly_rate']

        if self.Wärmemenge_MWh == 0:
            return 0

        # Calculate investment costs
        self.Investitionskosten_Speicher = self.vs * self.kosten_speicher_spez
        self.Investitionskosten_STA = self.bruttofläche_STA * self.Kosten_STA_spez
        self.Investitionskosten = self.Investitionskosten_Speicher + self.Investitionskosten_STA

        # Calculate standard annuity without subsidies
        self.A_N = self.annuity(
            initial_investment_cost=self.Investitionskosten,
            asset_lifespan_years=self.Nutzungsdauer,
            installation_factor=self.f_Inst,
            maintenance_inspection_factor=self.f_W_Insp,
            operational_effort_h=self.Bedienaufwand,
            interest_rate_factor=self.q,
            inflation_rate_factor=self.r,
            consideration_time_period_years=self.T, 
            annual_energy_demand=0,
            energy_cost_per_unit=0,
            annual_revenue=0,
            hourly_rate=self.stundensatz
        )
        
        self.WGK = self.A_N / self.Wärmemenge_MWh

        # Calculate subsidized costs with BEW program
        self.Eigenanteil = 1 - self.Anteil_Förderung_BEW
        self.Investitionskosten_Gesamt_BEW = self.Investitionskosten * self.Eigenanteil
        self.Annuität_BEW = self.annuity(
            initial_investment_cost=self.Investitionskosten_Gesamt_BEW,
            asset_lifespan_years=self.Nutzungsdauer,
            installation_factor=self.f_Inst,
            maintenance_inspection_factor=self.f_W_Insp,
            operational_effort_h=self.Bedienaufwand,
            interest_rate_factor=self.q,
            inflation_rate_factor=self.r,
            consideration_time_period_years=self.T, 
            annual_energy_demand=0,
            energy_cost_per_unit=0,
            annual_revenue=0,
            hourly_rate=self.stundensatz
        )
        
        self.WGK_BEW = self.Annuität_BEW / self.Wärmemenge_MWh
        self.WGK_BEW_BKF = self.WGK_BEW - self.Betriebskostenförderung_BEW

        if self.BEW == "Nein":
            return self.WGK
        elif self.BEW == "Ja":
            return self.WGK_BEW_BKF
        
    def calculate_environmental_impact(self) -> None:
        """
        Calculate environmental impact metrics (zero CO2 emissions, zero primary energy factor).

        .. note::
           Solar thermal has zero direct emissions and no fossil fuel dependency.
        """
        # Calculate CO2 emissions (zero for renewable solar energy)
        self.co2_emissions = self.Wärmemenge_MWh * self.co2_factor_solar  # tCO2
        
        # Calculate specific CO2 emissions per unit heat generated
        self.spec_co2_total = (self.co2_emissions / self.Wärmemenge_MWh 
                              if self.Wärmemenge_MWh > 0 else 0)  # tCO2/MWh_heat
        
        # Calculate primary energy consumption (zero for solar energy)
        self.primärenergie_Solarthermie = self.Wärmemenge_MWh * self.primärenergiefaktor

    def calculate_solar_thermal_with_storage(self, Last_L: np.ndarray, VLT_L: np.ndarray, 
                                           RLT_L: np.ndarray, TRY_data: Tuple, 
                                           time_steps: np.ndarray, duration: float) -> None:
        """
        Hourly solar thermal simulation with storage integration.

        :param Last_L: Heat demand profile [kW]
        :type Last_L: numpy.ndarray
        :param VLT_L: Supply temperature [°C]
        :type VLT_L: numpy.ndarray
        :param RLT_L: Return temperature [°C]
        :type RLT_L: numpy.ndarray
        :param TRY_data: Weather data (air_temp, wind_speed, direct_rad, global_rad)
        :type TRY_data: Tuple
        :param time_steps: Time step array
        :type time_steps: numpy.ndarray
        :param duration: Time step duration [hours]
        :type duration: float

        .. note::
           Calculates solar radiation, collector efficiency, storage stratification, and heat generation.
        """
        self.Lufttemperatur_L, self.Windgeschwindigkeit_L, self.Direktstrahlung_L, self.Globalstrahlung_L = TRY_data[0], TRY_data[1], TRY_data[2], TRY_data[3]
        
        # Calculate solar radiation on collector surface
        self.GT_H_Gk, self.K_beam_L, self.GbT_L, self.GdT_H_Dk_L = calculate_solar_radiation(
            time_steps, self.Globalstrahlung_L, self.Direktstrahlung_L, self.Longitude,
            self.STD_Longitude, self.Latitude, self.Albedo, 
            self.East_West_collector_azimuth_angle,
            self.Collector_tilt_angle, self.IAM_W, self.IAM_N
        )

        # Hourly simulation loop
        n_steps = len(time_steps)

        for i in range(n_steps):
            # Calculate effective solar radiation terms
            Eta0b_neu_K_beam_GbT = self.Eta0b_neu * self.K_beam_L[i] * self.GbT_L[i]
            Eta0b_neu_Kthetadiff_GdT_H_Dk = self.Eta0b_neu * self.Kthetadiff * self.GdT_H_Dk_L[i]

            if i == 0:
                # Initialize first time step
                self.TS_unten_L[i] = RLT_L[i]
                self.TRL_Solar_L[i] = RLT_L[i]
                self.Zieltemperatur_Solaranlage_L[i] = self.TS_unten_L[i] + self.Vorwärmung_K + self.DT_WT_Solar_K + self.DT_WT_Netz_K
                self.Tm_a_L[i] = (self.Zieltemperatur_Solaranlage_L[i] + self.TRL_Solar_L[i]) / 2
                self.Pkoll_a_L[i] = 0
                self.Tgkoll_a_L[i] = 9.3
                self.T_koll_a_L[i] = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - self.Tgkoll_a_L[i]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_a_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                self.Pkoll_b_L[i] = 0
                self.T_koll_b_L[i] = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - 0) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_b_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                self.Tgkoll_L[i] = 9.3
                self.Tm_koll_L[i] = (self.T_koll_a_L[i] + self.T_koll_b_L[i]) / 2

                self.Kollektorfeldertrag_L[i] = 0
                self.Wärmeleistung_kW[i] = min(self.Kollektorfeldertrag_L[i], Last_L[i])
                self.Verlustwärmestrom_Speicher_L[i] = 0
                self.Speicherinhalt[i] = self.Qsa * 1000
                self.Speicherfüllstand[i] = self.Speicherinhalt[i] / self.QSmax
                self.Stagnation_L[i] = 0

            else:
                # Calculate storage temperature stratification
                if self.Speicherfüllstand[i - 1] >= 0.8:
                    self.TS_unten_L[i] = RLT_L[i] + self.DT_WT_Netz_K + (2/3 * (VLT_L[i] - RLT_L[i]) / 0.2 * self.Speicherfüllstand[i - 1]) + (1 / 3 * (VLT_L[i] - RLT_L[i])) - (2/3 * (VLT_L[i] - RLT_L[i]) / 0.2 * self.Speicherfüllstand[i - 1])
                else:
                    self.TS_unten_L[i] = RLT_L[i] + self.DT_WT_Netz_K + (1 / 3 * (VLT_L[i] - RLT_L[i]) / 0.8) * self.Speicherfüllstand[i - 1]

                # Calculate solar circuit temperatures
                self.Zieltemperatur_Solaranlage_L[i] = self.TS_unten_L[i] + self.Vorwärmung_K + self.DT_WT_Solar_K + self.DT_WT_Netz_K
                self.TRL_Solar_L[i] = self.TS_unten_L[i] + self.DT_WT_Solar_K
                self.Tm_a_L[i] = (self.Zieltemperatur_Solaranlage_L[i] + self.TRL_Solar_L[i]) / 2

                # Calculate collector performance with thermal losses
                c1a = self.Koll_c1 * (self.Tm_a_L[i] - self.Lufttemperatur_L[i])
                c2a = self.Koll_c2 * (self.Tm_a_L[i] - self.Lufttemperatur_L[i]) ** 2
                c3a = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[i] * (self.Tm_a_L[i] - self.Lufttemperatur_L[i])

                self.Pkoll_a_L[i] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1a - c2a - c3a) * self.Bezugsfläche / 1000)
                self.T_koll_a_L[i] = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - self.Tgkoll_a_L[i - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_a_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)

                # Calculate alternative collector state
                c1b = self.Koll_c1 * (self.T_koll_b_L[i - 1] - self.Lufttemperatur_L[i])
                c2b = self.Koll_c2 * (self.T_koll_b_L[i - 1] - self.Lufttemperatur_L[i]) ** 2
                c3b = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[i] * (self.T_koll_b_L[i - 1] - self.Lufttemperatur_L[i])
                
                self.Pkoll_b_L[i] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1b - c2b - c3b) * self.Bezugsfläche / 1000)
                self.T_koll_b_L[i] = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - self.Tgkoll_a_L[i - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (self.Pkoll_b_L[i] * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                
                # Temperature control and collector field output
                self.Tgkoll_a_L[i] = min(self.Zieltemperatur_Solaranlage_L[i], self.T_koll_a_L[i])
                self.Tm_koll_L[i] = (self.T_koll_a_L[i] + self.T_koll_b_L[i]) / 2
                Tm_sys = (self.Zieltemperatur_Solaranlage_L[i] + self.TRL_Solar_L[i]) / 2
                
                if self.Tm_koll_L[i] < Tm_sys and self.Tm_koll_L[i - 1] < Tm_sys:
                    self.Tm_L[i] = self.Tm_koll_L[i]
                else:
                    self.Tm_L[i] = Tm_sys

                # Final collector output calculation
                c1 = self.Koll_c1 * (self.Tm_L[i] - self.Lufttemperatur_L[i])
                c2 = self.Koll_c2 * (self.Tm_L[i] - self.Lufttemperatur_L[i]) ** 2
                c3 = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[i] * (self.Tm_L[i] - self.Lufttemperatur_L[i])
                Pkoll = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - c1 - c2 - c3) * self.Bezugsfläche / 1000)

                # Temperature rise calculation
                T_koll = self.Lufttemperatur_L[i] - (self.Lufttemperatur_L[i] - self.Tgkoll_L[i - 1]) * exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + (Pkoll * 3600) / (
                            self.KollCeff_A * self.Bezugsfläche)
                self.Tgkoll_L[i] = min(self.Zieltemperatur_Solaranlage_L[i], T_koll)

                # Collector field yield calculation
                if T_koll > self.Tgkoll_L[i - 1]:
                    Pkoll_temp_corr = (T_koll-self.Tgkoll_L[i])/(T_koll-self.Tgkoll_L[i - 1]) * Pkoll if self.Tgkoll_L[i] >= self.Zieltemperatur_Solaranlage_L[i] else 0
                    self.Kollektorfeldertrag_L[i] = max(0, min(Pkoll, Pkoll_temp_corr)) if self.Stagnation_L[i - 1] <= 0 else 0
                else:
                    self.Kollektorfeldertrag_L[i] = 0

                # Heat output and storage balance
                self.Wärmeleistung_kW[i] = min(self.Kollektorfeldertrag_L[i] + self.Speicherinhalt[i - 1], Last_L[i]) if self.Kollektorfeldertrag_L[i] + self.Speicherinhalt[i - 1] > 0 else 0

                # Storage energy balance
                Stagnationsverluste = max(0, self.Speicherinhalt[i - 1] - self.Verlustwärmestrom_Speicher_L[i - 1] + self.Kollektorfeldertrag_L[i] - self.Wärmeleistung_kW[i] - self.QSmax)
                PSin = self.Kollektorfeldertrag_L[i] - Stagnationsverluste

                if self.Speicherinhalt[i - 1] - self.Verlustwärmestrom_Speicher_L[i - 1] + PSin - self.Wärmeleistung_kW[i] > self.QSmax:
                    self.Speicherinhalt[i] = self.QSmax
                else:
                    self.Speicherinhalt[i] = self.Speicherinhalt[i - 1] - self.Verlustwärmestrom_Speicher_L[i - 1] + PSin - self.Wärmeleistung_kW[i]

                # Storage temperature and heat loss calculation
                self.Speicherfüllstand[i] = self.Speicherinhalt[i] / self.QSmax

                TS_oben = self.Zieltemperatur_Solaranlage_L[i] - self.DT_WT_Solar_K
                if self.Speicherinhalt[i] <= 0:
                    berechnete_temperatur = TS_oben
                else:
                    temperaturverhältnis = (TS_oben - self.Tm_rl) / (self.Tsmax - self.Tm_rl)
                    if self.Speicherfüllstand[i] < temperaturverhältnis:
                        berechnete_temperatur = VLT_L[i] + self.DT_WT_Netz_K
                    else:
                        berechnete_temperatur = self.Tsmax

                gewichtete_untere_temperatur = (1 - self.Speicherfüllstand[i]) * self.TS_unten_L[i]
                Tms = self.Speicherfüllstand[i] * berechnete_temperatur + gewichtete_untere_temperatur

                self.Verlustwärmestrom_Speicher_L[i] = 0.75 * (self.vs * 1000) ** 0.5 * 0.16 * (Tms - self.Lufttemperatur_L[i]) / 1000

                # Stagnation detection
                self.Stagnation_L[i] = 1 if np.datetime_as_string(time_steps[i], unit='D') == np.datetime_as_string(time_steps[i - 1], unit='D') and self.Kollektorfeldertrag_L[i] > Last_L[i] and self.Speicherinhalt[i] >= self.QSmax else 0

        # Calculate total annual heat generation
        self.Wärmemenge_MWh = np.sum(self.Wärmeleistung_kW) * duration / 1000  # kWh -> MWh

    def generate(self, t: int, **kwargs) -> Tuple[float, float]:
        """
        Generate instantaneous heat output with detailed collector and storage modeling.

        :param t: Current time step index
        :type t: int
        :param kwargs: Simulation parameters (remaining_load, storage temps, TRY_data, time_steps, etc.)
        :return: (heat_output[kW], electrical_output[kW]=0)
        :rtype: Tuple[float, float]

        .. note::
           Implements dual collector A/B approach, temperature stratification, and stagnation prevention.
        """
        # Extract simulation parameters from kwargs
        remaining_load = kwargs.get('remaining_load', 0.0)
        upper_storage_temperature = kwargs.get('upper_storage_temperature', 70.0)
        lower_storage_temperature = kwargs.get('lower_storage_temperature', 40.0)
        current_storage_state = kwargs.get('current_storage_state', 0.0)
        available_energy = kwargs.get('available_energy', 0.0)
        max_energy = kwargs.get('max_energy', 1000.0)
        Q_loss = kwargs.get('Q_loss', 0.0)
        TRY_data = kwargs.get('TRY_data', (20.0, 2.0, 200.0, 400.0))
        time_steps = kwargs.get('time_steps', np.array([]))
        duration = kwargs.get('duration', 1.0)

        # Initialize weather data and solar radiation calculations at t=0
        if t == 0:
            # Extract weather data components
            self.Lufttemperatur_L, self.Windgeschwindigkeit_L, self.Direktstrahlung_L, self.Globalstrahlung_L = TRY_data[0], TRY_data[1], TRY_data[2], TRY_data[3]
        
            # Calculate solar radiation on collector surface
            self.GT_H_Gk, self.K_beam_L, self.GbT_L, self.GdT_H_Dk_L = calculate_solar_radiation(
                time_steps, self.Globalstrahlung_L, self.Direktstrahlung_L, self.Longitude,
                self.STD_Longitude, self.Latitude, self.Albedo, 
                self.East_West_collector_azimuth_angle,
                self.Collector_tilt_angle, self.IAM_W, self.IAM_N
            )
        
        # Perform heat generation calculation only if system is active
        if self.active:
            # Calculate optical efficiency components for current time step
            Eta0b_neu_K_beam_GbT = self.Eta0b_neu * self.K_beam_L[t] * self.GbT_L[t]
            Eta0b_neu_Kthetadiff_GdT_H_Dk = self.Eta0b_neu * self.Kthetadiff * self.GdT_H_Dk_L[t]

            # Update storage parameters from external storage system
            self.QSmax = max_energy  # Maximum storage energy capacity [kWh]
            self.Speicherinhalt[t] = available_energy  # Current storage energy content [kWh]
            self.Speicherfüllstand[t] = current_storage_state  # Storage filling level [-]

            # Update storage heat losses and initialize stagnation state
            self.Verlustwärmestrom_Speicher_L[t] = Q_loss  # Storage heat losses [kW]
            self.Stagnation_L[t] = 0  # Initialize stagnation indicator

            # Initial conditions for first time step
            if t == 0:
                # Initialize storage and solar circuit temperatures
                self.TS_unten_L[t] = lower_storage_temperature
                self.TRL_Solar_L[t] = lower_storage_temperature
                
                # Calculate target temperature for solar circuit
                self.Zieltemperatur_Solaranlage_L[t] = (self.TS_unten_L[t] + self.Vorwärmung_K + 
                                                    self.DT_WT_Solar_K + self.DT_WT_Netz_K)
                
                # Calculate mean collector A temperature
                self.Tm_a_L[t] = (self.Zieltemperatur_Solaranlage_L[t] + self.TRL_Solar_L[t]) / 2
                
                # Initialize collector power outputs and temperatures
                self.Pkoll_a_L[t] = 0
                self.Tgkoll_a_L[t] = 9.3  # Initial glycol temperature [°C]
                
                # Calculate initial collector A temperature using thermal time constant
                self.T_koll_a_L[t] = (self.Lufttemperatur_L[t] - 
                                    (self.Lufttemperatur_L[t] - self.Tgkoll_a_L[t]) * 
                                    exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + 
                                    (self.Pkoll_a_L[t] * 3600) / (self.KollCeff_A * self.Bezugsfläche))
                
                # Initialize collector B with zero initial conditions
                self.Pkoll_b_L[t] = 0
                self.T_koll_b_L[t] = (self.Lufttemperatur_L[t] - 
                                    (self.Lufttemperatur_L[t] - 0) * 
                                    exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + 
                                    (self.Pkoll_b_L[t] * 3600) / (self.KollCeff_A * self.Bezugsfläche))
                
                # Initialize system glycol temperature
                self.Tgkoll_L[t] = 9.3

                # No collector field output at initialization
                self.Kollektorfeldertrag_L[t] = 0
                self.Wärmeleistung_kW[t] = min(self.Kollektorfeldertrag_L[t], remaining_load)

            else:
                # Calculate lower storage tank temperature based on stratification model
                if self.Speicherfüllstand[t - 1] >= 0.8:
                    # High filling level: complex stratification calculation
                    self.TS_unten_L[t] = (lower_storage_temperature + self.DT_WT_Netz_K + 
                                        (2/3 * (upper_storage_temperature - lower_storage_temperature) / 0.2 * 
                                        self.Speicherfüllstand[t - 1]) + 
                                        (1/3 * (upper_storage_temperature - lower_storage_temperature)) - 
                                        (2/3 * (upper_storage_temperature - lower_storage_temperature) / 0.2 * 
                                        self.Speicherfüllstand[t - 1]))
                else:
                    # Low filling level: simplified linear stratification
                    self.TS_unten_L[t] = (lower_storage_temperature + self.DT_WT_Netz_K + 
                                        (1/3 * (upper_storage_temperature - lower_storage_temperature) / 0.8) * 
                                        self.Speicherfüllstand[t - 1])

                # Calculate solar circuit target and return temperatures
                self.Zieltemperatur_Solaranlage_L[t] = (self.TS_unten_L[t] + self.Vorwärmung_K + 
                                                    self.DT_WT_Solar_K + self.DT_WT_Netz_K)
                self.TRL_Solar_L[t] = self.TS_unten_L[t] + self.DT_WT_Solar_K

                # Calculate mean collector A temperature for performance calculation
                self.Tm_a_L[t] = (self.Zieltemperatur_Solaranlage_L[t] + self.TRL_Solar_L[t]) / 2

                # Calculate collector A thermal loss coefficients
                c1a = self.Koll_c1 * (self.Tm_a_L[t] - self.Lufttemperatur_L[t])
                c2a = self.Koll_c2 * (self.Tm_a_L[t] - self.Lufttemperatur_L[t]) ** 2
                c3a = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[t] * (self.Tm_a_L[t] - self.Lufttemperatur_L[t])

                # Calculate collector A power output with thermal losses
                self.Pkoll_a_L[t] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - 
                                        c1a - c2a - c3a) * self.Bezugsfläche / 1000)
                
                # Calculate collector A temperature evolution
                self.T_koll_a_L[t] = (self.Lufttemperatur_L[t] - 
                                    (self.Lufttemperatur_L[t] - self.Tgkoll_a_L[t - 1]) * 
                                    exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + 
                                    (self.Pkoll_a_L[t] * 3600) / (self.KollCeff_A * self.Bezugsfläche))

                # Calculate collector B thermal loss coefficients using previous temperature
                c1b = self.Koll_c1 * (self.T_koll_b_L[t - 1] - self.Lufttemperatur_L[t])
                c2b = self.Koll_c2 * (self.T_koll_b_L[t - 1] - self.Lufttemperatur_L[t]) ** 2
                c3b = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[t] * (self.T_koll_b_L[t - 1] - self.Lufttemperatur_L[t])
                
                # Calculate collector B power output
                self.Pkoll_b_L[t] = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - 
                                        c1b - c2b - c3b) * self.Bezugsfläche / 1000)
                
                # Calculate collector B temperature evolution
                self.T_koll_b_L[t] = (self.Lufttemperatur_L[t] - 
                                    (self.Lufttemperatur_L[t] - self.Tgkoll_a_L[t - 1]) * 
                                    exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + 
                                    (self.Pkoll_b_L[t] * 3600) / (self.KollCeff_A * self.Bezugsfläche))
                
                # Calculate glycol temperature with target temperature limitation
                self.Tgkoll_a_L[t] = min(self.Zieltemperatur_Solaranlage_L[t], self.T_koll_a_L[t])

                # Calculate average collector temperature and system mean temperature
                self.Tm_koll_L[t] = (self.T_koll_a_L[t] + self.T_koll_b_L[t]) / 2
                Tm_sys = (self.Zieltemperatur_Solaranlage_L[t] + self.TRL_Solar_L[t]) / 2
                
                # Select appropriate mean temperature for system calculation
                if self.Tm_koll_L[t] < Tm_sys and self.Tm_koll_L[t - 1] < Tm_sys:
                    self.Tm_L[t] = self.Tm_koll_L[t]
                else:
                    self.Tm_L[t] = Tm_sys

                # Calculate system collector power output using system mean temperature
                c1 = self.Koll_c1 * (self.Tm_L[t] - self.Lufttemperatur_L[t])
                c2 = self.Koll_c2 * (self.Tm_L[t] - self.Lufttemperatur_L[t]) ** 2
                c3 = self.Koll_c3 * self.wcorr * self.Windgeschwindigkeit_L[t] * (self.Tm_L[t] - self.Lufttemperatur_L[t])
                Pkoll = max(0, (Eta0b_neu_K_beam_GbT + Eta0b_neu_Kthetadiff_GdT_H_Dk - 
                            c1 - c2 - c3) * self.Bezugsfläche / 1000)

                # Calculate collector temperature with thermal inertia
                T_koll = (self.Lufttemperatur_L[t] - 
                        (self.Lufttemperatur_L[t] - self.Tgkoll_L[t - 1]) * 
                        exp(-self.Koll_c1 / self.KollCeff_A * 3.6) + 
                        (Pkoll * 3600) / (self.KollCeff_A * self.Bezugsfläche))
                
                # Apply target temperature limitation to glycol temperature
                self.Tgkoll_L[t] = min(self.Zieltemperatur_Solaranlage_L[t], T_koll)

                # Calculate collector field output with temperature corrections
                if T_koll > self.Tgkoll_L[t - 1]:
                    # Apply temperature correction factor if target temperature is reached
                    Pkoll_temp_corr = ((T_koll - self.Tgkoll_L[t]) / (T_koll - self.Tgkoll_L[t - 1]) * Pkoll 
                                    if self.Tgkoll_L[t] >= self.Zieltemperatur_Solaranlage_L[t] else 0)

                    # Determine collector field output considering stagnation protection
                    self.Kollektorfeldertrag_L[t] = (max(0, min(Pkoll, Pkoll_temp_corr)) 
                                                    if self.Stagnation_L[t - 1] <= 0 else 0)
                else:
                    # No output if collector temperature is not increasing
                    self.Kollektorfeldertrag_L[t] = 0

                # Set system heat output to collector field output
                self.Wärmeleistung_kW[t] = self.Kollektorfeldertrag_L[t]

                # Check for stagnation conditions and activate protection
                same_day = (np.datetime_as_string(time_steps[t], unit='D') == 
                        np.datetime_as_string(time_steps[t - 1], unit='D'))
                excess_generation = self.Kollektorfeldertrag_L[t] > remaining_load
                storage_full = self.Speicherinhalt[t] >= self.QSmax
                
                self.Stagnation_L[t] = 1 if (same_day and excess_generation and storage_full) else 0

        else:
            # System inactive: no heat generation
            self.Wärmeleistung_kW[t] = 0

        # Update cumulative energy generation
        self.Wärmemenge_MWh += self.Wärmeleistung_kW[t] * duration / 1000  # Convert kW·h to MWh

        # Return heat output and zero electrical output (solar thermal only)
        return self.Wärmeleistung_kW[t], 0

    def calculate(self, economic_parameters: Dict[str, Union[float, str]], duration: float, 
                load_profile: np.ndarray, **kwargs) -> Dict[str, Union[str, float, np.ndarray]]:
        """
        Comprehensive system analysis including performance and economic evaluation.

        :param economic_parameters: Economic parameters (interest_rate, inflation_rate, subsidies, etc.)
        :type economic_parameters: Dict[str, Union[float, str]]
        :param duration: Time step duration [hours]
        :type duration: float
        :param load_profile: Heat demand profile [kW]
        :type load_profile: numpy.ndarray
        :param kwargs: VLT_L, RLT_L, TRY_data, time_steps
        :return: Results dict with Wärmemenge, Wärmeleistung_L, WGK, operational stats, environmental data
        :rtype: Dict[str, Union[str, float, np.ndarray]]

        .. note::
           Performs thermal simulation, operational analysis, economic cost assessment, and environmental evaluation.
        """
        # Extract additional calculation parameters
        VLT_L = kwargs.get('VLT_L', np.full(len(load_profile), 70.0))
        RLT_L = kwargs.get('RLT_L', np.full(len(load_profile), 40.0))
        TRY_data = kwargs.get('TRY_data', (np.full(len(load_profile), 10.0),) * 4)
        time_steps = kwargs.get('time_steps', np.arange(len(load_profile)))

        # Perform thermal calculation if not already completed
        if not self.calculated:
            # Execute complete solar thermal system calculation
            self.calculate_solar_thermal_with_storage(
                load_profile,
                VLT_L,
                RLT_L,
                TRY_data,
                time_steps,
                duration
            )
            
            # Mark calculation as completed
            self.calculated = True

        # Calculate operational statistics
        betrieb_mask = self.Wärmeleistung_kW > 0
        starts = np.diff(betrieb_mask.astype(int)) > 0
        self.Anzahl_Starts = np.sum(starts)
        self.Betriebsstunden = np.sum(betrieb_mask) * duration
        self.Betriebsstunden_pro_Start = (self.Betriebsstunden / self.Anzahl_Starts 
                                        if self.Anzahl_Starts > 0 else 0)

        # Calculate economic performance
        self.WGK = self.calculate_heat_generation_costs(economic_parameters)

        # Calculate environmental impact
        self.calculate_environmental_impact()

        # Compile comprehensive results dictionary
        results = {
            'tech_name': self.name,
            'Wärmemenge': self.Wärmemenge_MWh,
            'Wärmeleistung_L': self.Wärmeleistung_kW,
            'WGK': self.WGK,
            'Anzahl_Starts': self.Anzahl_Starts,
            'Betriebsstunden': self.Betriebsstunden,
            'Betriebsstunden_pro_Start': self.Betriebsstunden_pro_Start,
            'spec_co2_total': self.spec_co2_total,
            'primärenergie': self.primärenergie_Solarthermie,
            'Speicherladung_L': self.Speicherinhalt,
            'Speicherfüllstand_L': self.Speicherfüllstand,
            'color': "red"  # Red color for solar thermal visualization
        }

        return results

    def set_parameters(self, variables: List[float], variables_order: List[str], idx: int) -> None:
        """
        Set optimization parameters from optimizer variable list.

        :param variables: Optimization variable values
        :type variables: List[float]
        :param variables_order: Variable names corresponding to values
        :type variables_order: List[str]
        :param idx: Technology index for unique parameter identification
        :type idx: int

        .. note::
           Updates bruttofläche_STA and vs from variables with names f"bruttofläche_STA_{idx}" and f"vs_{idx}".
        """
        try:
            # Extract collector area from optimization variables
            area_var_name = f"bruttofläche_STA_{idx}"
            if area_var_name in variables_order:
                area_index = variables_order.index(area_var_name)
                self.bruttofläche_STA = variables[area_index]
            
            # Extract storage volume from optimization variables
            volume_var_name = f"vs_{idx}"
            if volume_var_name in variables_order:
                volume_index = variables_order.index(volume_var_name)
                self.vs = variables[volume_index]
                
            # Recalculate dependent parameters after optimization update
            self.init_calculation_constants()
            
        except (ValueError, IndexError) as e:
            print(f"Error setting optimization parameters for {self.name}: {e}")
            print(f"Available variables: {variables_order}")
            print(f"Expected variables: bruttofläche_STA_{idx}, vs_{idx}")

    def add_optimization_parameters(self, idx: int) -> Tuple[List[float], List[str], List[Tuple[float, float]]]:
        """
        Define optimization parameters for solar thermal system sizing.

        :param idx: Technology index for unique parameter names
        :type idx: int
        :return: (initial_values, variables_order, bounds)
        :rtype: Tuple[List[float], List[str], List[Tuple[float, float]]]

        .. note::
           Returns [bruttofläche_STA, vs] with bounds from opt_area_min/max and opt_volume_min/max.
        """
        # Define initial values from current system configuration
        initial_values = [self.bruttofläche_STA, self.vs]
        
        # Create unique variable names using technology index
        variables_order = [f"bruttofläche_STA_{idx}", f"vs_{idx}"]
        
        # Define optimization bounds from system constraints
        bounds = [
            (self.opt_area_min, self.opt_area_max),      # Collector area bounds [m²]
            (self.opt_volume_min, self.opt_volume_max)   # Storage volume bounds [m³]
        ]
        
        return initial_values, variables_order, bounds

    def get_display_text(self) -> str:
        """
        Generate formatted display text for GUI representation.

        :return: Formatted text with key system parameters
        :rtype: str
        """
        return (f"{self.name}: Bruttokollektorfläche: {self.bruttofläche_STA:.1f} m², "
                f"Volumen Solarspeicher: {self.vs:.1f} m³, Kollektortyp: {self.Typ}, "
                f"spez. Kosten Speicher: {self.kosten_speicher_spez:.1f} €/m³, "
                f"spez. Kosten Flachkollektor: {self.kosten_fk_spez:.1f} €/m², "
                f"spez. Kosten Röhrenkollektor: {self.kosten_vrk_spez:.1f} €/m²")

    def extract_tech_data(self) -> Tuple[str, str, str, str]:
        """
        Extract technology data for reporting and documentation.

        :return: (name, dimensions, costs, full_costs)
        :rtype: Tuple[str, str, str, str]
        """
        dimensions = (f"Bruttokollektorfläche: {self.bruttofläche_STA:.1f} m², "
                    f"Speichervolumen: {self.vs:.1f} m³, Kollektortyp: {self.Typ}")
        costs = (f"Investitionskosten Speicher: {self.Investitionskosten_Speicher:.1f} €, "
                f"Investitionskosten STA: {self.Investitionskosten_STA:.1f} €")
        full_costs = f"{self.Investitionskosten:.1f}"
        
        return self.name, dimensions, costs, full_costs

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SolarThermal':
        """
        Create SolarThermal object from dictionary representation.

        :param data: Dictionary containing SolarThermal attributes
        :type data: Dict[str, Any]
        :return: Restored SolarThermal object
        :rtype: SolarThermal

        .. note::
           Ensures IAM dictionaries are properly restored when loading saved objects.
        """
        # Create object using base class method
        obj = super().from_dict(data)
        
        # Ensure IAM dictionaries exist and are valid
        # If they are missing or empty, reinitialize calculation constants
        if not hasattr(obj, 'IAM_W') or not obj.IAM_W or not isinstance(obj.IAM_W, dict):
            obj.init_calculation_constants()
        elif not hasattr(obj, 'IAM_N') or not obj.IAM_N or not isinstance(obj.IAM_N, dict):
            obj.init_calculation_constants()
        
        return obj

class SolarThermalStrategy(BaseStrategy):
    """
    Control strategy for solar thermal systems.

    :param charge_on: Temperature threshold for activation [°C]
    :type charge_on: int
    :param charge_off: Temperature threshold for deactivation [°C], optional
    :type charge_off: int, optional

    .. note::
       Operates continuously when solar irradiation available.
    """
    
    def __init__(self, charge_on: int, charge_off: Optional[int] = None):
        """
        Initialize solar thermal control strategy.

        :param charge_on: Activation temperature threshold [°C]
        :type charge_on: int
        :param charge_off: Deactivation temperature threshold [°C], optional
        :type charge_off: int, optional
        """
        super().__init__(charge_on, charge_off)

    def decide_operation(self, current_state: float, upper_storage_temp: float, 
                        lower_storage_temp: float, remaining_demand: float) -> bool:
        """
        Decide solar thermal operation (always True for renewable energy priority).

        :param current_state: Current system state (not used)
        :type current_state: float
        :param upper_storage_temp: Upper storage temperature [°C] (not used)
        :type upper_storage_temp: float
        :param lower_storage_temp: Lower storage temperature [°C] (not used)
        :type lower_storage_temp: float
        :param remaining_demand: Remaining heat demand [kW] (not used)
        :type remaining_demand: float
        :return: Always True (renewable energy priority strategy)
        :rtype: bool
        """
        # Solar thermal operates continuously when solar irradiation is available
        # Operation is weather-dependent and prioritizes renewable energy harvesting
        return True