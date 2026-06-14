"""
Filename: 18_stanet_to_pandapipes.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-21
Description: This script demonstrates how to use the `create_net_from_stanet_csv` function from the `feature_develop.stanet_import_pandapipes` module.

"""

from stanet_import_pandapipes import create_net_from_stanet_csv
import pandapipes as pp
import matplotlib.pyplot as plt
import numpy as np


def plot_net_3d(net) -> None:
    """3D network plot: X/Y = geographic coordinates, Z = elevation (GEOH, mNN)."""
    geo = net.junction_geodata
    z_arr = geo["z"].fillna(0.0).values

    fig = plt.figure(figsize=(14, 8))
    ax = fig.add_subplot(111, projection="3d")

    cmap = plt.cm.terrain
    v_min, v_max = z_arr.min(), z_arr.max()

    # --- Pipes as 3D polylines, Z interpolated linearly between junctions ---
    for _, pipe_row in net.pipe.iterrows():
        fj = pipe_row["from_junction"]
        tj = pipe_row["to_junction"]
        if fj not in geo.index or tj not in geo.index:
            continue

        if pipe_row.name in net.pipe_geodata.index:
            coords = net.pipe_geodata.at[pipe_row.name, "coords"]
            xs = [c[0] for c in coords]
            ys = [c[1] for c in coords]
        else:
            xs = [geo.at[fj, "x"], geo.at[tj, "x"]]
            ys = [geo.at[fj, "y"], geo.at[tj, "y"]]

        z_from = float(geo.at[fj, "z"])
        z_to   = float(geo.at[tj, "z"])
        zs = np.linspace(z_from, z_to, len(xs))

        ax.plot(xs, ys, zs, color="steelblue", linewidth=1.0, alpha=0.7)

    # --- Junctions coloured by elevation ---
    sc = ax.scatter(
        geo["x"], geo["y"], z_arr,
        c=z_arr, cmap=cmap, s=25, zorder=5,
        vmin=v_min, vmax=v_max,
    )
    fig.colorbar(sc, ax=ax, shrink=0.5, pad=0.1, label="Elevation (mNN)")

    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    ax.set_zlabel("Elevation (mNN)")
    ax.set_title("District heating network — elevation profile")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # Example usage
    stanet_csv_file_path = "examples/data/STANET/Example_STANET_ETRS89.CSV"
    TRY_file_path = "examples/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat"
    supply_temperature = 80  # Supply temperature in Celsius
    flow_pressure_pump = 4.0  # Flow pressure of the pump in bar
    lift_pressure_pump = 1.5  # Lift pressure of the pump in bar

    net, yearly_time_steps, total_heat_W, max_heat_requirement_W, crs_epsg = \
        create_net_from_stanet_csv(stanet_csv_file_path, TRY_file_path,
                                   supply_temperature, flow_pressure_pump, lift_pressure_pump)
    print(f"CRS: {crs_epsg}")

    if net is not None:
        plot_net_3d(net)