"""
Filename: stanet_import_pandapipes.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2026-04-30
Description: Script to import a STANET district heating net to a pandapipes net.

Additional Information: Currently outdated
"""

import pandas as pd
import pandapipes as pp
import pandapipes.plotting as pp_plot
import numpy as np
import traceback
import matplotlib.pyplot as plt

from pyslpheat import bdew_calculate
from districtheatingsim.net_simulation_pandapipes.config_plot import config_plot

def _detect_crs(dataframes_dict):
    """Extract CRS and ZONEPREFIX from the STANET NET block.

    COORDSYS4 holds the CRS (e.g. 'EPSG:25833' or 'EPSG:3146*' where '*' is a
    wildcard for the DHDN GK zone digit). ZONEPREFIX='N' means the zone prefix
    digit is NOT stored in the X coordinate (stripped easting).

    For wildcard GK codes, each candidate zone is validated by transforming a
    sample coordinate to WGS84 and checking that it falls within the expected
    geographic area (Central Europe).

    Returns (crs_epsg, zoneprefix, utmzone) where utmzone is the integer UTM/GK zone
    number (0 if not set).
    """
    from pyproj import CRS as ProjCRS, Transformer as ProjTransformer

    net_df = dataframes_dict.get('NET')
    if net_df is None or net_df.empty:
        return None, 'J', 0

    row = net_df.iloc[0].str.strip() if net_df.dtypes.eq(object).all() else net_df.iloc[0]

    coordsys4 = str(row.get('COORDSYS4', '') or '').strip()
    utmzone_raw = str(row.get('UTMZONE', '0') or '0').strip()
    zoneprefix = str(row.get('ZONEPREFIX', 'J') or 'J').strip().upper()

    try:
        utmzone = int(float(utmzone_raw))
    except ValueError:
        utmzone = 0

    if not coordsys4:
        return None, zoneprefix

    # Exact code — validate and return immediately
    if not coordsys4.endswith('*'):
        try:
            ProjCRS.from_user_input(coordsys4)
        except Exception:
            pass
        return coordsys4, zoneprefix, utmzone

    base = coordsys4[:-1]  # e.g. 'EPSG:3146'

    # Build candidate list: explicit UTMZONE first, then DHDN range (31466–31469), then others
    if utmzone > 0:
        digit_order = [utmzone]
    elif base.upper() == 'EPSG:3146':
        digit_order = [6, 7, 8, 9, 1, 2, 3, 4, 5]
    else:
        digit_order = list(range(1, 10))

    # Try to get a sample coordinate from KNO for geographic validation
    sample_x = sample_y = None
    kno_df = dataframes_dict.get('KNO')
    if kno_df is not None and not kno_df.empty and 'XRECHTS' in kno_df.columns:
        try:
            sample_x = pd.to_numeric(kno_df['XRECHTS'].str.strip(), errors='coerce').median()
            sample_y = pd.to_numeric(kno_df['YHOCH'].str.strip(), errors='coerce').median()
        except Exception:
            pass

    # Central-Europe bounding box for validation (lon, lat): covers D/A/CH/PL/CZ
    bbox = (5.0, 46.0, 19.0, 57.0)

    for digit in digit_order:
        code = base + str(digit)
        try:
            crs = ProjCRS.from_user_input(code)
        except Exception:
            continue

        if sample_x is None or sample_y is None:
            return code, zoneprefix, utmzone  # no coordinates to validate — take first valid

        # Restore zone prefix for stripped coordinates before validation
        test_x = sample_x
        if zoneprefix == 'N':
            try:
                false_easting = float(crs.to_dict().get('x_0', 0))
                zone_pref = int(false_easting) // 1_000_000
                if zone_pref > 0:
                    test_x = sample_x + zone_pref * 1_000_000
            except Exception:
                pass

        try:
            t = ProjTransformer.from_crs(code, 'EPSG:4326', always_xy=True)
            lon, lat = t.transform(float(test_x), float(sample_y))
            if bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]:
                return code, zoneprefix, utmzone
        except Exception:
            continue

    return coordsys4, zoneprefix  # fallback: return raw value



# Read the exported STANET-CSV file with the specified delimiter and ignore bad lines
# Since we are now looking for specific entries, we read the entire file as a single column

