"""
LOD2 Download Module
====================

This module provides automated download functionality for LOD2 (Level of Detail 2) 
building data from the Saxon geodata portal.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-07

It uses Selenium WebDriver to interact with the dynamic web interface and handles the complete download and extraction 
workflow for 3D building models in Shape format.

The module supports batch downloads for entire municipalities and automatically 
handles file extraction with intelligent directory structure management.
"""

import json
import os
import requests
import urllib.parse
import time
import zipfile
from pathlib import Path
from typing import List, Optional, Dict, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Configuration constants
URL = "https://www.geodaten.sachsen.de/batch-download-4719.html"
LOD2_PRODUCT_NAME = "3D-Stadtmodell LoD2 Shape (LoD2_Shape)"
LINKS_FILE = "lod2_selected.json"
DOWNLOAD_TIMEOUT = 10
CHUNK_SIZE = 8192

def _setup_webdriver() -> webdriver.Chrome:
    """
    Set up and configure Chrome WebDriver for headless operation.
    
    Returns
    -------
    webdriver.Chrome
        Configured Chrome WebDriver instance optimized for server environments.
        
    Notes
    -----
    - Runs in headless mode for server compatibility
    - Automatically downloads and manages ChromeDriver
    - Configured for minimal resource usage and stability
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def get_lod2_links(landkreis_name: str, gemeinde_name: str, download_dir: str) -> Optional[List[str]]:
    """
    Extract LOD2 download links for a specific municipality from Saxon geodata portal.
    
    This function automates the web interaction to select a district (Landkreis) and 
    municipality (Gemeinde), then extracts the actual download URLs for LOD2 building 
    data files. The extracted links are saved to a JSON file for later use.
    
    Parameters
    ----------
    landkreis_name : str
        Name of the district (Landkreis) as it appears in the web interface.
        Must match exactly the text shown in the dropdown menu.
    gemeinde_name : str
        Name of the municipality (Gemeinde) as it appears in the web interface.
        Must match exactly the text shown in the dropdown menu.
    download_dir : str
        Directory path where the links JSON file will be saved.
        Directory will be created if it doesn't exist.
        
    Returns
    -------
    List[str] or None
        List of download URLs for LOD2 files, or None if no links found.
        
    Raises
    ------
    TimeoutException
        If web elements cannot be located within the timeout period.
    WebDriverException
        If there are issues with WebDriver setup or page navigation.
    OSError
        If the download directory cannot be created.
        
    Examples
    --------
    >>> # Extract download links for Dresden
    >>> links = get_lod2_links("Dresden", "Dresden", "./downloads")
    >>> if links:
    ...     print(f"Found {len(links)} download files")
    Found 3 download files
    
    >>> # Check saved links file
    >>> with open("./downloads/lod2_selected.json", "r") as f:
    ...     data = json.load(f)
    >>> print(data["gemeinde"])
    Dresden
    
    Notes
    -----
    - Automatically creates the download directory if it doesn't exist
    - Saves results to 'lod2_selected.json' in the specified directory
    - Uses intelligent waiting for dynamic content loading
    - Closes WebDriver automatically after completion
    - Requires active internet connection and access to Saxon geodata portal
    
    See Also
    --------
    download_lod2_files : Download and extract the LOD2 files using saved links
    """
    # Create download directory
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)
    
    driver = _setup_webdriver()
    download_links = []
    
    try:
        print(f"Processing: {landkreis_name} → {gemeinde_name}")
        driver.get(URL)
        
        # Select district (Landkreis)
        select_municipality = WebDriverWait(driver, DOWNLOAD_TIMEOUT).until(
            EC.element_to_be_clickable((By.ID, "select_municipality"))
        )
        dropdown_municipality = Select(select_municipality)
        dropdown_municipality.select_by_visible_text(landkreis_name)
        time.sleep(2)
        
        # Select municipality (Gemeinde)
        select_district = WebDriverWait(driver, DOWNLOAD_TIMEOUT).until(
            EC.element_to_be_clickable((By.ID, "select_district"))
        )
        dropdown_district = Select(select_district)
        dropdown_district.select_by_visible_text(gemeinde_name)
        time.sleep(2)
        
        # Select LOD2 product
        select_product = WebDriverWait(driver, DOWNLOAD_TIMEOUT).until(
            EC.element_to_be_clickable((By.ID, "select_product"))
        )
        dropdown_product = Select(select_product)
        dropdown_product.select_by_visible_text(LOD2_PRODUCT_NAME)
        time.sleep(2)
        
        # Extract download links
        download_div = WebDriverWait(driver, DOWNLOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "div_downloads"))
        )
        download_links = [
            a.get_attribute("href") 
            for a in download_div.find_elements(By.TAG_NAME, "a")
            if a.get_attribute("href")
        ]
        
    except TimeoutException as e:
        print(f"Timeout while extracting links for {gemeinde_name}: {e}")
        return None
    except WebDriverException as e:
        print(f"WebDriver error for {gemeinde_name}: {e}")
        return None
    finally:
        driver.quit()
    
    if download_links:
        print(f"Found {len(download_links)} download links:")
        for i, link in enumerate(download_links, 1):
            print(f"  {i}. {link}")
        
        # Save links to JSON file
        result = {
            "landkreis": landkreis_name,
            "gemeinde": gemeinde_name,
            "lod2_files": download_links,
            "extraction_date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        links_file = download_path / LINKS_FILE
        with open(links_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        
        print(f"Links saved to: {links_file}")
        return download_links
    else:
        print("No download links found")
        return None

def download_lod2_files(landkreis_name: str, gemeinde_name: str, 
                       download_dir: str, extract_dir: str) -> bool:
    """
    Download and extract LOD2 files using previously saved download links.
    
    This function loads download URLs from a JSON file (created by get_lod2_links)
    and downloads the corresponding LOD2 building data files. It handles the complete
    workflow including downloading ZIP files and extracting them with intelligent
    directory structure management.
    
    Parameters
    ----------
    landkreis_name : str
        Name of the district (Landkreis). Must match the data in the links file.
    gemeinde_name : str
        Name of the municipality (Gemeinde). Must match the data in the links file.
    download_dir : str
        Directory containing the saved links JSON file.
    extract_dir : str
        Target directory for extracted LOD2 files.
        Directory will be created if it doesn't exist.
        
    Returns
    -------
    bool
        True if all files were successfully downloaded and extracted, False otherwise.
        
    Raises
    ------
    FileNotFoundError
        If the links JSON file doesn't exist in the download directory.
    json.JSONDecodeError
        If the links file contains invalid JSON data.
    requests.RequestException
        If there are network issues during file download.
    zipfile.BadZipFile
        If downloaded ZIP files are corrupted or invalid.
    OSError
        If directories cannot be created or files cannot be written.
        
    Examples
    --------
    >>> # Download files for Dresden (requires prior link extraction)
    >>> success = download_lod2_files("Dresden", "Dresden", 
    ...                              "./downloads", "./extracted")
    >>> if success:
    ...     print("All files downloaded successfully")
    
    >>> # Check extracted files
    >>> import os
    >>> files = os.listdir("./extracted")
    >>> print(f"Extracted {len(files)} files")
    
    Notes
    -----
    - Requires get_lod2_links() to be run first to generate the links file
    - Automatically creates extraction directory if it doesn't exist
    - Skips downloading files that already exist locally
    - Handles ZIP files with different internal directory structures
    - Validates downloaded files and parameters against saved metadata
    - Uses streaming download for large files to minimize memory usage
    
    See Also
    --------
    get_lod2_links : Extract download links from the geodata portal
    """
    # Ensure directories exist
    download_path = Path(download_dir)
    extract_path = Path(extract_dir)
    extract_path.mkdir(parents=True, exist_ok=True)
    
    # Load saved download links
    links_file = download_path / LINKS_FILE
    if not links_file.exists():
        raise FileNotFoundError(
            f"Links file not found: {links_file}\n"
            f"Please run get_lod2_links() first to extract download URLs."
        )
    
    try:
        with open(links_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in links file: {e}")
    
    # Validate parameters against saved data
    if data["landkreis"] != landkreis_name or data["gemeinde"] != gemeinde_name:
        print(f"Parameter mismatch:")
        print(f"  Expected: {data['landkreis']} → {data['gemeinde']}")
        print(f"  Provided: {landkreis_name} → {gemeinde_name}")
        return False
    
    download_links = data["lod2_files"]
    success_count = 0
    
    print(f"Starting download for {gemeinde_name} ({len(download_links)} files)")
    
    for i, link in enumerate(download_links, 1):
        print(f"\n[{i}/{len(download_links)}] Processing: {link}")
        
        try:
            # Extract filename from URL
            parsed_url = urllib.parse.urlparse(link)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            file_name = (query_params.get("files", ["unknown_file.zip"])[0]
                        if "files" in query_params else f"lod2_file_{i}.zip")
            
            zip_path = extract_path / file_name
            
            # Download file if it doesn't exist
            if not zip_path.exists():
                print(f"  Downloading: {file_name}")
                response = requests.get(link, stream=True)
                response.raise_for_status()
                
                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                
                print(f"  ✅ Downloaded: {zip_path.name}")
            else:
                print(f"  ⏭️  Already exists: {zip_path.name}")
            
            # Extract ZIP file with intelligent directory handling
            if zip_path.exists():
                print(f"  Extracting: {zip_path.name}")
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_content = zip_ref.namelist()
                    
                    # Check if ZIP contains a root directory
                    common_prefix = os.path.commonprefix(zip_content).rstrip('/')
                    
                    if common_prefix and "/" in common_prefix:
                        # ZIP has internal directory structure - extract directly
                        extract_target = extract_path
                    else:
                        # ZIP has flat structure - create subdirectory
                        extract_target = extract_path / zip_path.stem
                        extract_target.mkdir(exist_ok=True)
                    
                    zip_ref.extractall(extract_target)
                    print(f"  📂 Extracted to: {extract_target}")
                
                success_count += 1
            
        except requests.RequestException as e:
            print(f"  ❌ Download failed: {e}")
            continue
        except zipfile.BadZipFile as e:
            print(f"  ❌ ZIP extraction failed: {e}")
            continue
        except OSError as e:
            print(f"  ❌ File system error: {e}")
            continue
    
    print(f"\n{'='*50}")
    print(f"Download Summary:")
    print(f"  Municipality: {gemeinde_name}")
    print(f"  Successful: {success_count}/{len(download_links)} files")
    print(f"  Target directory: {extract_path}")
    
    return success_count == len(download_links)

def batch_download_lod2(districts_data: Dict[str, Dict[str, Any]], 
                       base_download_dir: str, base_extract_dir: str) -> Dict[str, bool]:
    """
    Perform batch download of LOD2 data for multiple municipalities.
    
    This convenience function processes multiple municipalities in sequence,
    handling the complete workflow of link extraction and file downloading
    for each location.
    
    Parameters
    ----------
    districts_data : Dict[str, Dict[str, Any]]
        Dictionary containing district and municipality information.
        Expected structure matches output from lod2_landkreise_laden.get_municipalities().
    base_download_dir : str
        Base directory for storing intermediate files and download links.
    base_extract_dir : str
        Base directory for extracted LOD2 files.
        
    Returns
    -------
    Dict[str, bool]
        Dictionary mapping municipality names to their download success status.
        
    Examples
    --------
    >>> # Batch download for multiple municipalities
    >>> districts = {
    ...     "14713": {
    ...         "name": "Dresden",
    ...         "gemeinden": {"14713000": "Dresden"}
    ...     }
    ... }
    >>> results = batch_download_lod2(districts, "./downloads", "./lod2_data")
    >>> print(f"Success rate: {sum(results.values())}/{len(results)}")
    
    See Also
    --------
    get_lod2_links : Extract download links for a single municipality
    download_lod2_files : Download and extract files for a single municipality
    """
    results = {}
    
    for district_code, district_info in districts_data.items():
        district_name = district_info["name"]
        
        for municipality_code, municipality_name in district_info["gemeinden"].items():
            print(f"\n{'='*60}")
            print(f"Processing: {district_name} → {municipality_name}")
            print(f"{'='*60}")
            
            try:
                # Create specific directories for this municipality
                download_dir = os.path.join(base_download_dir, municipality_name)
                extract_dir = os.path.join(base_extract_dir, municipality_name)
                
                # Step 1: Extract download links
                links = get_lod2_links(district_name, municipality_name, download_dir)
                
                if links:
                    # Step 2: Download and extract files
                    success = download_lod2_files(district_name, municipality_name, 
                                                download_dir, extract_dir)
                    results[municipality_name] = success
                else:
                    results[municipality_name] = False
                    
            except Exception as e:
                print(f"Error processing {municipality_name}: {e}")
                results[municipality_name] = False
    
    # Print summary
    print(f"\n{'='*60}")
    print("BATCH DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    successful = sum(results.values())
    total = len(results)
    
    for municipality, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {municipality}: {status}")
    
    print(f"\nOverall: {successful}/{total} municipalities processed successfully")
    
    return results

if __name__ == "__main__":
    # Example usage
    print("LOD2 Download Module")
    print("Run functions individually or import as module")
    
    # Example: Extract links for a single municipality
    # links = get_lod2_links("Dresden", "Dresden", "./downloads")
    
    # Example: Download files using saved links
    # success = download_lod2_files("Dresden", "Dresden", "./downloads", "./extracted")