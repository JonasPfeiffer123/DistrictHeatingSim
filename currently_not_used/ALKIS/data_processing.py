import os
import zipfile

import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np

def preprocessing(directory="C:/Users/username/heating_network_generation/project_data/Bad Muskau/Gebäudedaten/alkis_data"):
    # Define the directory where the zip files are located and where to extract them
    zip_directory = directory  # Directory containing the zip files
    extraction_directory = directory  # Directory to extract the files to

    # Create the extraction directory if it doesn't exist
    if not os.path.exists(extraction_directory):
        os.makedirs(extraction_directory)

    # Iterate over all files in the zip directory
    for filename in os.listdir(zip_directory):
        if filename.endswith('.zip'):
            file_path = os.path.join(zip_directory, filename)
            # Open the zip file
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                # Extract all the contents of the zip file into the extraction directory
                zip_ref.extractall(extraction_directory)
            # Delete the zip file after extraction
            os.remove(file_path)

# Define the path to your XML file
file_path = 'C:/Users/username/heating_network_generation/project_data/Bad Muskau/Gebäudedaten/alkis_data/148298.xml'  # Update for your local path

# XML-Namespace
ns = {
    'gml': 'http://www.opengis.net/gml/3.2',
    'adv': 'http://www.adv-online.de/namespaces/adv/gid/6.0'
}

def extract_building_data(file_path):
    # XML-Datei laden und parsen
    tree = ET.parse(file_path)
    root = tree.getroot()

    buildings_data = []

    # Finde alle Gebäudeelemente in der XML-Datei
    for bldg in root.findall('.//adv:AX_Gebaeude', ns):
        usage_type = bldg.find('.//adv:gebaeudefunktion', ns).text
        pos_list_elements = bldg.findall('.//gml:posList', ns)
        for pos_list_element in pos_list_elements:
            # Koordinatenstring in ein numpy array umwandeln
            coords = np.array([float(x) for x in pos_list_element.text.split()]).reshape((-1, 2))
            buildings_data.append((usage_type, coords))

    return buildings_data

def plot_buildings(buildings_data):
    fig, ax = plt.subplots()
    # Define different colors for each usage type
    colors = iter(plt.cm.tab20(np.linspace(0, 1, len(set([b[0] for b in buildings_data])))))
    color_map = {}
    
    for usage_type, coords in buildings_data:
        if usage_type not in color_map:
            color_map[usage_type] = next(colors)
        
        polygon = Polygon(coords, closed=True, facecolor=color_map[usage_type], edgecolor='black', alpha=0.5)
        ax.add_patch(polygon)

    # Create a legend
    legend_elements = [plt.Line2D([0], [0], color=color_map[ut], lw=4, label=f'Usage Type: {ut}') for ut in color_map]
    ax.legend(handles=legend_elements, loc='upper left')

    # Set the axes aspect
    ax.set_aspect('equal')
    ax.autoscale_view()

    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.title('Building Usage Types')

    plt.show()

# Hauptfunktion
def main():
    buildings_data = extract_building_data(file_path)
    plot_buildings(buildings_data)

if __name__ == "__main__":
    main()


# 1000: Wohngebäude
# 2000: Gebäude für Wirtschaft oder Gewerbe
# 3000: Gebäude für öffentliche Zwecke
# sonstige und 9998, wenn die Funktion nicht spezifiziert werden kann.