def create_net_from_stanet_csv(stanet_csv_file_path, TRY_file_path, supply_temperature, flow_pressure_pump, lift_pressure_pump):
    # Criteria for the different object types and their table headers
    object_types = {
        'KNO': 'REM FLDNAM KNO',
        'LEI': 'REM FLDNAM LEI',
        'KNI': 'REM FLDNAM KNI',
        'NET': 'REM FLDNAM NET',
        'WAE': 'REM FLDNAM WAE',
        'HEA': 'REM FLDNAM HEA',
        'ZAE': 'REM FLDNAM ZAE'
    }

    try:
        # Read the CSV file as one large string, each line becomes an item in a list
        with open(stanet_csv_file_path, 'r', encoding='ISO-8859-1') as file:
            lines = file.readlines()

        # Dictionaries for the saved lines
        lines_dict = {key: [] for key in object_types}

        # Loop through the rows and collect the data for each object type
        for line in lines:
            for obj_type, header in object_types.items():
                if line.startswith(obj_type) or line.startswith(header):
                    lines_dict[obj_type].append(line.strip())

        # Create DataFrames for each object type taking column inconsistencies into account
        dataframes_dict = {}
        for obj_type in object_types:
            if lines_dict[obj_type]:
                # Extract the table header and data rows
                header_line = lines_dict[obj_type][0]
                data_lines = lines_dict[obj_type][1:]

                # Convert to DataFrame
                header = header_line.split(';')
                data = [line.split(';') for line in data_lines]

                # Check the number of columns and adjust if necessary
                max_cols = len(header)
                data = [row[:max_cols] for row in data]  # Limit to the number of columns in the header

                df = pd.DataFrame(data, columns=header)
                df.columns = df.columns.str.strip()
                dataframes_dict[obj_type] = df

        error_message = None

        # --- Detect coordinate reference system from NET block ---
        crs_epsg, _, _ = _detect_crs(dataframes_dict)
        print(f"Detected CRS: {crs_epsg}")

        # Prerequisite: STANET must be configured with
        #   Koordinatensystem Onlinekartographie 10.0 = "EPSG:258*; ETRS89 / UTM"
        #   Meridianstreifen/UTM Zone = 32  (western Germany)  or  33  (eastern Germany)
        # _detect_crs resolves the wildcard using UTMZONE and returns e.g. EPSG:25833.
        display_crs = crs_epsg or "EPSG:25833"

        # Access to the created DataFrames, e.g.:
        kno_df = dataframes_dict['KNO']
        lei_df = dataframes_dict['LEI']
        wae_df = dataframes_dict.get('WAE', pd.DataFrame())
        hea_df = dataframes_dict.get('HEA', pd.DataFrame())
        zae_df = dataframes_dict.get('ZAE', pd.DataFrame())

        # Parse KNI (bend-point) data if present
        kni_df = dataframes_dict.get('KNI')
        if kni_df is not None and not kni_df.empty:
            kni_df = kni_df.apply(lambda col: col.str.strip() if col.dtype == object else col)
            kni_df['SNUM'] = pd.to_numeric(kni_df['SNUM'], errors='coerce').astype('Int64')
            kni_df['KNICKNO'] = pd.to_numeric(kni_df['KNICKNO'], errors='coerce').astype('Int64')
            kni_df['XRECHTS'] = pd.to_numeric(kni_df['XRECHTS'], errors='coerce')
            kni_df['YHOCH'] = pd.to_numeric(kni_df['YHOCH'], errors='coerce')
        else:
            kni_df = None

        # Selected columns for nodes
        selected_columns_kno = ["XRECHTS", "YHOCH", "KNAM", "GEOH"]
        selected_columns_lei = ["ANFNAM", "ENDNAM", "WDZAHL", "RORL", "DM", "WANDDICKE", "OUTERDM", "RAU", "ZETA", "ROHRTYP", "DN"]
        selected_columns_wae = ["ANFNAM", "ENDNAM", "WDZAHL", "RORL", "DM", "RAU"]
        selected_columns_hea = ["ANFNAM", "ENDNAM"]
        selected_columns_zae = ["KNAM", "VERBRAUCH", "PROFIL"]

        # Filter the DataFrame to the selected columns
        filtered_kno_df = kno_df[selected_columns_kno].copy()
        filtered_lei_df = lei_df[selected_columns_lei]

        # Convert node coordinates and elevation to float
        filtered_kno_df['XRECHTS'] = pd.to_numeric(filtered_kno_df['XRECHTS'].str.strip(), errors='coerce')
        filtered_kno_df['YHOCH']   = pd.to_numeric(filtered_kno_df['YHOCH'].str.strip(),   errors='coerce')
        filtered_kno_df['GEOH']    = pd.to_numeric(filtered_kno_df['GEOH'].str.strip(),    errors='coerce').fillna(0.0)

        # Assign coordinates of the start and end nodes to the lines
        filtered_lei_df = filtered_lei_df.merge(filtered_kno_df[['KNAM', 'XRECHTS', 'YHOCH']], left_on='ANFNAM', right_on='KNAM', how='left')
        filtered_lei_df.rename(columns={'XRECHTS': 'ANF_X', 'YHOCH': 'ANF_Y'}, inplace=True)
        filtered_lei_df = filtered_lei_df.merge(filtered_kno_df[['KNAM', 'XRECHTS', 'YHOCH']], left_on='ENDNAM', right_on='KNAM', how='left')
        filtered_lei_df.rename(columns={'XRECHTS': 'END_X', 'YHOCH': 'END_Y'}, inplace=True)

        # Removing the now unnecessary columns 'KNAM'
        filtered_lei_df.drop(columns=['KNAM_x', 'KNAM_y'], inplace=True)

        # SNUM matches KNI.SNUM — use !RECNO from LEI when present (authoritative);
        # fall back to 1-based sequential index if the column is absent.
        filtered_lei_df = filtered_lei_df.reset_index(drop=True)
        if '!RECNO' in lei_df.columns:
            filtered_lei_df['SNUM'] = pd.to_numeric(
                lei_df['!RECNO'].str.strip(), errors='coerce'
            ).reset_index(drop=True).astype('Int64')
        else:
            filtered_lei_df['SNUM'] = filtered_lei_df.index + 1

        # Transform the coordinates
        if not wae_df.empty:
            filtered_wae_df = wae_df[selected_columns_wae]
            filtered_wae_df = filtered_wae_df.merge(filtered_kno_df[['KNAM', 'XRECHTS', 'YHOCH']], left_on='ANFNAM', right_on='KNAM', how='left')
            filtered_wae_df.rename(columns={'XRECHTS': 'ANF_X', 'YHOCH': 'ANF_Y'}, inplace=True)
            filtered_wae_df = filtered_wae_df.merge(filtered_kno_df[['KNAM', 'XRECHTS', 'YHOCH']], left_on='ENDNAM', right_on='KNAM', how='left')
            filtered_wae_df.rename(columns={'XRECHTS': 'END_X', 'YHOCH': 'END_Y'}, inplace=True)
            filtered_wae_df.drop(columns=['KNAM_x', 'KNAM_y'], inplace=True)
        else:
            filtered_wae_df = pd.DataFrame()

        filtered_hea_df = hea_df[selected_columns_hea] if not hea_df.empty else pd.DataFrame()

        if not zae_df.empty:
            filtered_zae_df = zae_df[selected_columns_zae]
            filtered_zae_df['PROFIL'] = filtered_zae_df['PROFIL'].str.replace('*', '')
        else:
            filtered_zae_df = pd.DataFrame()

        """
        # Create the transformer for the coordinate transformation from EPSG:31467 to EPSG:25833
        transformer = Transformer.from_crs("EPSG:31465", "EPSG:25833")

        # Funktion zur Transformation der Koordinaten
        def transform_coords(x, y):
            return transformer.transform(x, y)

        # Transformation of the coordinates in the DataFrames
        filtered_kno_df[['XRECHTS', 'YHOCH']] = filtered_kno_df.apply(lambda row: transform_coords(row['XRECHTS'], row['YHOCH']), axis=1, result_type="expand")
        filtered_lei_df[['ANF_X', 'ANF_Y']] = filtered_lei_df.apply(lambda row: transform_coords(row['ANF_X'], row['ANF_Y']), axis=1, result_type="expand")
        filtered_lei_df[['END_X', 'END_Y']] = filtered_lei_df.apply(lambda row: transform_coords(row['END_X'], row['END_Y']), axis=1, result_type="expand")
        filtered_wae_df[['ANF_X', 'ANF_Y']] = filtered_wae_df.apply(lambda row: transform_coords(row['ANF_X'], row['ANF_Y']), axis=1, result_type="expand")
        filtered_wae_df[['END_X', 'END_Y']] = filtered_wae_df.apply(lambda row: transform_coords(row['END_X'], row['END_Y']), axis=1, result_type="expand")
        """

        # Merge WAE and ZAE — only possible when both blocks are present
        if not filtered_wae_df.empty and not filtered_zae_df.empty:
            merged_wae_zae_df = pd.merge(filtered_wae_df, filtered_zae_df, left_on='ANFNAM', right_on='KNAM')
        else:
            merged_wae_zae_df = pd.DataFrame()

        # Creating a new pandapipes network
        net = pp.create_empty_network(fluid="water")

        for idx, row in filtered_kno_df.iterrows():
            x_coord  = float(row['XRECHTS'])
            y_coord  = float(row['YHOCH'])
            kno_name = row['KNAM']
            pp.create_junction(net, pn_bar=1.0, tfluid_k=293.15, name=kno_name, geodata=(x_coord, y_coord))

        # Store elevation (GEOH, mNN) as 'z' column in junction_geodata for 3-D plotting
        name_to_geoh = filtered_kno_df.set_index('KNAM')['GEOH']
        net.junction_geodata['z'] = (
            net.junction['name'].map(name_to_geoh).fillna(0.0).values
        )

        # Function to find the index of a junction by its name
        def get_junction_index(net, junction_name):
            return net['junction'][net['junction']['name'] == junction_name].index[0]

        for idx, row in filtered_lei_df.iterrows():
            # Find the indices of the beginning and ending junctions based on the names
            from_junction = get_junction_index(net, row["ANFNAM"])
            to_junction = get_junction_index(net, row["ENDNAM"])

            std_type = row["ROHRTYP"]
            length_km = float(row["RORL"])/1000  # Length of the line in km
            k_mm = float(row["RAU"])
            alpha_w_per_m2k = float(row["WDZAHL"])

            # Build geodata: start node → KNI bend points (ordered) → end node
            from_coords = (float(row["ANF_X"]), float(row["ANF_Y"]))
            to_coords = (float(row["END_X"]), float(row["END_Y"]))
            if kni_df is not None:
                snum = int(row["SNUM"])
                kni_rows = kni_df[kni_df['SNUM'] == snum].sort_values('KNICKNO')
                kni_coords = [(float(r['XRECHTS']), float(r['YHOCH'])) for _, r in kni_rows.iterrows()]
            else:
                kni_coords = []
            line_coords = [from_coords] + kni_coords + [to_coords]

            # Creating the pipe in pandapipes; fall back to explicit parameters when std_type is unknown
            pipe_kwargs = dict(from_junction=from_junction, to_junction=to_junction,
                               length_km=length_km, k_mm=k_mm, alpha_w_per_m2k=alpha_w_per_m2k,
                               sections=5, text_k=281, name="Pipe_" + str(idx), fluid="water",
                               geodata=line_coords)
            try:
                pp.create_pipe(net, std_type=std_type, **pipe_kwargs)
            except UserWarning:
                diameter_m = float(row["DM"]) / 1000
                pp.create_pipe_from_parameters(net, diameter_m=diameter_m, **pipe_kwargs)


        for idx, row in filtered_hea_df.iterrows():
            # Finden der Indizes der Anfangs- und End-Junctions basierend auf den Namen
            from_junction = get_junction_index(net, row["ANFNAM"])
            to_junction = get_junction_index(net, row["ENDNAM"])

            # Finding the indices of the starting and ending junctions based on the names
            pp.create_circ_pump_const_pressure(net, return_junction=from_junction, flow_junction=to_junction,
                                            p_flow_bar=flow_pressure_pump, plift_bar=lift_pressure_pump,
                                            t_flow_k=273.15+supply_temperature, type="auto", name="Pump_" + str(idx))
            
        yearly_time_steps = None
        total_heat_W = []
        max_heat_requirement_W = []

        for idx, row in merged_wae_zae_df.iterrows():
            from_junction = get_junction_index(net, row["ANFNAM"])
            to_junction = get_junction_index(net, row["ENDNAM"])

            heat_usage_kWh = float(row["VERBRAUCH"])
            current_building_type = row["PROFIL"]

            df_bdew = bdew_calculate(
                annual_heat_kWh=heat_usage_kWh,
                profile_type=current_building_type,
                subtype="03",
                TRY_file_path=TRY_file_path,
                year=2021,
                dhw_share=None,
            )
            yearly_time_steps = df_bdew.index.values
            total_heat_kW = df_bdew["Q_total_kWh"].values
            heating_demand_kW = df_bdew["Q_heat_kWh"].values
            warm_water_demand_kW = df_bdew["Q_dhw_kWh"].values
            ourly_temperatures = df_bdew["temperature_C"].values

            total_heat_W.append(total_heat_kW * 1000)
            max_heat_requirement_W.append(np.max(total_heat_kW * 1000))

            # Create a heat consumer directly between the start and end junctions
            pp.create_heat_consumer(
                net,
                from_junction=from_junction,
                to_junction=to_junction,
                loss_coefficient=0.0,
                qext_w=np.max(total_heat_kW * 1000),
                treturn_k=273.15 + 20,
                name=f"HeatConsumer_{idx}"
            )
        
        total_heat_W = np.array(total_heat_W)
        max_heat_requirement_W = np.array(max_heat_requirement_W)

        pp_plot.simple_plot(net, show_junctions=True, show_pipes=True, show_heat_consumers=True, show_pump=True)
            
        # Simulate pipe flow
        pp.pipeflow(net, mode="bidirectional", iter=100)

        print("Simulation completed successfully.")

        # Use matplotlib axes for plotting
        fig, ax = plt.subplots()
        config_plot(net, show_junctions=True, show_pipes=True, show_heat_consumers=True, show_pump=True, ax=ax,
                    crs=display_crs)
        plt.show()



    except Exception as e:
        error_message = str(e)
        print("Exception occurred:", error_message)
        print(traceback.format_exc())
        dataframes_dict = None
        return None, None, None, None, None

    return net, yearly_time_steps, total_heat_W, max_heat_requirement_W, crs_epsg