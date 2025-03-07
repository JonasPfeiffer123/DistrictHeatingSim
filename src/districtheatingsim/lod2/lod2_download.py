"""
Filename: lod2_download.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-07
Description: Contains the script to download the LOD2 files.
"""

import json
import os
import requests
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
import time
import zipfile

# Datei mit gespeicherten LOD2-Dateinamen
URL = "https://www.geodaten.sachsen.de/batch-download-4719.html"    # URL der Download-Seite

def get_lod2_links(landkreis_name, gemeinde_name, download_dir):
    os.makedirs(download_dir, exist_ok=True)
    
    """Ermittelt die tatsächlichen Download-Links für eine Gemeinde und speichert sie."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(URL)

    print(f"Landkreis: {landkreis_name}")
    print(f"Gemeinde: {gemeinde_name}...")

    try:
        # Landkreis setzen
        select_municipality = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "select_municipality"))
        )
        dropdown_municipality = Select(select_municipality)
        dropdown_municipality.select_by_visible_text(landkreis_name)
        time.sleep(2)

        # Stadt auswählen
        select_district = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "select_district"))
        )
        dropdown_district = Select(select_district)
        dropdown_district.select_by_visible_text(gemeinde_name)
        time.sleep(2)

        # LOD2 Produkt auswählen
        select_product = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "select_product"))
        )
        dropdown_product = Select(select_product)
        dropdown_product.select_by_visible_text("3D-Stadtmodell LoD2 Shape (LoD2_Shape)")
        time.sleep(2)

        # Extrahiere die echten Download-Links
        download_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "div_downloads"))
        )
        download_links = [a.get_attribute("href") for a in download_div.find_elements(By.TAG_NAME, "a")]

    finally:
        driver.quit()

    if download_links:
        print(f"{len(download_links)} Download-Links gefunden.")
        for link in download_links:
            print(f"    🔗 {link}")

        # Speichern in JSON
        result = {
            "landkreis": landkreis_name,
            "gemeinde": gemeinde_name,
            "lod2_files": download_links
        }

        OUTPUT_FILE = os.path.join(download_dir, "lod2_selected.json")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)

        return download_links
    else:
        print("Keine Download-Links gefunden.")
        return None


def download_lod2_files(landkreis_name, gemeinde_name, download_dir, extract_dir):
    os.makedirs(download_dir, exist_ok=True)
    
    # Lade gespeicherte Download-Links
    OUTPUT_FILE = os.path.join(download_dir, "lod2_selected.json")
    if not os.path.exists(OUTPUT_FILE):
        print("Keine gespeicherten Download-Links gefunden. Bitte zuerst `get_lod2_links` ausführen!")
        return

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data["landkreis"] != landkreis_name or data["gemeinde"] != gemeinde_name:
        print("Die gespeicherten Daten stimmen nicht mit der Auswahl überein.")
        return

    download_links = data["lod2_files"]

    # Zielordner für Gemeinde erstellen
    os.makedirs(extract_dir, exist_ok=True)

    for link in download_links:
        parsed_url = urllib.parse.urlparse(link)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        file_name = query_params["files"][0] if "files" in query_params else "unknown_file.zip"

        zip_path = os.path.join(extract_dir, file_name)

        # ⬇️ Datei nur herunterladen, wenn sie nicht existiert
        if not os.path.exists(zip_path):
            response = requests.get(link, stream=True)
            if response.status_code == 200:
                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"✅ Datei gespeichert: {zip_path}")
            else:
                print(f"❌ Fehler beim Download: {link}")
                continue

        # 🗂 ZIP entpacken, aber doppelte Unterverzeichnisse vermeiden
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_content = zip_ref.namelist()
            first_folder = os.path.commonprefix(zip_content).rstrip('/')

            # 🔄 Überprüfen, ob ZIP bereits ein Verzeichnis enthält
            if first_folder and "/" in first_folder:
                extract_target = extract_dir  # Direkt in `kommune_folder` extrahieren
            else:
                extract_target = os.path.join(extract_dir, file_name.replace(".zip", ""))
            
            zip_ref.extractall(extract_target)
            print(f"📂 Entpackt nach: {extract_target}")