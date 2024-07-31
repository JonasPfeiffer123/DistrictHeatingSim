"""
Filename: download_lod2.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Script for downloading and unzipping the LOD2 data.
"""

import requests
import os
import zipfile

def download_file(url, destination_folder):
    """Download and unzip a ZIP file from a URL into a folder with the same name within the specified destination folder.

    Args:
        url (str): The URL of the ZIP file to be downloaded.
        destination_folder (str): The folder where the ZIP file will be downloaded and unzipped.

    Returns:
        None
    """
    # Extract the relevant part of the filename from the URL
    filename = url.split('=')[-1]
    filename = filename.replace('%2F', '/').split('/')[-1]
    
    # Determine the path of the ZIP file and the target folder for unzipping
    file_path = os.path.join(destination_folder, filename)
    extract_folder = os.path.join(destination_folder, filename.replace('.zip', ''))

    # Send a GET request and save the response to a file
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"File downloaded: {filename}")

        # Create the target folder for unzipping if it does not exist
        if not os.path.exists(extract_folder):
            os.makedirs(extract_folder)

        # Unzip the file into the folder with the same name
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
        print(f"File unzipped to: {extract_folder}")

        # Optionally delete the ZIP file after unzipping
        os.remove(file_path)
        print(f"ZIP file deleted: {filename}")
    else:
        print(f"Error downloading {url}")

def download_from_list(file_list_path, destination_folder):
    """Read download links from a text file and download them.

    Args:
        file_list_path (str): The path to the text file containing download links.
        destination_folder (str): The folder where the downloaded files will be saved.

    Returns:
        None
    """
    # Create the destination directory if it does not exist
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    with open(file_list_path, 'r') as file:
        for url in file.readlines():
            url = url.strip()  # Remove whitespace and newlines
            if url:  # Ensure the line is not empty
                download_file(url, destination_folder)

# Path to the text file with the download links
file_list_path = 'C:/Users/username/heating_network_generation/project_data/Görlitz_SH_Campus/Gebäudedaten/lod2_data/lod2_downloadlinks.txt'

# Destination folder for the downloaded files
destination_folder = 'C:/Users/username/heating_network_generation/project_data/Görlitz_SH_Campus/Gebäudedaten/lod2_data'

download_from_list(file_list_path, destination_folder)
