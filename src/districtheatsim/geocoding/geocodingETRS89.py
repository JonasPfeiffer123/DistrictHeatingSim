"""
Filename: geocodingETRS89.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Contains the geocoding functions necessary to geocode adresses.
"""

import os
import csv
import tempfile
import shutil

from geopy.geocoders import Nominatim
from pyproj import Transformer

def get_coordinates(address):
    """Geocoding the Adress to coordinates and transforming them from EPSG:4326 to EPSG:25833 for higher accuracy

    Args:
        address (str): Adress of the Building that is being geocoded

    Returns:
        tuple: (UTM_X, UMT_Y) Koordinates
    """
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


def process_data(input_csv):
    """Processes the CSV file to add or update UTM_X and UTM_Y columns.

    Args:
        input_csv (str): Path to the input CSV file.
    """
    temp_fd, temp_path = tempfile.mkstemp()
    os.close(temp_fd)

    try:
        with open(input_csv, mode='r', encoding='utf-8') as infile, \
            open(temp_path, mode='w', newline='', encoding='utf-8') as outfile:
            reader = csv.reader(infile, delimiter=';')
            writer = csv.writer(outfile, delimiter=';')

            headers = next(reader)

            # Check if UTM_X and UTM_Y columns are already in the headers
            if "UTM_X" in headers and "UTM_Y" in headers:
                utm_x_index = headers.index("UTM_X")
                utm_y_index = headers.index("UTM_Y")
                headers_written = True
                writer.writerow(headers)
            else:
                utm_x_index = len(headers)
                utm_y_index = len(headers) + 1
                headers_written = False
                writer.writerow(headers + ["UTM_X", "UTM_Y"])

            for row in reader:
                country, state, city, address = row[0], row[1], row[2], row[3]
                full_address = f"{address}, {city}, {state}, {country}"
                utm_x, utm_y = get_coordinates(full_address)

                if headers_written:
                    # Ensure the row has enough columns before assignment
                    if len(row) > utm_x_index:
                        row[utm_x_index] = utm_x
                    else:
                        row.extend([utm_x])
                    if len(row) > utm_y_index:
                        row[utm_y_index] = utm_y
                    else:
                        row.extend([utm_y])
                else:
                    row.extend([utm_x, utm_y])

                writer.writerow(row)

        # Replace the original file with the updated temporary file using shutil.move
        shutil.move(temp_path, input_csv)
        print("Processing completed.")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

if __name__ == '__main__':
    # file name of the data file with adresses
    input_csv = "data_input.csv"

    # Calling the process_data function to read from input_csv and write to output_csv
    process_data(input_csv)