import requests
import os
import zipfile

import os

def download_file(url, destination_folder):
    """Download und entpacke eine ZIP-Datei von einer URL in einen gleichnamigen Ordner im angegebenen Zielordner."""
    # Extrahiere den relevanten Teil des Dateinamens aus der URL
    filename = url.split('=')[-1]
    filename = filename.replace('%2F', '/').split('/')[-1]
    
    # Bestimme den Pfad der ZIP-Datei und den Zielordner für das Entpacken
    file_path = os.path.join(destination_folder, filename)
    extract_folder = os.path.join(destination_folder, filename.replace('.zip', ''))

    # Sende eine GET-Anfrage und speichere die Antwort in einer Datei
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Datei heruntergeladen: {filename}")

        # Erstelle den Zielordner für das Entpacken, falls er noch nicht existiert
        if not os.path.exists(extract_folder):
            os.makedirs(extract_folder)

        # Entpacke die ZIP-Datei in den gleichnamigen Ordner
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
        print(f"Datei entpackt in: {extract_folder}")

        # Optional: Lösche die ZIP-Datei nach dem Entpacken
        os.remove(file_path)
        print(f"ZIP-Datei gelöscht: {filename}")
    else:
        print(f"Fehler beim Herunterladen von {url}")

def download_from_list(file_list_path, destination_folder):
    """Liest Download-Links aus einer Textdatei und lädt sie herunter."""
    # Erstelle das Zielverzeichnis, falls es nicht existiert
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    with open(file_list_path, 'r') as file:
        for url in file.readlines():
            url = url.strip()  # Entferne Whitespace und Zeilenumbrüche
            if url:  # Stelle sicher, dass die Zeile nicht leer ist
                download_file(url, destination_folder)

# Pfad zur Textdatei mit den Download-Links
file_list_path = 'C:/Users/username/heating_network_generation/project_data/Görlitz_SH_Campus/Gebäudedaten/lod2_data/lod2_downloadlinks.txt'

# Zielordner für die heruntergeladenen Dateien
destination_folder = 'C:/Users/username/heating_network_generation/project_data/Görlitz_SH_Campus/Gebäudedaten/lod2_data'

download_from_list(file_list_path, destination_folder)