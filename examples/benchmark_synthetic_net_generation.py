"""
Filename: 06_benchmark_synthetic_net_generation.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-27
Description: Benchmarks the net generation for synthetic GIS data with varying building counts.
"""

import os
import time
import geopandas as gpd
import matplotlib.pyplot as plt

from districtheatingsim.net_generation.import_and_create_layers import generate_and_export_layers

# Einstellungen
base_dir = "examples\\data"
base_data_dir = "examples\\data\\synthetic_gis_data"
output_base_dir = "examples\\benchmark_output"
coordinates = [(498823.8,5667017.8)]  # Dummy heat source in UTM (passt zum synthetischen Kataster)
algorithm = "Advanced MST"  # oder "MST", "Steiner", etc.

building_counts = [25, 50, 75, 100, 150, 200, 250, 300]


def run_benchmark():
    os.makedirs(output_base_dir, exist_ok=True)

    total_start = time.time()
    results = []

    for n_buildings in building_counts:
        print(f"\n--- Starte Netzgenerierung für {n_buildings} Gebäude ---")
        data_dir = os.path.join(base_data_dir, f"{n_buildings}_buildings")
        data_csv_file_name = os.path.join(data_dir, "synthetic_buildings.csv")
        #osm_street_layer_geojson_file_name = os.path.join(data_dir, "synthetic_streets.geojson")
        osm_street_layer_geojson_file_name = os.path.join(base_dir, "streets.geojson")
        out_dir = os.path.join(output_base_dir, f"{n_buildings}_buildings")
        os.makedirs(out_dir, exist_ok=True)

        subdir = os.path.join(out_dir, "Wärmenetz")
        os.makedirs(subdir, exist_ok=True)

        start = time.time()
        try:
            generate_and_export_layers(
                osm_street_layer_geojson_file_name,
                data_csv_file_name,
                coordinates,
                out_dir,
                algorithm=algorithm
            )
            elapsed = time.time() - start
            print(f"Netz für {n_buildings} Gebäude generiert in {elapsed:.2f} Sekunden.")
            results.append((n_buildings, elapsed))
        except Exception as e:
            print(f"Fehler bei {n_buildings} Gebäuden: {e}")
            results.append((n_buildings, None))

    total_elapsed = time.time() - total_start
    print("\nBenchmark abgeschlossen.")
    print(f"Gesamtlaufzeit: {total_elapsed:.2f} Sekunden\n")

    print("Ergebnisse:")
    for n_buildings, elapsed in results:
        if elapsed is not None:
            print(f"{n_buildings} Gebäude: {elapsed:.2f} s")
        else:
            print(f"{n_buildings} Gebäude: Fehler")

    # Optional: Ergebnisse als CSV speichern
    import pandas as pd
    df = pd.DataFrame(results, columns=["n_buildings", "runtime_seconds"])
    df.to_csv(os.path.join(output_base_dir, "benchmark_results.csv"), index=False)
    print(f"\nBenchmark-Ergebnisse gespeichert unter {output_base_dir}\\benchmark_results.csv")

def plot_benchmark_networks(
    data_base_dir="examples/data/synthetic_gis_data",
    result_base_dir="examples/benchmark_output",
    building_counts=[25, 50, 75, 100, 150, 200, 250, 300]
):
    n = len(building_counts)

    ncols = 4
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(20, 5 * nrows))
    axes = axes.flatten()

    street_file = os.path.join(base_dir, "streets.geojson")
    streets = gpd.read_file(street_file)

    for idx, n_buildings in enumerate(building_counts):
        ax = axes[idx]
        # Lade Daten
        building_file = os.path.join(data_base_dir, f"{n_buildings}_buildings", "synthetic_buildings.geojson")
        unified_file = os.path.join(result_base_dir, f"{n_buildings}_buildings", "Wärmenetz", "Wärmenetz.geojson")

        if not (os.path.exists(street_file) and os.path.exists(building_file) and os.path.exists(unified_file)):
            ax.set_title(f"{n_buildings} Gebäude (Dateien fehlen)")
            ax.axis("off")
            continue

        from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema
        
        buildings = gpd.read_file(building_file)
        unified_geojson = NetworkGeoJSONSchema.load_from_file(unified_file)
        vorlauf, _, _, _ = NetworkGeoJSONSchema.split_to_legacy_format(unified_geojson)

        streets.plot(ax=ax, color="grey", linewidth=1, label="Straßennetz")
        buildings.plot(ax=ax, color="red", markersize=8, label="Gebäude")
        vorlauf.plot(ax=ax, color="blue", linewidth=2, label="Vorlaufnetz")

        ax.set_title(f"{n_buildings} Gebäude")
        ax.set_xlabel("UTM X [m]")
        ax.set_ylabel("UTM Y [m]")

        # set min and max limits
        ax.set_xlim(vorlauf.total_bounds[0] - 100, vorlauf.total_bounds[2] + 100)
        ax.set_ylim(vorlauf.total_bounds[1] - 100, vorlauf.total_bounds[3] + 100)

        ax.legend()

    # Leere Subplots ausblenden
    for i in range(len(building_counts), len(axes)):
        axes[i].axis("off")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    run_benchmark()
    plot_benchmark_networks()