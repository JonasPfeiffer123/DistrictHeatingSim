"""
Filename: lod2_landkreise_laden.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-07
Description: Contains the script to load the districts and municipalities from the website.
"""

import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
import time

# Datei mit den gespeicherten Landkreisen
CONFIG_FILE = "landkreise.json"
OUTPUT_FILE = "landkreise_gemeinden.json"
URL = "https://www.geodaten.sachsen.de/batch-download-4719.html"

# Selenium Setup
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Unsichtbarer Browser-Modus
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get(URL)

def get_landkreise():
    # Warten, bis die Landkreise im Dropdown erscheinen
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "select_municipality"))
    )

    # Landkreise auslesen
    landkreis_dropdown = driver.find_element(By.ID, "select_municipality")
    landkreis_options = landkreis_dropdown.find_elements(By.TAG_NAME, "option")

    # Speichern in einem Dictionary
    landkreise = {
        option.get_attribute("value"): option.text.strip() if option.text.strip() else option.get_attribute("value")
        for option in landkreis_options if option.get_attribute("value") not in ["notset", "all"]
    }

    # Browser schließen
    driver.quit()

    # Speichern der Landkreise in einer JSON-Datei
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(landkreise, f, indent=4, ensure_ascii=False)

    print(f"Gefundene Landkreise: {len(landkreise)}")
    print("Landkreise erfolgreich gespeichert in 'landkreise.json'!")

# get_landkreise()

def get_Stadt():
    # Lade gespeicherte Landkreise
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        landkreise = json.load(f)

    # Ergebnis-Dictionary
    data = {}

    # Schleife über alle Landkreise
    for landkreis_code, landkreis_name in landkreise.items():
        print(f"Verarbeite Landkreis: {landkreis_name}...")

        # Landkreis im Dropdown auswählen
        select_municipality = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "select_municipality"))
        )

        # Warten, bis das Element sichtbar und interaktiv ist
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "select_municipality")))

        # Erst klicken, dann Auswahl setzen
        select_municipality.click()
        dropdown = Select(select_municipality)
        dropdown.select_by_visible_text(landkreis_name)

        # Warten, bis die Gemeinden geladen sind
        time.sleep(2)  # Kleine Wartezeit, um sicherzugehen, dass JS ausgeführt wurde

        # Extrahieren der Gemeinden aus dem aktualisierten Dropdown
        select_district = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "select_district"))
        )
        gemeinden_options = select_district.find_elements(By.TAG_NAME, "option")

        # Speichern der Gemeinden
        gemeinden = {
            option.get_attribute("value"): option.text.strip()
            for option in gemeinden_options if option.get_attribute("value") != "notset"
        }

        data[landkreis_code] = {
            "name": landkreis_name,
            "gemeinden": gemeinden
        }

        print(f"  → Gefundene Gemeinden: {len(gemeinden)}")

    # Speichern der Daten
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"\nAlle Landkreise & Gemeinden gespeichert in '{OUTPUT_FILE}'")

    # Selenium beenden
    driver.quit()

get_Stadt()