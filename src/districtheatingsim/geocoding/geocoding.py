"""
Filename: geocoding.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-06-25
Description: Contains the geocoding functions necessary to geocode addresses.
"""

import os
import csv
import tempfile
import shutil

from geopy.geocoders import Nominatim
from pyproj import Transformer

def get_coordinates(address, from_crs="epsg:4326", to_crs="epsg:25833"):
    """
    Geocode an address and transform coordinates from EPSG:4326 to EPSG:25833.

    Uses the Nominatim geocoder to obtain WGS84 coordinates and transforms them
    to ETRS89 / UTM Zone 33N for higher accuracy.

    Parameters
    ----------
    address : str
        Address of the building to be geocoded.
    from_crs : str, optional
        Source coordinate reference system (default is "epsg:4326").
    to_crs : str, optional
        Target coordinate reference system (default is "epsg:25833").

    Returns
    -------
    tuple of float or (None, None)
        (UTM_X, UTM_Y) coordinates if successful, otherwise (None, None).
    """
    geolocator = Nominatim(user_agent="DistrictHeatingSim")
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)

    try:
        location = geolocator.geocode(address)
        if location:
            utm_x, utm_y = transformer.transform(location.longitude, location.latitude)
            return (utm_x, utm_y)
        else:
            print(f"Could not geocode the address {address}.")
            return (None, None)
    except Exception as e:
        print(f"An error occurred: {e}")
        return (None, None)


def process_data(input_csv):
    """
    Process a CSV file to add or update UTM_X and UTM_Y columns using geocoding.

    Reads a CSV file with address information, geocodes each address, transforms
    the coordinates to UTM, and writes the results back to the file. If the columns
    ``UTM_X`` and ``UTM_Y`` already exist, they are updated; otherwise, they are added.

    Parameters
    ----------
    input_csv : str
        Path to the input CSV file. The file must use ``;`` as delimiter and contain
        at least the columns: country, state, city, address (in this order).

    Returns
    -------
    None
    """
    temp_fd, temp_path = tempfile.mkstemp()
    os.close(temp_fd)

    try:
        with open(input_csv, mode='r', encoding='utf-8') as infile, \
            open(temp_path, mode='w', newline='', encoding='utf-8-sig') as outfile:
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
    # File name of the data file with addresses
    input_csv = "data/data_geocoded.csv" # dummy file name, replace with actual file path

    # Call the process_data function to read from input_csv and write to
    #process_data(input_csv)