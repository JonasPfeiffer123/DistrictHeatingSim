"""
LOD2 District Download Module
=============================

This module provides functionality to scrape district (Landkreise) and municipality
(Gemeinden) data from the Saxon geodata portal.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-07

It uses Selenium WebDriver to interact with dynamic web content and extract administrative boundary information
for LOD2 building data downloads.
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configuration constants
CONFIG_FILE = "landkreise.json"
OUTPUT_FILE = "landkreise_gemeinden.json"
URL = "https://www.geodaten.sachsen.de/batch-download-4719.html"

def _setup_webdriver() -> webdriver.Chrome:
    """
    Set up and configure Chrome WebDriver with optimal settings.
    
    Returns
    -------
    webdriver.Chrome
        Configured Chrome WebDriver instance with headless mode enabled.
        
    Notes
    -----
    - Uses headless mode for server compatibility
    - Automatically downloads and manages ChromeDriver
    - Optimized for minimal resource usage
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def get_district(output_file: Optional[str] = None) -> Dict[str, str]:
    """
    Extract district (Landkreis) data from Saxon geodata portal.
    
    This function scrapes the district dropdown menu from the Saxon geodata portal
    and extracts all available districts with their codes and names.
    
    Parameters
    ----------
    output_file : str, optional
        Path to save the extracted district data. If None, uses CONFIG_FILE.
        
    Returns
    -------
    Dict[str, str]
        Dictionary mapping district codes to district names.
        
    Raises
    ------
    TimeoutException
        If the webpage elements cannot be located within the timeout period.
    WebDriverException
        If there are issues with the WebDriver setup or navigation.
    FileNotFoundError
        If the output directory does not exist.
        
    Examples
    --------
    >>> districts = get_landkreise()
    >>> print(f"Found {len(districts)} districts")
    Found 13 districts
    
    >>> # Save to custom file
    >>> districts = get_landkreise("custom_districts.json")
    
    Notes
    -----
    - Automatically filters out placeholder values ("notset", "all")
    - Uses UTF-8 encoding for proper German character support
    - Creates JSON file with proper indentation for readability
    - Closes WebDriver automatically after completion
    """
    if output_file is None:
        output_file = CONFIG_FILE
        
    driver = _setup_webdriver()
    
    try:
        driver.get(URL)
        
        # Wait for district dropdown to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "select_municipality"))
        )
        
        # Extract district options
        landkreis_dropdown = driver.find_element(By.ID, "select_municipality")
        landkreis_options = landkreis_dropdown.find_elements(By.TAG_NAME, "option")
        
        # Build district dictionary, filtering invalid entries
        landkreise = {
            option.get_attribute("value"): option.text.strip() if option.text.strip() else option.get_attribute("value")
            for option in landkreis_options 
            if option.get_attribute("value") not in ["notset", "all"]
        }
        
        # Save to JSON file with UTF-8 encoding
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(landkreise, f, indent=4, ensure_ascii=False)
        
        print(f"Successfully extracted {len(landkreise)} districts")
        print(f"Districts saved to '{output_file}'")
        
        return landkreise
        
    finally:
        driver.quit()

