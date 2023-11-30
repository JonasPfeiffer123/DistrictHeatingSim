from geopy.geocoders import Nominatim
from pyproj import Transformer
import csv

# Initialisieren Sie den Geolocator
geolocator = Nominatim(user_agent="sdistrict_heating")

# Initialisieren Sie die Transformer-Funktion mit PyProj
transformer = Transformer.from_crs("epsg:4326", "epsg:25833", always_xy=True)

def get_coordinates(address):
    try:
        # Versuchen Sie, die Adresse zu geokodieren
        location = geolocator.geocode(address)
        if location:
            # Transformieren Sie die Koordinaten von WGS84 zu ETRS89 / UTM Zone 33N
            utm_x, utm_y = transformer.transform(location.longitude, location.latitude)
            return (utm_x, utm_y)
        else:
            print(f"Die Adresse {address} konnte nicht geokodiert werden.")
            return (None, None)
    except Exception as e:
        print(f"Es ist ein Fehler aufgetreten: {e}")
        return (None, None)

def process_data(input_csv, output_csv):
    with open(input_csv, mode='r', encoding='utf-8') as infile, \
        open(output_csv, mode='w', newline='', encoding='utf-8') as outfile:
        reader = csv.reader(infile, delimiter=';')
        writer = csv.writer(outfile, delimiter=';')

        # Header schreiben
        headers = next(reader)
        writer.writerow(headers + ["UTM_X", "UTM_Y"])

        for row in reader:
            land, bundesland, stadt, adresse, _, _, _ = row
            full_address = f"{adresse}, {stadt}, {bundesland}, {land}"
            utm_x, utm_y = get_coordinates(full_address)

            writer.writerow(row + [utm_x, utm_y])
    print("Verarbeitung abgeschlossen.")


input_csv = "data_input.csv"
output_csv = "data_output_ETRS89.csv"

process_data(input_csv, output_csv)
