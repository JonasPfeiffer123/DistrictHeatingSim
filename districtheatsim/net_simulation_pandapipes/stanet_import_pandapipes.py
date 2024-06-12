import pandas as pd
import pandapipes as pp
import numpy as np
from pyproj import Transformer

from heat_requirement import heat_requirement_BDEW

# Read the CSV file with the specified delimiter and ignore bad lines
# Since we are now looking for specific entries, we read the entire file as a single column

def create_net_from_stanet_csv(file_path, supply_temperature, flow_pressure_pump, lift_pressure_pump):
    # Criteria for the different object types and their table headers
    object_types = {
        'KNO': 'REM FLDNAM KNO',
        'LEI': 'REM FLDNAM LEI',
        'WAE': 'REM FLDNAM WAE',
        'HEA': 'REM FLDNAM HEA',
        'ZAE': 'REM FLDNAM ZAE'
    }

    try:
        # Read the CSV file as one large string, each line becomes an item in a list
        with open(file_path, 'r', encoding='ISO-8859-1') as file:
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

                dataframes_dict[obj_type] = pd.DataFrame(data, columns=header)

        error_message = None
    except Exception as e:
        error_message = str(e)
        print(error_message)
        dataframes_dict = None

    # Access to the created DataFrames, e.g.:
    kno_df = dataframes_dict['KNO']
    lei_df = dataframes_dict['LEI']
    wae_df = dataframes_dict['WAE']
    hea_df = dataframes_dict['HEA']
    zae_df = dataframes_dict['ZAE']

    # Selected columns for nodes
    selected_columns_kno = ["XRECHTS", "YHOCH", "KNAM"]
    selected_columns_lei = ["ANFNAM", "ENDNAM", "WDZAHL", "RORL", "DM", "WANDDICKE", "OUTERDM", "RAU", "ZETA", "ROHRTYP", "DN"]
    selected_columns_wae = ["ANFNAM", "ENDNAM", "WDZAHL", "RORL", "DM", "RAU"]
    selected_columns_hea = ["ANFNAM", "ENDNAM"]
    selected_columns_zae = ["KNAM", "VERBRAUCH", "PROFIL"]

    # Filter the DataFrame to the selected columns
    filtered_kno_df = kno_df[selected_columns_kno]
    filtered_lei_df = lei_df[selected_columns_lei]

    # Assign coordinates of the start and end nodes to the lines
    filtered_lei_df = filtered_lei_df.merge(filtered_kno_df[['KNAM', 'XRECHTS', 'YHOCH']], left_on='ANFNAM', right_on='KNAM', how='left')
    filtered_lei_df.rename(columns={'XRECHTS': 'ANF_X', 'YHOCH': 'ANF_Y'}, inplace=True)
    filtered_lei_df = filtered_lei_df.merge(filtered_kno_df[['KNAM', 'XRECHTS', 'YHOCH']], left_on='ENDNAM', right_on='KNAM', how='left')
    filtered_lei_df.rename(columns={'XRECHTS': 'END_X', 'YHOCH': 'END_Y'}, inplace=True)

    # Removing the now unnecessary columns 'KNAM'
    filtered_lei_df.drop(columns=['KNAM_x', 'KNAM_y'], inplace=True)

    # Transform the coordinates
    filtered_wae_df = wae_df[selected_columns_wae]
    # Assign coordinates of the start and end nodes to the heat exchangers

    filtered_wae_df = filtered_wae_df.merge(filtered_kno_df[['KNAM', 'XRECHTS', 'YHOCH']], left_on='ANFNAM', right_on='KNAM', how='left')
    filtered_wae_df.rename(columns={'XRECHTS': 'ANF_X', 'YHOCH': 'ANF_Y'}, inplace=True)
    filtered_wae_df = filtered_wae_df.merge(filtered_kno_df[['KNAM', 'XRECHTS', 'YHOCH']], left_on='ENDNAM', right_on='KNAM', how='left')
    filtered_wae_df.rename(columns={'XRECHTS': 'END_X', 'YHOCH': 'END_Y'}, inplace=True)

    # Removing the now unnecessary columns 'KNAM'
    filtered_wae_df.drop(columns=['KNAM_x', 'KNAM_y'], inplace=True)

    filtered_hea_df = hea_df[selected_columns_hea]
    filtered_zae_df = zae_df[selected_columns_zae]
    filtered_zae_df['PROFIL'] = filtered_zae_df['PROFIL'].str.replace('*', '')

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


    # Merge the DataFrames
    merged_wae_zae_df = pd.merge(filtered_wae_df, filtered_zae_df, left_on='ANFNAM', right_on='KNAM')

    # Creating a new pandapipes network
    net = pp.create_empty_network(fluid="water")

    for idx, row in filtered_kno_df.iterrows():
        # Extract the coordinates and node name
        x_coord = float(row['XRECHTS'])
        y_coord = float(row['YHOCH'])
        kno_name = row['KNAM']

        pp.create_junction(net, pn_bar=1.0, tfluid_k=293.15, name=kno_name, geodata=(x_coord, y_coord))

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

        # Using the new coordinates for the start and end points of the line
        from_coords = (float(row["ANF_X"]), float(row["ANF_Y"]))
        to_coords = (float(row["END_X"]), float(row["END_Y"]))
        line_coords = [from_coords, to_coords]

        # Creating the pipe in pandapipes
        pp.create_pipe(net, from_junction=from_junction, to_junction=to_junction, std_type=std_type, length_km=length_km, 
                    k_mm=k_mm, alpha_w_per_m2k=alpha_w_per_m2k, sections=5, text_k=281, name="Pipe_" + str(idx), fluid="water",
                    geodata=line_coords)


    for idx, row in filtered_hea_df.iterrows():
        # Finden der Indizes der Anfangs- und End-Junctions basierend auf den Namen
        from_junction = get_junction_index(net, row["ANFNAM"])
        to_junction = get_junction_index(net, row["ENDNAM"])

        # Finding the indices of the starting and ending junctions based on the names
        pp.create_circ_pump_const_pressure(net, return_junction=from_junction, flow_junction=to_junction,
                                        p_flow_bar=flow_pressure_pump, plift_bar=lift_pressure_pump,
                                        t_flow_k=273.15+supply_temperature, type="auto", name="Pump_" + str(idx))
        
    total_heat_W = []
    max_heat_requirement_W = []

    for idx, row in merged_wae_zae_df.iterrows():
        from_junction = get_junction_index(net, row["ANFNAM"])
        to_junction = get_junction_index(net, row["ENDNAM"])
        # Calculate the mean coordinates
        mid_coord = ((float(row["ANF_X"]) + float(row["END_X"])) / 2, (float(row["ANF_Y"]) + float(row["END_Y"])) / 2)

        # Extract other required parameters from the DataFrame
        diameter_m = float(row["DM"]) / 1000  # Diameter of the heat exchanger in meters

        heat_usage_kWh = float(row["VERBRAUCH"])
        current_building_type = row["PROFIL"]

        yearly_time_steps, total_heat_kW, hourly_temperatures  = heat_requirement_BDEW.calculate(heat_usage_kWh, current_building_type, subtyp="03")

        total_heat_W.append(total_heat_kW * 1000)
        max_heat_requirement_W.append(np.max(total_heat_kW * 1000))

        # Create a middle junction
        mid_junction_idx = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name=f"Mid_Junction_{idx}", geodata=mid_coord)

        # Create a flow control between the initial node of the heat exchanger and the middle junction
        pp.create_flow_control(net, from_junction=from_junction, to_junction=mid_junction_idx, controlled_mdot_kg_per_s=0.25, diameter_m=diameter_m)

        # Create a heat exchanger between the middle junction and the end node of the heat exchanger
        pp.create_heat_exchanger(net, from_junction=mid_junction_idx, to_junction=to_junction, diameter_m=diameter_m, loss_coefficient=0,
                                qext_w=np.max(total_heat_kW * 1000), name=f"HeatExchanger_{idx}")  # qext_w needs to be adjusted accordingly
    
    total_heat_W = np.array(total_heat_W)
    max_heat_requirement_W = np.array(max_heat_requirement_W)
        
    pp.pipeflow(net, mode="all")

    return net, yearly_time_steps, total_heat_W, max_heat_requirement_W