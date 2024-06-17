import numpy as np
from datetime import datetime, timedelta

# Define the SolarThermal class
class SolarThermal:
    def __init__(self, Bruttofläche_STA, VS, Typ, storage=None):
        self.Bruttofläche_STA = Bruttofläche_STA
        self.VS = VS
        self.Typ = Typ
        self.storage = storage  # Use the shared storage object

    def generate_heat(self, Last_L, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, duration):
        if not isinstance(Last_L, list):
            Last_L = [Last_L]  # Ensure Last_L is a list
        Gesamtwärmemenge, Speicher_Wärmeoutput_L, Speicherladung_L, Speicherfüllstand_L = self.calculate_heat(Last_L, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, duration)

        if self.storage:
            for energy in Speicher_Wärmeoutput_L:
                self.storage.add_energy(energy)

        return Gesamtwärmemenge, Speicher_Wärmeoutput_L

    def calculate_heat(self, Last_L, VLT_L, RLT_L, TRY, time_steps, calc1, calc2, duration):
        Bruttofläche_STA = self.Bruttofläche_STA
        VS = self.VS
        Typ = self.Typ
        # Here we simulate the Berechnung_STA function with a placeholder
        return np.random.random(), np.random.random(size=len(Last_L)), np.random.random(size=len(Last_L)), np.random.random(size=len(Last_L))

# Define the Storage class
class Storage:
    def __init__(self, capacity, max_temp=90):
        self.capacity = capacity
        self.max_temp = max_temp
        self.current_energy = 0  # in Joules
        self.current_temp = 20  # initial temperature

    def add_energy(self, energy):
        self.current_energy += energy
        if self.current_energy > self.capacity:
            self.current_energy = self.capacity
        self.update_temp()

    def remove_energy(self, energy):
        self.current_energy -= energy
        if self.current_energy < 0:
            self.current_energy = 0
        self.update_temp()

    def update_temp(self):
        self.current_temp = (self.current_energy / self.capacity) * self.max_temp

    def get_energy(self):
        return self.current_energy

    def get_temp(self):
        return self.current_temp

# Define the CHP class
class CHP:
    def __init__(self, name, th_Leistung_BHKW, storage=None, spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850):
        self.name = name
        self.th_Leistung_BHKW = th_Leistung_BHKW
        self.storage = storage  # Use the shared storage object
        self.spez_Investitionskosten_GBHKW = spez_Investitionskosten_GBHKW
        self.spez_Investitionskosten_HBHKW = spez_Investitionskosten_HBHKW

    def generate_heat(self, Last_L, duration, el_Wirkungsgrad=0.33, KWK_Wirkungsgrad=0.9):
        if not isinstance(Last_L, list):
            Last_L = [Last_L]  # Ensure Last_L is a list
        Wärmeleistung_BHKW_L = self.calculate_heat(Last_L, duration, el_Wirkungsgrad, KWK_Wirkungsgrad)

        if self.storage:
            for energy in Wärmeleistung_BHKW_L:
                self.storage.add_energy(energy)

        return Wärmeleistung_BHKW_L

    def calculate_heat(self, Last_L, duration, el_Wirkungsgrad, KWK_Wirkungsgrad):
        thermischer_Wirkungsgrad = KWK_Wirkungsgrad - el_Wirkungsgrad
        self.el_Leistung_Soll = self.th_Leistung_BHKW / thermischer_Wirkungsgrad * el_Wirkungsgrad

        Wärmeleistung_BHKW_L = np.where(Last_L >= self.th_Leistung_BHKW, self.th_Leistung_BHKW, Last_L)
        return Wärmeleistung_BHKW_L

# Define the HeatSystem class
class HeatSystem:
    def __init__(self, solar_thermal, chp, storage_capacity):
        self.storage = Storage(storage_capacity)  # Create a shared storage object
        self.solar_thermal = solar_thermal
        self.solar_thermal.storage = self.storage  # Link the storage to the solar thermal
        self.chp = chp
        self.chp.storage = self.storage  # Link the storage to the CHP

    def simulate(self, demands, other_parameters):
        for demand in demands:
            Gesamtwärmemenge, Speicher_Wärmeoutput_L = self.solar_thermal.generate_heat(demand, *other_parameters)
            chp_heat = self.chp.generate_heat(demand - self.storage.get_energy(), *other_parameters)

            total_generated = sum(Speicher_Wärmeoutput_L) + sum(chp_heat)
            if total_generated > demand:
                self.storage.add_energy(total_generated - demand)
            else:
                self.storage.remove_energy(demand - total_generated)

            print(f"Current Storage Energy: {self.storage.get_energy()} J")
            print(f"Current Storage Temperature: {self.storage.get_temp()} °C")

# Example usage
# Initialize the components
solar_thermal = SolarThermal(500, 20, "Vakuumröhrenkollektor")
chp = CHP("BHKW", 100)
storage_capacity = 1000000  # example capacity in Joules

# Create the HeatSystem instance
heat_system = HeatSystem(solar_thermal, chp, storage_capacity)

# Define the demands and other parameters
# For the sake of this example, let's create a list of demands and necessary parameters
demands = [300, 400, 500, 600, 700]  # example demand values in Joules

# Simulating hourly data for one day (24 hours)
time_steps = np.array([datetime(2022, 1, 1, hour).timestamp() for hour in range(24)])
calc1, calc2 = 0, 23  # indices for the calculation period
duration = 3600  # 1 hour in seconds

# Placeholder values for TRY (Test Reference Year) data, VLT_L and RLT_L
VLT_L = np.random.uniform(60, 80, len(time_steps))
RLT_L = np.random.uniform(40, 60, len(time_steps))
TRY = [np.random.uniform(5, 15, len(time_steps)) for _ in range(4)]  # temperature, wind speed, direct radiation, global radiation

other_parameters = (VLT_L, RLT_L, TRY, time_steps, calc1, calc2, duration)

# Simulate the system
heat_system.simulate(demands, other_parameters)
