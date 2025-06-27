"""
Heat Requirement Calculation for LOD2 Buildings Module
======================================================

This module implements comprehensive building energy demand calculation for district heating
applications using Level of Detail 2 (LOD2) building geometry data.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-10

It combines 3D building information with thermal building physics, Test Reference Year (TRY) weather data, and
TABULA building typology standards to calculate heating and domestic hot water demands.

The module provides automated heat demand assessment for entire building stocks using
standardized German building energy calculation methods. It supports both individual
building analysis and batch processing of municipal building datasets for district
heating network planning and sizing applications.
"""

import pandas as pd
from typing import Dict, Any, Optional, Tuple, Union

from districtheatingsim.lod2.filter_LOD2 import spatial_filter_with_polygon, process_lod2, calculate_centroid_and_geocode
from districtheatingsim.utilities.test_reference_year import import_TRY
from districtheatingsim.utilities.utilities import get_resource_path

class Building:
    """
    Building energy model for heat demand calculation using LOD2 geometry and TABULA standards.

    This class implements building thermal physics calculations according to German standards
    for district heating applications. It uses LOD2 building geometry data combined with
    TABULA building typology thermal properties to calculate annual heating and domestic
    hot water demands based on hourly weather data from Test Reference Years.

    Attributes
    ----------
    ground_area : float
        Building ground floor area [m²]. Used for domestic hot water demand calculation.
    wall_area : float
        Total exterior wall area including windows and doors [m²].
    roof_area : float
        Total roof area [m²]. Includes all exposed roof surfaces.
    building_volume : float
        Total heated building volume [m³]. Used for ventilation heat loss calculation.
    filename_TRY : str
        Path to Test Reference Year weather data file for hourly temperature data.
    u_values : Dict[str, float]
        Thermal properties and building parameters dictionary.

    Notes
    -----
    Calculation Methodology:
        The heat demand calculation follows simplified DIN EN 12831 methodology:
        
        1. **Transmission Heat Loss**: Through building envelope components
        2. **Ventilation Heat Loss**: Natural air infiltration without heat recovery
        3. **Linear Heat Demand Model**: Temperature-dependent heating demand curve
        4. **Domestic Hot Water**: Area-based constant annual demand
        
    Standard U-Values (W/m²K):
        - Ground: 0.31 (typical insulated basement floor)
        - Wall: 0.23 (modern insulated exterior wall)
        - Roof: 0.19 (well-insulated pitched roof)
        - Windows: 1.3 (double-glazed windows)
        - Doors: 1.3 (insulated exterior doors)

    Building Parameters:
        - Air change rate: 0.5 h⁻¹ (natural ventilation)
        - Room temperature: 20°C (standard indoor temperature)
        - Design outdoor temperature: -12°C (German climate)
        - Window fraction: 10% of wall area
        - Door fraction: 1% of wall area
        - Domestic hot water: 12.8 kWh/m²a (residential standard)

    Examples
    --------
    >>> # Create building with custom geometry
    >>> building = Building(
    ...     ground_area=100.0,    # 100 m² ground floor
    ...     wall_area=200.0,      # 200 m² exterior walls
    ...     roof_area=100.0,      # 100 m² roof area
    ...     building_volume=300.0  # 300 m³ heated volume
    ... )
    >>> 
    >>> # Calculate annual heat demand
    >>> building.calc_yearly_heat_demand()
    >>> print(f"Annual heat demand: {building.yearly_heat_demand:.1f} kWh/a")
    >>> print(f"Hot water share: {building.warm_water_share:.1%}")

    >>> # Use TABULA building typology
    >>> tabula_building = Building(
    ...     ground_area=150.0, wall_area=300.0, roof_area=150.0, building_volume=450.0,
    ...     u_type="EFH",           # Single family house
    ...     building_state="existing"  # Existing building state
    ... )
    >>> tabula_building.calc_yearly_heat_demand()

    >>> # Custom thermal properties
    >>> custom_u_values = {
    ...     'wall_u': 0.15,        # High-performance wall
    ...     'roof_u': 0.12,        # Passive house roof
    ...     'window_u': 0.8        # Triple-glazed windows
    ... }
    >>> efficient_building = Building(
    ...     ground_area=100.0, wall_area=200.0, roof_area=100.0, building_volume=300.0,
    ...     u_values=custom_u_values
    ... )

    See Also
    --------
    calculate_heat_demand_for_lod2_area : Batch processing for building areas
    load_u_values : TABULA building typology integration
    """

    STANDARD_U_VALUES = {
        'ground_u': 0.31,           # Ground floor U-value [W/m²K]
        'wall_u': 0.23,             # Wall U-value [W/m²K]
        'roof_u': 0.19,             # Roof U-value [W/m²K]
        'window_u': 1.3,            # Window U-value [W/m²K]
        'door_u': 1.3,              # Door U-value [W/m²K]
        'air_change_rate': 0.5,     # Air change rate [1/h]
        'floors': 4,                # Number of floors (for hot water calculation)
        'fracture_windows': 0.10,   # Window fraction of wall area [-]
        'fracture_doors': 0.01,     # Door fraction of wall area [-]
        'min_air_temp': -12,        # Design outdoor temperature [°C]
        'room_temp': 20,            # Indoor temperature [°C]
        'max_air_temp_heating': 15, # Heating limit temperature [°C]
        'ww_demand_kWh_per_m2': 12.8  # Domestic hot water demand [kWh/m²a]
    }

    def __init__(self, 
                 ground_area: float, 
                 wall_area: float, 
                 roof_area: float, 
                 building_volume: float, 
                 filename_TRY: str = None,
                 u_type: Optional[str] = None, 
                 building_state: Optional[str] = None, 
                 u_values: Optional[Dict[str, float]] = None):
        """
        Initialize Building object with geometry and thermal properties.

        Parameters
        ----------
        ground_area : float
            Building ground floor area [m²]. Must be positive value.
        wall_area : float
            Total exterior wall area including openings [m²]. Must be positive value.
        roof_area : float
            Total roof area [m²]. Must be positive value.
        building_volume : float
            Total heated building volume [m³]. Must be positive value.
        filename_TRY : str, optional
            Path to Test Reference Year weather data file.
            Default uses included TRY data for Dresden, Germany.
        u_type : str, optional
            TABULA building type identifier. Examples: "EFH", "RH", "MFH", "AB".
            Used with building_state to load standardized thermal properties.
        building_state : str, optional
            TABULA building state identifier. Examples: "existing", "usual_refurbishment", "advanced_refurbishment".
            Defines thermal performance level for building type.
        u_values : Dict[str, float], optional
            Custom thermal properties dictionary overriding standard values.
            Keys should match STANDARD_U_VALUES keys for proper integration.

        Notes
        -----
        Parameter Priority:
            1. Custom u_values dictionary (highest priority)
            2. TABULA typology (u_type + building_state)
            3. Standard default values (fallback)

        TABULA Building Types:
            - **EFH**: Single family house (Einfamilienhaus)
            - **RH**: Row house (Reihenhaus)
            - **MFH**: Multi-family house (Mehrfamilienhaus)
            - **AB**: Apartment building (Geschosswohnungsbau)

        Building States:
            - **existing**: Original building without renovation
            - **usual_refurbishment**: Standard renovation measures
            - **advanced_refurbishment**: Deep energy renovation
            - **new_building**: New construction standards

        Examples
        --------
        >>> # Standard building with default values
        >>> building = Building(100.0, 200.0, 100.0, 300.0)

        >>> # TABULA building typology
        >>> building = Building(
        ...     150.0, 300.0, 150.0, 450.0,
        ...     u_type="EFH", 
        ...     building_state="usual_refurbishment"
        ... )

        >>> # High-performance building with custom properties
        >>> custom_values = {'wall_u': 0.15, 'roof_u': 0.12, 'window_u': 0.8}
        >>> building = Building(
        ...     100.0, 200.0, 100.0, 300.0,
        ...     u_values=custom_values
        ... )
        """
        self.ground_area = ground_area
        self.wall_area = wall_area
        self.roof_area = roof_area
        self.building_volume = building_volume
        self.filename_TRY = filename_TRY or get_resource_path(
            "data\\TRY\\TRY_511676144222\\TRY2015_511676144222_Jahr.dat"
        )
        self.u_values = self.STANDARD_U_VALUES.copy()
        
        # Apply thermal properties in priority order
        if u_values:
            self.u_values.update(u_values)
        elif u_type and building_state:
            self.u_values.update(self.load_u_values(u_type, building_state))

    def calc_heat_demand(self) -> None:
        """
        Calculate building heat demand components for design conditions.

        This method calculates the maximum heating power demand under design outdoor
        temperature conditions. It determines transmission and ventilation heat losses
        through the building envelope and natural air infiltration.

        Notes
        -----
        Calculation Steps:
            1. Calculate window and door areas from wall area fractions
            2. Determine effective wall area excluding openings
            3. Calculate heat loss coefficients for all envelope components
            4. Compute transmission heat loss through building envelope
            5. Calculate ventilation heat loss from air infiltration
            6. Sum total maximum heating demand

        Heat Loss Components:
            - **Transmission**: Heat loss through walls, roof, ground, windows, doors
            - **Ventilation**: Heat loss from air change (natural infiltration)
            - **Solar/Internal Gains**: Not considered (conservative approach)

        Simplified Assumptions:
            - Natural ventilation without heat recovery
            - No thermal bridging corrections
            - Steady-state heat transfer conditions
            - Uniform indoor temperature distribution

        Results Stored:
            - window_area : Window area [m²]
            - door_area : Door area [m²]
            - real_wall_area : Net wall area excluding openings [m²]
            - total_heat_loss_per_K : Total heat loss coefficient [W/K]
            - transmission_heat_loss : Transmission heat loss [W]
            - ventilation_heat_loss : Ventilation heat loss [W]
            - max_heating_demand : Maximum heating power demand [W]

        Examples
        --------
        >>> building = Building(100.0, 200.0, 100.0, 300.0)
        >>> building.calc_heat_demand()
        >>> print(f"Maximum heating demand: {building.max_heating_demand:.0f} W")
        >>> print(f"Heat loss coefficient: {building.total_heat_loss_per_K:.1f} W/K")
        """
        # Calculate opening areas and net wall area
        self.window_area = self.wall_area * self.u_values["fracture_windows"]
        self.door_area = self.wall_area * self.u_values["fracture_doors"]
        self.real_wall_area = self.wall_area - self.window_area - self.door_area

        # Calculate heat loss coefficients per component [W/K]
        heat_loss_per_K = {
            'wall': self.real_wall_area * self.u_values["wall_u"],
            'ground': self.ground_area * self.u_values["ground_u"],
            'roof': self.roof_area * self.u_values["roof_u"],
            'window': self.window_area * self.u_values["window_u"],
            'door': self.door_area * self.u_values["door_u"]
        }

        self.total_heat_loss_per_K = sum(heat_loss_per_K.values())

        # Calculate design temperature difference
        self.dT_max_K = self.u_values["room_temp"] - self.u_values["min_air_temp"]

        # Calculate transmission heat loss [W]
        self.transmission_heat_loss = self.total_heat_loss_per_K * self.dT_max_K

        # Calculate ventilation heat loss [W]
        # Factor 0.34 = air density × specific heat capacity [Wh/m³K]
        self.ventilation_heat_loss = (0.34 * self.u_values["air_change_rate"] * 
                                    self.building_volume * self.dT_max_K)

        # Total maximum heating demand [W]
        self.max_heating_demand = self.transmission_heat_loss + self.ventilation_heat_loss

    def calc_yearly_heating_demand(self) -> None:
        """
        Calculate annual heating energy demand using hourly weather data.

        This method uses Test Reference Year hourly temperature data to calculate
        the annual heating energy demand. It applies a linear heat demand model
        based on outdoor temperature with heating limit temperature consideration.

        Notes
        -----
        Linear Heat Demand Model:
            The heating demand follows a linear relationship with outdoor temperature:
            
            Q_heating = max(0, m × T_outdoor + b)
            
            Where:
            - m: slope coefficient [W/K]
            - b: intercept [W]
            - T_outdoor: hourly outdoor temperature [°C]

        Model Parameters:
            - **Heating limit**: No heating above 15°C outdoor temperature
            - **Design point**: Maximum demand at -12°C outdoor temperature
            - **Linear interpolation**: Between limit and design temperatures

        Energy Integration:
            - Sums hourly heating power demands over full year
            - Converts from Wh to kWh (division by 1000)
            - Only includes hours below heating limit temperature

        Weather Data:
            Uses standardized Test Reference Year (TRY) hourly temperature data
            representing typical meteorological conditions for building location.

        Results Stored:
            - temperature : List of hourly temperatures [°C]
            - yearly_heating_demand : Annual heating energy [kWh/a]

        Examples
        --------
        >>> building = Building(100.0, 200.0, 100.0, 300.0)
        >>> building.calc_heat_demand()  # Required prerequisite
        >>> building.calc_yearly_heating_demand()
        >>> print(f"Annual heating demand: {building.yearly_heating_demand:.0f} kWh/a")

        See Also
        --------
        import_TRY : Weather data import function
        calc_heat_demand : Required prerequisite calculation
        """
        # Load hourly temperature data from TRY file
        self.temperature, _, _, _, _ = import_TRY(self.filename_TRY)
        
        # Calculate linear heat demand model coefficients
        temp_range = self.u_values["min_air_temp"] - self.u_values["max_air_temp_heating"]
        m = self.max_heating_demand / temp_range  # Slope [W/K]
        b = -m * self.u_values["max_air_temp_heating"]  # Intercept [W]

        # Calculate annual heating energy demand
        heating_hours = [temp for temp in self.temperature 
                        if temp < self.u_values["max_air_temp_heating"]]
        
        annual_heating_Wh = sum(max(m * temp + b, 0) for temp in heating_hours)
        self.yearly_heating_demand = annual_heating_Wh / 1000  # Convert to kWh

    def calc_yearly_warm_water_demand(self) -> None:
        """
        Calculate annual domestic hot water energy demand.

        This method calculates the annual energy demand for domestic hot water
        preparation based on heated floor area and standardized specific demand
        values according to German building energy standards.

        Notes
        -----
        Calculation Method:
            Annual DHW demand = Specific demand × Floor area × Number of floors
            
            Default specific demand: 12.8 kWh/m²a (residential buildings)

        Standard Values:
            Based on German energy standards and typical usage patterns:
            - Residential buildings: 12.8 kWh/m²a
            - Office buildings: 5-8 kWh/m²a
            - Schools: 3-5 kWh/m²a
            - Hotels: 20-30 kWh/m²a

        Floor Area Calculation:
            Uses ground floor area multiplied by number of floors to estimate
            total heated floor area for domestic hot water demand calculation.

        Assumptions:
            - Constant annual demand (no seasonal variation)
            - Standard occupancy and usage patterns
            - Centralized hot water system efficiency included in specific values

        Results Stored:
            - yearly_warm_water_demand : Annual DHW energy demand [kWh/a]

        Examples
        --------
        >>> building = Building(100.0, 200.0, 100.0, 300.0)
        >>> building.calc_yearly_warm_water_demand()
        >>> print(f"DHW demand: {building.yearly_warm_water_demand:.0f} kWh/a")

        >>> # Custom DHW demand for office building
        >>> office_values = {'ww_demand_kWh_per_m2': 6.0, 'floors': 3}
        >>> office = Building(200.0, 400.0, 200.0, 600.0, u_values=office_values)
        >>> office.calc_yearly_warm_water_demand()
        """
        # Calculate annual domestic hot water demand
        heated_floor_area = self.ground_area * self.u_values["floors"]
        self.yearly_warm_water_demand = (self.u_values["ww_demand_kWh_per_m2"] * 
                                       heated_floor_area)

    def calc_yearly_heat_demand(self) -> None:
        """
        Calculate total annual heat demand including heating and domestic hot water.

        This method orchestrates the complete building energy demand calculation
        by combining space heating and domestic hot water demands. It provides
        the total annual heat demand and calculates the domestic hot water share
        for district heating system sizing and operation planning.

        Notes
        -----
        Calculation Sequence:
            1. Maximum heat demand calculation (design conditions)
            2. Annual heating energy demand (weather-dependent)
            3. Annual domestic hot water demand (constant)
            4. Total demand summation and DHW share calculation

        Result Components:
            - **Space Heating**: Weather-dependent demand for indoor comfort
            - **Domestic Hot Water**: Constant annual demand for hot water preparation
            - **Total Heat Demand**: Sum of both components
            - **DHW Share**: Fraction of total demand for hot water (%)

        District Heating Relevance:
            - Total demand: Network sizing and peak load calculation
            - DHW share: Summer operation planning and base load determination
            - Seasonal patterns: Network operation optimization

        Results Stored:
            - yearly_heat_demand : Total annual heat demand [kWh/a]
            - yearly_heating_demand : Space heating demand [kWh/a]
            - yearly_warm_water_demand : DHW demand [kWh/a]
            - warm_water_share : DHW fraction of total demand [-]

        Examples
        --------
        >>> building = Building(100.0, 200.0, 100.0, 300.0)
        >>> building.calc_yearly_heat_demand()
        >>> 
        >>> print(f"Total annual demand: {building.yearly_heat_demand:.0f} kWh/a")
        >>> print(f"Heating demand: {building.yearly_heating_demand:.0f} kWh/a")
        >>> print(f"DHW demand: {building.yearly_warm_water_demand:.0f} kWh/a")
        >>> print(f"DHW share: {building.warm_water_share:.1%}")

        >>> # Analyze demand pattern
        >>> specific_demand = building.yearly_heat_demand / building.ground_area
        >>> print(f"Specific heat demand: {specific_demand:.0f} kWh/m²a")

        See Also
        --------
        calc_heat_demand : Maximum heat demand calculation
        calc_yearly_heating_demand : Annual heating energy calculation
        calc_yearly_warm_water_demand : Annual DHW energy calculation
        """
        # Execute complete calculation sequence
        self.calc_heat_demand()
        self.calc_yearly_heating_demand()
        self.calc_yearly_warm_water_demand()
        
        # Calculate total annual heat demand
        self.yearly_heat_demand = (self.yearly_heating_demand + 
                                 self.yearly_warm_water_demand)
        
        # Calculate domestic hot water share
        if self.yearly_heat_demand > 0:
            self.warm_water_share = (self.yearly_warm_water_demand / 
                                   self.yearly_heat_demand)
        else:
            self.warm_water_share = 0.0

    def load_u_values(self, u_type: str, building_state: str) -> Dict[str, float]:
        """
        Load TABULA building typology thermal properties from standardized database.

        This method retrieves thermal properties (U-values and building parameters)
        from the TABULA building typology database based on building type and
        renovation state. TABULA provides standardized building characteristics
        for European building stock assessment and energy planning.

        Parameters
        ----------
        u_type : str
            TABULA building type identifier specifying construction and usage type.
            Examples: "EFH" (single family), "MFH" (multi-family), "AB" (apartment block).
        building_state : str
            TABULA building state identifier specifying renovation level.
            Examples: "existing", "usual_refurbishment", "advanced_refurbishment".

        Returns
        -------
        Dict[str, float]
            Dictionary containing thermal properties for the specified building type and state.
            Returns empty dictionary if no matching entry found.

        Notes
        -----
        TABULA Database:
            The TABULA building typology provides representative building types
            for European building stock analysis with standardized thermal properties
            based on construction period, building type, and renovation state.

        Building Type Categories:
            - **EFH**: Single family house (detached)
            - **RH**: Row house (terraced house)
            - **MFH**: Multi-family house (3-6 units)
            - **AB**: Apartment building (>6 units)

        Building States:
            - **existing**: Original construction without major renovation
            - **usual_refurbishment**: Standard renovation (partial measures)
            - **advanced_refurbishment**: Deep renovation (comprehensive measures)
            - **new_building**: New construction according to current standards

        Database Structure:
            CSV file with columns: Typ, building_state, [thermal properties]
            Located at: data/TABULA/standard_u_values_TABULA.csv

        Examples
        --------
        >>> building = Building(100.0, 200.0, 100.0, 300.0)
        >>> 
        >>> # Load existing single family house properties
        >>> efh_existing = building.load_u_values("EFH", "existing")
        >>> print(f"EFH existing wall U-value: {efh_existing.get('wall_u', 'N/A')} W/m²K")
        >>> 
        >>> # Load renovated multi-family house properties
        >>> mfh_renovated = building.load_u_values("MFH", "usual_refurbishment")
        >>> print(f"MFH renovated roof U-value: {mfh_renovated.get('roof_u', 'N/A')} W/m²K")

        >>> # Compare different renovation states
        >>> states = ["existing", "usual_refurbishment", "advanced_refurbishment"]
        >>> for state in states:
        ...     values = building.load_u_values("EFH", state)
        ...     wall_u = values.get('wall_u', 'N/A')
        ...     print(f"EFH {state}: wall U-value = {wall_u} W/m²K")

        Raises
        ------
        FileNotFoundError
            If TABULA database file cannot be found at expected location.
        KeyError
            If required columns are missing from database file.

        See Also
        --------
        STANDARD_U_VALUES : Default thermal properties fallback
        __init__ : Building initialization with TABULA integration
        """
        try:
            # Load TABULA database
            df = pd.read_csv(
                get_resource_path('data\\TABULA\\standard_u_values_TABULA.csv'), 
                sep=";"
            )
            
            # Filter for specified building type and state
            u_values_row = df[(df['Typ'] == u_type) & (df['building_state'] == building_state)]
            
            if not u_values_row.empty:
                # Convert first matching row to dictionary, excluding identifier columns
                u_values_dict = u_values_row.iloc[0].drop(['Typ', 'building_state']).to_dict()
                print(f"Loaded TABULA values for {u_type} ({building_state})")
                return u_values_dict
            else:
                print(f"No TABULA values found for type '{u_type}' and state '{building_state}'. Using standard values.")
                return {}
                
        except FileNotFoundError:
            print(f"TABULA database file not found. Using standard values.")
            return {}
        except Exception as e:
            print(f"Error loading TABULA values: {e}. Using standard values.")
            return {}

