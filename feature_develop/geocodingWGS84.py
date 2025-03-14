from geopy.geocoders import Nominatim
import csv

# Create an instance of the Geocoder and specify a custom user agent.
geolocator = Nominatim(user_agent="district_heating")

def get_coordinates(address):
    try:
        # Attempt to geocode the address
        location = geolocator.geocode(address)
        if location is not None:
            # Return latitude and longitude if the location is found
            return location.latitude, location.longitude
        else:
            print(f"Could not geocode the address {address}.")
            return None, None
    except AttributeError as e:
        print(f"An error occurred: {e}")
        return None, None

# Read from input CSV and write to output CSV
def process_data(input_csv, output_csv):
    with open(input_csv, mode='r', encoding='utf-8') as infile, open(output_csv, mode='w', newline='',
                                                                    encoding='utf-8') as outfile:
        reader = csv.reader(infile, delimiter=';')
        writer = csv.writer(outfile, delimiter=';')

        # Write the header
        headers = next(reader)
        # Adding Latitude and Longitude columns to the header
        writer.writerow(headers + ["Latitude", "Longitude"])

        for row in reader:
            # Extracting relevant data from the row
            country, state, city, address, _, _, _ = row
            full_address = f"{address}, {city}, {state}, {country}"
            lat, lon = get_coordinates(full_address)

            # Writing the original data along with the geocoded coordinates
            writer.writerow(row + [lat, lon])

    print("Processing completed.")

# Paths to the input and output CSV files
input_csv = "data_input.csv"
output_csv = "data_output_WGS84.csv"
process_data(input_csv, output_csv)
