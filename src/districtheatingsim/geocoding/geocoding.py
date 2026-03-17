"""
Geocoding module for address to coordinate transformation.

Provides Nominatim-based geocoding with coordinate system transformation
from WGS84 to UTM Zone 33N (ETRS89).

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os
import csv
import time
import tempfile
import shutil

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from pyproj import Transformer

# Shared geolocator instance (Nominatim usage policy: max 1 req/sec, identify your app)
_geolocator = Nominatim(user_agent="DistrictHeatingSim/1.0")
_geocode = RateLimiter(_geolocator.geocode, min_delay_seconds=1, max_retries=3, error_wait_seconds=5)


def get_coordinates(address, from_crs="epsg:4326", to_crs="epsg:25833"):
    """
    Geocode address and transform coordinates to UTM.

    Uses a shared rate-limited Nominatim instance (max 1 req/sec) to comply
    with the Nominatim usage policy.

    :param address: Address to geocode
    :type address: str
    :param from_crs: Source CRS (default: WGS84)
    :type from_crs: str
    :param to_crs: Target CRS (default: ETRS89/UTM Zone 33N)
    :type to_crs: str
    :return: (UTM_X, UTM_Y) coordinates or (None, None) if failed
    :rtype: tuple of float
    """
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)

    try:
        location = _geocode(address)
        if location:
            utm_x, utm_y = transformer.transform(location.longitude, location.latitude)
            return (utm_x, utm_y)
        else:
            print(f"Could not geocode the address {address}.")
            return (None, None)
    except Exception as e:
        print(f"An error occurred: {e}")
        return (None, None)


def process_data(input_csv, crs: str = "EPSG:25833"):
    """
    Add projected coordinates to CSV file via geocoding.

    Requests are rate-limited to 1/sec to comply with the Nominatim usage policy.

    :param input_csv: Path to CSV file (delimiter ';', columns: country, state, city, address)
    :type input_csv: str
    :param crs: Target projected CRS for UTM_X/UTM_Y columns (default EPSG:25833)
    :type crs: str
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
                utm_x, utm_y = get_coordinates(full_address, to_crs=crs)  # rate-limited via _geocode

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