def calculate_heat_demand_for_lod2_area(lod_geojson_path: str, 
                                      polygon_shapefile_path: str, 
                                      output_geojson_path: str, 
                                      output_csv_path: str) -> None:
    """
    Calculate heat demand for all buildings in a specified LOD2 area with user interaction.

    This function provides an interactive workflow for processing entire building areas
    from LOD2 data. It combines spatial filtering, geometry processing, geocoding,
    and heat demand calculation with user input for building type classification.

    Parameters
    ----------
    lod_geojson_path : str
        Path to input LOD2 GeoJSON file containing 3D building geometries.
        Must contain valid MultiPolygon or Polygon geometries with height information.
    polygon_shapefile_path : str
        Path to polygon shapefile defining the area of interest for spatial filtering.
        Buildings intersecting this polygon will be processed.
    output_geojson_path : str
        Path for filtered LOD2 building data output.
        Intermediate file containing spatially filtered buildings.
    output_csv_path : str
        Path for final heat demand results output.
        Contains building information and calculated heat demands.

    Notes
    -----
    Processing Workflow:
        1. **Spatial Filtering**: Extract buildings within specified area polygon
        2. **Geometry Processing**: Calculate building areas and volumes from LOD2 data
        3. **Geocoding**: Determine building addresses using reverse geocoding
        4. **Interactive Classification**: User input for building type and state
        5. **Heat Demand Calculation**: Apply TABULA typology and calculate demands

    User Interaction:
        For each building, the function prompts for:
        - Building type (TABULA category: EFH, RH, MFH, AB, etc.)
        - Building state (renovation level: existing, usual_refurbishment, etc.)

    Data Requirements:
        - **LOD2 Data**: 3D building geometries with roof and wall surfaces
        - **Area Polygon**: Spatial boundary for building selection
        - **Internet Connection**: Required for geocoding services
        - **TABULA Database**: Thermal properties reference data

    Output Information:
        - Building geometry and volume data
        - Calculated heating and DHW demands
        - Building addresses and classifications
        - Thermal properties applied

    Examples
    --------
    >>> # Process municipal building area
    >>> calculate_heat_demand_for_lod2_area(
    ...     "data/lod2_buildings.geojson",
    ...     "data/study_area.shp",
    ...     "output/filtered_buildings.geojson",
    ...     "output/heat_demands.csv"
    ... )
    # Interactive prompts for each building:
    # Building ID: 1, Hauptstraße 15
    # Welchen Gebäudetyp hat das Gebäude?: EFH
    # Welchen energetischen Zustand hat das Gebäude?: existing

    >>> # Batch processing multiple areas
    >>> areas = ["downtown", "residential_north", "industrial_east"]
    >>> for area in areas:
    ...     lod2_file = f"data/{area}_lod2.geojson"
    ...     polygon_file = f"data/{area}_boundary.shp"
    ...     output_geojson = f"results/{area}_buildings.geojson"
    ...     output_csv = f"results/{area}_demands.csv"
    ...     
    ...     calculate_heat_demand_for_lod2_area(
    ...         lod2_file, polygon_file, output_geojson, output_csv
    ...     )

    Raises
    ------
    FileNotFoundError
        If input LOD2 or polygon files cannot be found.
    ValueError
        If building geometry data is incomplete or invalid.
    ConnectionError
        If geocoding services are unavailable.

    See Also
    --------
    spatial_filter_with_polygon : Spatial filtering function
    process_lod2 : LOD2 geometry processing
    calculate_centroid_and_geocode : Address geocoding
    Building : Heat demand calculation class
    """
    print("Starting LOD2 area heat demand calculation...")
    print(f"Input LOD2 file: {lod_geojson_path}")
    print(f"Area boundary: {polygon_shapefile_path}")
    
    # Step 1: Spatial filtering to extract buildings in area of interest
    print("\n--- Step 1: Spatial Filtering ---")
    spatial_filter_with_polygon(lod_geojson_path, polygon_shapefile_path, output_geojson_path)

    # Step 2: Process LOD2 data to extract building geometry information
    print("\n--- Step 2: LOD2 Geometry Processing ---")
    building_data = process_lod2(output_geojson_path)
    print(f"Processed {len(building_data)} buildings")

    # Step 3: Geocoding to determine building addresses
    print("\n--- Step 3: Geocoding Building Addresses ---")
    building_data = calculate_centroid_and_geocode(building_data)

    # Step 4: Interactive heat demand calculation
    print("\n--- Step 4: Heat Demand Calculation ---")
    print("Please provide building type and state information for each building:")
    print("\nBuilding Types (TABULA):")
    print("  EFH - Single Family House")
    print("  RH  - Row House") 
    print("  MFH - Multi-Family House")
    print("  AB  - Apartment Building")
    print("\nBuilding States:")
    print("  existing - Original construction")
    print("  usual_refurbishment - Standard renovation")
    print("  advanced_refurbishment - Deep renovation")
    print("  new_building - New construction")

    results = []
    processed_count = 0
    skipped_count = 0

    # Process each building with user interaction
    for building_id, info in building_data.items():
        ground_area = info.get('Ground_Area')
        wall_area = info.get('Wall_Area')
        roof_area = info.get('Roof_Area')
        building_volume = info.get('Volume')
        address = info.get('Adresse', 'Address unknown')
        
        # Validate geometry data completeness
        if all(area is not None for area in [ground_area, wall_area, roof_area, building_volume]):
            print(f"\n--- Building {building_id} ---")
            print(f"Address: {address}")
            print(f"Geometry: {ground_area:.1f}m² ground, {wall_area:.1f}m² walls, {roof_area:.1f}m² roof, {building_volume:.1f}m³ volume")
            
            # Interactive user input for building classification
            print('Building type (EFH/RH/MFH/AB): ', end='')
            u_type = input().strip()
            print('Building state (existing/usual_refurbishment/advanced_refurbishment/new_building): ', end='')
            building_state = input().strip()

            try:
                # Create building object and calculate heat demand
                building = Building(
                    ground_area, wall_area, roof_area, building_volume, 
                    u_type=u_type, building_state=building_state
                )
                
                building.calc_yearly_heat_demand()
                
                # Store results
                result = {
                    'Building_ID': building_id,
                    'Address': address,
                    'Ground_Area_m2': ground_area,
                    'Wall_Area_m2': wall_area,
                    'Roof_Area_m2': roof_area,
                    'Volume_m3': building_volume,
                    'Building_Type': u_type,
                    'Building_State': building_state,
                    'Yearly_Heat_Demand_kWh': building.yearly_heat_demand,
                    'Heating_Demand_kWh': building.yearly_heating_demand,
                    'DHW_Demand_kWh': building.yearly_warm_water_demand,
                    'DHW_Share': building.warm_water_share,
                    'Specific_Demand_kWh_m2': building.yearly_heat_demand / ground_area
                }
                results.append(result)
                processed_count += 1
                
                print(f"✓ Heat demand calculated: {building.yearly_heat_demand:.0f} kWh/a")
                print(f"  Specific demand: {result['Specific_Demand_kWh_m2']:.1f} kWh/m²a")
                
            except Exception as e:
                print(f"✗ Error calculating heat demand: {e}")
                skipped_count += 1
        else:
            print(f"\n⚠ Building {building_id}: Incomplete geometry data - skipping")
            print(f"  Address: {address}")
            print(f"  Missing: {[k for k, v in zip(['Ground', 'Wall', 'Roof', 'Volume'], [ground_area, wall_area, roof_area, building_volume]) if v is None]}")
            skipped_count += 1

    # Save results to CSV
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv(output_csv_path, index=False, sep=';')
        
        # Summary statistics
        total_demand = results_df['Yearly_Heat_Demand_kWh'].sum()
        avg_specific_demand = results_df['Specific_Demand_kWh_m2'].mean()
        avg_dhw_share = results_df['DHW_Share'].mean()
        
        print(f"\n=== Heat Demand Calculation Complete ===")
        print(f"Results saved to: {output_csv_path}")
        print(f"Processed buildings: {processed_count}")
        print(f"Skipped buildings: {skipped_count}")
        print(f"Total heat demand: {total_demand:,.0f} kWh/a")
        print(f"Average specific demand: {avg_specific_demand:.1f} kWh/m²a")
        print(f"Average DHW share: {avg_dhw_share:.1%}")
    else:
        print("\n⚠ No buildings successfully processed. Check input data quality.")