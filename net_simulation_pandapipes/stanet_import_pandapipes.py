import pandas as pd
import pandapipes as pp
import numpy as np
from pyproj import Transformer

import sys
sys.path.append('C:/Users/username/heating_network_generation')

from heat_requirement import heat_requirement_BDEW
from net_simulation_pandapipes.net_simulation_calculation import create_controllers, correct_flow_directions, export_net_geojson, optimize_diameter_parameters
from net_simulation_pandapipes.net_simulation import init_timeseries_opt, thermohydraulic_time_series_net_calculation

# Einlesen der CSV-Datei mit dem angegebenen Trennzeichen und Ignorieren von fehlerhaften Zeilen
# Da wir nun spezifische Einträge suchen, lesen wir die ganze Datei als eine einzige Spalte ein

def create_net_from_stanet_csv(file_path):
    #file_path = "C:/Users/username/heating_network_generation/net_simulation_pandapipes/stanet files/Beleg_1.CSV"

    # Kriterien für die verschiedenen Objekttypen und ihre Tabellenköpfe
    object_types = {
        'KNO': 'REM FLDNAM KNO',
        'LEI': 'REM FLDNAM LEI',
        'WAE': 'REM FLDNAM WAE',
        'HEA': 'REM FLDNAM HEA',
        'ZAE': 'REM FLDNAM ZAE'
    }

    try:
        # Einlesen der CSV-Datei als eine große Zeichenkette, jede Zeile wird zu einem Element in einer Liste
        with open(file_path, 'r', encoding='ISO-8859-1') as file:
            lines = file.readlines()

        # Dictionaries für die gespeicherten Zeilen
        lines_dict = {key: [] for key in object_types}

        # Durchlaufen der Zeilen und Sammeln der Daten für jeden Objekttyp
        for line in lines:
            for obj_type, header in object_types.items():
                if line.startswith(obj_type) or line.startswith(header):
                    lines_dict[obj_type].append(line.strip())

        # Erstellen von DataFrames für jeden Objekttyp unter Berücksichtigung von Spalteninkonsistenzen
        dataframes_dict = {}
        for obj_type in object_types:
            if lines_dict[obj_type]:
                # Extrahieren des Tabellenkopfes und der Datenzeilen
                header_line = lines_dict[obj_type][0]
                data_lines = lines_dict[obj_type][1:]

                # Umwandeln in DataFrame
                header = header_line.split(';')
                data = [line.split(';') for line in data_lines]

                # Überprüfen der Spaltenanzahl und Anpassen falls notwendig
                max_cols = len(header)
                data = [row[:max_cols] for row in data]  # Beschränken auf die Anzahl der Spalten im Header

                dataframes_dict[obj_type] = pd.DataFrame(data, columns=header)

        error_message = None
    except Exception as e:
        error_message = str(e)
        print(error_message)
        dataframes_dict = None

    # Zugriff auf die erstellten DataFrames, z.B.:
    kno_df = dataframes_dict['KNO']
    lei_df = dataframes_dict['LEI']
    wae_df = dataframes_dict['WAE']
    hea_df = dataframes_dict['HEA']
    zae_df = dataframes_dict['ZAE']

    # Ausgewählte Spalten für Knoten
    selected_columns_kno = ["XRECHTS", "YHOCH", "KNAM"]
    selected_columns_lei = ["ANFNAM", "ENDNAM", "WDZAHL", "RORL", "DM", "WANDDICKE", "OUTERDM", "RAU", "ZETA", "ROHRTYP", "DN"]
    selected_columns_wae = ["ANFNAM", "ENDNAM", "WDZAHL", "RORL", "DM", "RAU"]
    selected_columns_hea = ["ANFNAM", "ENDNAM"]
    selected_columns_zae = ["KNAM", "VERBRAUCH", "PROFIL"]

    # Filtern des DataFrames auf die ausgewählten Spalten
    filtered_kno_df = kno_df[selected_columns_kno]
    filtered_lei_df = lei_df[selected_columns_lei]

    # Koordinaten der Anfangs- und Endknoten den Leitungen zuweisen
    filtered_lei_df = filtered_lei_df.merge(filtered_kno_df[['KNAM', 'XRECHTS', 'YHOCH']], left_on='ANFNAM', right_on='KNAM', how='left')
    filtered_lei_df.rename(columns={'XRECHTS': 'ANF_X', 'YHOCH': 'ANF_Y'}, inplace=True)
    filtered_lei_df = filtered_lei_df.merge(filtered_kno_df[['KNAM', 'XRECHTS', 'YHOCH']], left_on='ENDNAM', right_on='KNAM', how='left')
    filtered_lei_df.rename(columns={'XRECHTS': 'END_X', 'YHOCH': 'END_Y'}, inplace=True)

    # Entfernen der jetzt unnötigen Spalten 'KNAM'
    filtered_lei_df.drop(columns=['KNAM_x', 'KNAM_y'], inplace=True)

    # Transformieren der Koordinaten
    filtered_wae_df = wae_df[selected_columns_wae]
    # Koordinaten der Anfangs- und Endknoten den Wärmeübertragern zuweisen
    filtered_wae_df = filtered_wae_df.merge(filtered_kno_df[['KNAM', 'XRECHTS', 'YHOCH']], left_on='ANFNAM', right_on='KNAM', how='left')
    filtered_wae_df.rename(columns={'XRECHTS': 'ANF_X', 'YHOCH': 'ANF_Y'}, inplace=True)
    filtered_wae_df = filtered_wae_df.merge(filtered_kno_df[['KNAM', 'XRECHTS', 'YHOCH']], left_on='ENDNAM', right_on='KNAM', how='left')
    filtered_wae_df.rename(columns={'XRECHTS': 'END_X', 'YHOCH': 'END_Y'}, inplace=True)

    # Entfernen der jetzt unnötigen Spalten 'KNAM'
    filtered_wae_df.drop(columns=['KNAM_x', 'KNAM_y'], inplace=True)

    filtered_hea_df = hea_df[selected_columns_hea]
    filtered_zae_df = zae_df[selected_columns_zae]
    filtered_zae_df['PROFIL'] = filtered_zae_df['PROFIL'].str.replace('*', '')

    # Erstellen des Transformers für die Koordinatentransformation von EPSG:31467 zu EPSG:25833
    transformer = Transformer.from_crs("EPSG:31465", "EPSG:25833")

    # Funktion zur Transformation der Koordinaten
    def transform_coords(x, y):
        return transformer.transform(x, y)

    # Transformation der Koordinaten in den DataFrames
    filtered_kno_df[['XRECHTS', 'YHOCH']] = filtered_kno_df.apply(lambda row: transform_coords(row['XRECHTS'], row['YHOCH']), axis=1, result_type="expand")
    filtered_lei_df[['ANF_X', 'ANF_Y']] = filtered_lei_df.apply(lambda row: transform_coords(row['ANF_X'], row['ANF_Y']), axis=1, result_type="expand")
    filtered_lei_df[['END_X', 'END_Y']] = filtered_lei_df.apply(lambda row: transform_coords(row['END_X'], row['END_Y']), axis=1, result_type="expand")
    filtered_wae_df[['ANF_X', 'ANF_Y']] = filtered_wae_df.apply(lambda row: transform_coords(row['ANF_X'], row['ANF_Y']), axis=1, result_type="expand")
    filtered_wae_df[['END_X', 'END_Y']] = filtered_wae_df.apply(lambda row: transform_coords(row['END_X'], row['END_Y']), axis=1, result_type="expand")


    # Zusammenführen der DataFrames
    merged_wae_zae_df = pd.merge(filtered_wae_df, filtered_zae_df, left_on='ANFNAM', right_on='KNAM')

    # Erstellen eines neuen pandapipes-Netzes
    net = pp.create_empty_network(fluid="water")

    for idx, row in filtered_kno_df.iterrows():
        # Extrahieren der Koordinaten und des Knotennamens
        x_coord = float(row['XRECHTS'])
        y_coord = float(row['YHOCH'])
        kno_name = row['KNAM']

        # Erstellen der Junction in pandapipes
        pp.create_junction(net, pn_bar=1.0, tfluid_k=293.15, name=kno_name, geodata=(x_coord, y_coord))

    # Funktion, um den Index einer Junction anhand ihres Namens zu finden
    def get_junction_index(net, junction_name):
        return net['junction'][net['junction']['name'] == junction_name].index[0]

    for idx, row in filtered_lei_df.iterrows():
        # Finden Sie die Indizes der Anfangs- und End-Junctions basierend auf den Namen
        from_junction = get_junction_index(net, row["ANFNAM"])
        to_junction = get_junction_index(net, row["ENDNAM"])

        std_type = row["ROHRTYP"]
        length_km = float(row["RORL"])/1000  # Länge der Leitung in km
        k_mm = float(row["RAU"])
        alpha_w_per_m2k = float(row["WDZAHL"])

        # Verwenden der neuen Koordinaten für Anfangs- und Endpunkt der Leitung
        from_coords = (float(row["ANF_X"]), float(row["ANF_Y"]))
        to_coords = (float(row["END_X"]), float(row["END_Y"]))
        line_coords = [from_coords, to_coords]

        # Erstellen der Pipe in pandapipes
        pp.create_pipe(net, from_junction=from_junction, to_junction=to_junction, std_type=std_type, length_km=length_km, 
                    k_mm=k_mm, alpha_w_per_m2k=alpha_w_per_m2k, sections=5, text_k=281, name="Pipe_" + str(idx), fluid="water",
                    geodata=line_coords)  # oder entsprechendes Fluid


    for idx, row in filtered_hea_df.iterrows():
        # Finden der Indizes der Anfangs- und End-Junctions basierend auf den Namen
        from_junction = get_junction_index(net, row["ANFNAM"])
        to_junction = get_junction_index(net, row["ENDNAM"])

        # Parameter für die Pumpe
        p_flow_bar = 4  # Druckanstieg über die Pumpe in bar
        plift_bar = 1.5  # Förderhöhe der Pumpe in bar
        t_flow_k = 273.15 + 90  # Fördermediumtemperatur in Kelvin

        # Erstellen der Pumpe in pandapipes
        pp.create_circ_pump_const_pressure(net, return_junction=from_junction, flow_junction=to_junction,
                                        p_flow_bar=p_flow_bar, plift_bar=plift_bar,
                                        t_flow_k=t_flow_k, type="auto", name="Pump_" + str(idx))
        
    waerme_ges_W_L = []
    max_waerme_ges_W_L = []

    for idx, row in merged_wae_zae_df.iterrows():
        from_junction = get_junction_index(net, row["ANFNAM"])
        to_junction = get_junction_index(net, row["ENDNAM"])
        # Berechnen der mittleren Koordinaten
        mid_coord = ((float(row["ANF_X"]) + float(row["END_X"])) / 2, (float(row["ANF_Y"]) + float(row["END_Y"])) / 2)

        # Extrahieren weiterer erforderlicher Parameter aus dem DataFrame
        diameter_m = float(row["DM"]) / 1000  # Durchmesser des Wärmetauschers in Metern

        Verbrauch_kWh = float(row["VERBRAUCH"])
        current_building_type = row["PROFIL"]

        yearly_time_steps, waerme_ges_kW, hourly_temperatures  = heat_requirement_BDEW.calculate(Verbrauch_kWh, current_building_type, subtyp="03")

        waerme_ges_W_L.append(waerme_ges_kW * 1000)
        max_waerme_ges_W = np.max(waerme_ges_kW * 1000)
        max_waerme_ges_W_L.append(max_waerme_ges_W)

        # Erstellen einer mittleren Junction
        mid_junction_idx = pp.create_junction(net, pn_bar=1.05, tfluid_k=293.15, name=f"Mid_Junction_{idx}", geodata=mid_coord)

        # Erstellen eines Flow Control zwischen dem Anfangsknoten des Wärmeübertragers und der mittleren Junction
        pp.create_flow_control(net, from_junction=from_junction, to_junction=mid_junction_idx, controlled_mdot_kg_per_s=0.25, diameter_m=diameter_m)

        # Erstellen eines Heat Exchanger zwischen der mittleren Junction und dem Endknoten des Wärmeübertragers
        pp.create_heat_exchanger(net, from_junction=mid_junction_idx, to_junction=to_junction, diameter_m=diameter_m, loss_coefficient=0,
                                qext_w=max_waerme_ges_W, name=f"HeatExchanger_{idx}")  # qext_w muss entsprechend angepasst werden
    
    waerme_ges_W_L = np.array(waerme_ges_W_L)
    max_waerme_ges_W_L = np.array(max_waerme_ges_W_L)
        
    pp.pipeflow(net, mode="all")

    net = create_controllers(net, max_waerme_ges_W_L,target_temperature=60)
    net = correct_flow_directions(net)

    net = init_timeseries_opt(net, max_waerme_ges_W_L, time_steps=3, target_temperature=60)
    
    net = optimize_diameter_parameters(net, element="heat_exchanger")
    net = optimize_diameter_parameters(net, element="flow_control")
    
    export_net_geojson(net)

    return net, yearly_time_steps, waerme_ges_W_L


#net, yearly_time_steps, waerme_ges_W_L = create_net_from_stanet_csv("net_simulation_pandapipes/stanet files/Beleg_1/Beleg_1.CSV")
#calc1 = 2660
#calc2 = 2670
#thermohydraulic_time_series_net_calculation(net, yearly_time_steps, waerme_ges_W_L, calc1, calc2)