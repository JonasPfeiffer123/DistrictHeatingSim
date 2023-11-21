from geopy.geocoders import Nominatim
import csv

# Erstellen Sie eine Instanz des Geokodierers und geben Sie einen benutzerdefinierten Benutzer-Agenten an.
geolocator = Nominatim(user_agent="district_heating")


def get_coordinates(address):
    try:
        location = geolocator.geocode(address)
        if location is not None:
            return location.latitude, location.longitude
        else:
            print(f"Die Adresse {address} konnte nicht geokodiert werden.")
            return None, None
    except AttributeError as e:
        print(f"Es ist ein Fehler aufgetreten: {e}")
        return None, None


# Pfad zur Eingabe- und Ausgabe-CSV
input_csv = "Beispieldaten.csv"
output_csv = "Beispieldaten_mit_Koordinaten.csv"

# Lesen der Eingabe-CSV und Schreiben in die Ausgabe-CSV
with open(input_csv, mode='r', encoding='utf-8') as infile, open(output_csv, mode='w', newline='',
                                                                 encoding='utf-8') as outfile:
    reader = csv.reader(infile, delimiter=';')
    writer = csv.writer(outfile, delimiter=';')

    # Header schreiben
    headers = next(reader)
    writer.writerow(headers + ["Latitude", "Longitude"])

    for row in reader:
        land, bundesland, stadt, adresse, _, _, _ = row
        full_address = f"{adresse}, {stadt}, {bundesland}, {land}"
        lat, lon = get_coordinates(full_address)

        writer.writerow(row + [lat, lon])

print("Verarbeitung abgeschlossen.")