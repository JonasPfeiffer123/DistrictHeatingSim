"""
Filename: 01_example_geocoding.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-18
Description: This script runs the geocoding process on a given CSV file containing addresses.
The script imports the `process_data` function from the `geocodingETRS89` module
within the `districtheatingsim` package and executes it with the specified CSV file.
Usage:
    Run this script directly to process the addresses in the "data/data_ETRS89.csv" file.
Functions:
    process_data(file_path: str) -> None
        Processes the geocoding of addresses from the given CSV file.
Example:
    $ python 01_geocoding.py
"""

import pandas as pd
import traceback

from districtheatingsim.geocoding.geocoding import process_data

if __name__ == '__main__':
    try:
        print("Running the geocoding script.")

        example_data_path = "examples/data/data_ETRS89.csv"

        print(f"Using example data from {example_data_path}.")

        example_data = pd.read_csv(example_data_path, sep=';')

        print("Example data:")
        print(example_data)

        process_data(example_data_path)

        geocode_data = pd.read_csv(example_data_path, sep=';')

        print("Geocoded data:")
        print(geocode_data)

    except Exception as e:
        print("An error occurred:")
        print(traceback.format_exc())
        raise e