from geopy.geocoders import Nominatim
from pyproj import Transformer
import csv

def get_coordinates(address):
    # Initialize the Geolocator
    geolocator = Nominatim(user_agent="district_heating")

    # Initialize the Transformer function with PyProj
    # This transforms coordinates from WGS84 (GPS) to ETRS89 / UTM Zone 33N
    transformer = Transformer.from_crs("epsg:4326", "epsg:25833", always_xy=True)

    try:
        # Attempt to geocode the address
        location = geolocator.geocode(address)
        if location:
            # Transform the coordinates from WGS84 to ETRS89 / UTM Zone 33N
            utm_x, utm_y = transformer.transform(location.longitude, location.latitude)
            return (utm_x, utm_y)
        else:
            print(f"Could not geocode the address {address}.")
            return (None, None)
    except Exception as e:
        print(f"An error occurred: {e}")
        return (None, None)

def process_data(input_csv, output_csv):
    with open(input_csv, mode='r', encoding='utf-8') as infile, \
        open(output_csv, mode='w', newline='', encoding='utf-8') as outfile:
        reader = csv.reader(infile, delimiter=';')
        writer = csv.writer(outfile, delimiter=';')

        # Write the header
        headers = next(reader)
        # Adding UTM_X and UTM_Y columns to the header
        writer.writerow(headers + ["UTM_X", "UTM_Y"])

        for row in reader:
            # Extracting relevant data from the row
            country, state, city, address, _, _, _, _, _, _, _ = row
            full_address = f"{address}, {city}, {state}, {country}"
            utm_x, utm_y = get_coordinates(full_address)

            # Writing the original data along with the transformed coordinates
            writer.writerow(row + [utm_x, utm_y])
    print("Processing completed.")


#input_csv = "data_input.csv"
#output_csv = "data_output_ETRS89.csv"

#input_csv = "geocoding/data_input_gr.csv"
#output_csv = "geocoding/data_output_gr_ETRS89.csv"

#input_csv = "geocoding/data_input_Beleg2.csv"
#output_csv = "geocoding/data_output_Beleg2_ETRS89.csv"

# Calling the process_data function to read from input_csv and write to output_csv
#process_data(input_csv, output_csv)