def get_municipalities(districts_file: Optional[str] = None, output_file: Optional[str] = None) -> Dict[str, Dict]:
    """
    Extract municipality data for all districts from Saxon geodata portal.
    
    This function loads previously extracted district data and scrapes the 
    corresponding municipalities for each district by interacting with 
    the dynamic dropdown menus on the webpage.
    
    Parameters
    ----------
    districts_file : str, optional
        Path to JSON file containing district data. If None, uses CONFIG_FILE.
    output_file : str, optional
        Path to save the extracted municipality data. If None, uses OUTPUT_FILE.
        
    Returns
    -------
    Dict[str, Dict]
        Nested dictionary structure with district codes as keys and district 
        information including municipality data as values.
        
        Structure::
        
            {
                "district_code": {
                    "name": "District Name",
                    "gemeinden": {
                        "municipality_code": "Municipality Name",
                        ...
                    }
                },
                ...
            }
        
    Raises
    ------
    FileNotFoundError
        If the districts file cannot be found.
    TimeoutException
        If webpage elements cannot be located within timeout periods.
    WebDriverException
        If there are issues with WebDriver interaction.
    json.JSONDecodeError
        If the districts file contains invalid JSON.
        
    Examples
    --------
    >>> # Extract municipalities for all districts
    >>> data = get_municipalities()
    >>> print(f"Processed {len(data)} districts")
    Processed 13 districts
    
    >>> # Use custom input/output files
    >>> data = get_municipalities("my_districts.json", "my_output.json")
    
    >>> # Access municipality data
    >>> for district_code, district_info in data.items():
    ...     print(f"{district_info['name']}: {len(district_info['gemeinden'])} municipalities")
    
    Notes
    -----
    - Requires district data to be available (run get_landkreise() first)
    - Uses intelligent waiting strategies for dynamic content loading
    - Filters out placeholder municipality entries
    - Progress information is printed during execution
    - Automatically handles UTF-8 encoding for German characters
    """
    if districts_file is None:
        districts_file = CONFIG_FILE
    if output_file is None:
        output_file = OUTPUT_FILE
        
    # Load district data
    try:
        with open(districts_file, "r", encoding="utf-8") as f:
            landkreise = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Districts file '{districts_file}' not found. "
            "Run get_landkreise() first to extract district data."
        )
    
    driver = _setup_webdriver()
    data = {}
    
    try:
        driver.get(URL)
        
        # Process each district
        for landkreis_code, landkreis_name in landkreise.items():
            print(f"Processing district: {landkreis_name}...")
            
            try:
                # Wait for and select district dropdown
                select_municipality = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "select_municipality"))
                )
                
                select_municipality.click()
                dropdown = Select(select_municipality)
                dropdown.select_by_visible_text(landkreis_name)
                
                # Wait for municipalities to load
                time.sleep(2)
                
                # Extract municipality options
                select_district = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "select_district"))
                )
                gemeinden_options = select_district.find_elements(By.TAG_NAME, "option")
                
                # Build municipality dictionary, filtering invalid entries
                gemeinden = {
                    option.get_attribute("value"): option.text.strip()
                    for option in gemeinden_options 
                    if option.get_attribute("value") != "notset"
                }
                
                data[landkreis_code] = {
                    "name": landkreis_name,
                    "gemeinden": gemeinden
                }
                
                print(f"  → Found {len(gemeinden)} municipalities")
                
            except TimeoutException:
                print(f"  → Timeout for district {landkreis_name}, skipping...")
                continue
        
        # Save complete dataset
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        print(f"\nSuccessfully processed {len(data)} districts")
        print(f"All districts & municipalities saved to '{output_file}'")
        
        return data
        
    finally:
        driver.quit()

def scrape_all_data(districts_output: Optional[str] = None, 
                   municipalities_output: Optional[str] = None) -> Dict[str, Dict]:
    """
    Complete workflow to scrape both districts and municipalities.
    
    This convenience function combines both scraping operations into a single
    workflow, first extracting districts and then their corresponding municipalities.
    
    Parameters
    ----------
    districts_output : str, optional
        Path to save district data. If None, uses CONFIG_FILE.
    municipalities_output : str, optional  
        Path to save municipality data. If None, uses OUTPUT_FILE.
        
    Returns
    -------
    Dict[str, Dict]
        Complete dataset with districts and their municipalities.
        
    Examples
    --------
    >>> # Scrape all data with default file names
    >>> complete_data = scrape_all_data()
    
    >>> # Use custom output files
    >>> complete_data = scrape_all_data("districts.json", "complete_data.json")
    
    See Also
    --------
    get_district : Extract district data only
    get_municipalities : Extract municipality data (requires districts)
    """
    print("Starting complete data scraping workflow...")
    print("Step 1: Extracting districts...")
    
    districts = get_district(districts_output)
    
    print("Step 2: Extracting municipalities...")
    municipalities_data = get_municipalities(districts_output, municipalities_output)
    
    print("Complete workflow finished successfully!")
    return municipalities_data

if __name__ == "__main__":
    # Example usage - uncomment desired operation
    
    # Extract districts only
    # get_district()
    
    # Extract municipalities (requires districts file)
    get_municipalities()
    
    # Complete workflow
    # scrape_all_data()