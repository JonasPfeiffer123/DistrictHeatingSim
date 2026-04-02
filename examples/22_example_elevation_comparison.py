"""
22_example_elevation_comparison.py
====================================
Demonstration: Höhendaten-Einfluss auf Druckberechnung in pandapipes
=====================================================================

Dieses Beispiel zeigt anhand eines synthetischen Hügelnetzes den Unterschied
zwischen einer Simulation **ohne** und **mit** Höhendaten.  In Fernwärmenetzen
mit nennenswerten Höhenunterschieden liefert eine flache Rechnung (height_m=0)
systematisch falsche Drücke – dieses Skript macht den Fehler quantifizierbar.

Netz-Topologie (Längsschnitt)::

    Elevation
    [m NN]
     215 ┤                 S2/R2 (Schlechtpunkt)
     205 ┤                              S3/R3
     195 ┤          S1/R1                      S4/R4
     180 ┤ S0/R0 (Erzeuger)
              |── 100 m ──|── 100 m ──|── 100 m ──|── 100 m ──|
           x=0          x=100       x=200       x=300       x=400

    Vorlauf:  S0 ──────► S1 ──────► S2 ──────► S3 ──────► S4
    Rücklauf: R0 ◄────── R1 ◄────── R2 ◄────── R3 ◄────── R4
    Verbraucher: (S1,R1), (S2,R2), (S3,R3), (S4,R4)
    Pumpe:    R0 → S0  (Druckgeregelt)

Erzeugte Plots:
    1. Druckdiagramm (Absolutdruck VL/RL entlang des Netzes)
    2. Piezometrische Drucklinie (Energielinie gegen Geländeprofil)
    3. Differenzdruck VL-RL je Verbraucher
    4. Mindestdrucknachweis (Abstand zum Mindestdruck)

Autor: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import sys
import io

# Ensure UTF-8 output on Windows consoles (colorama/cp1252 workaround)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandapipes as pp

# ---------------------------------------------------------------------------
# Netzparameter
# ---------------------------------------------------------------------------
SUPPLY_TEMP_K   = 80 + 273.15   # Vorlauftemperatur [K]
RETURN_TEMP_K   = 60 + 273.15   # Rücklauftemperatur [K]
P_FLOW_BAR      = 10.0          # Druck am Pumpenauslass (Vorlauf) [bar]
P_LIFT_BAR      = 6.0           # Pumpenhebedruckdifferenz [bar]
PIPE_DIAMETER_M = 0.1022        # Innendurchmesser DN100 [m]
PIPE_K_MM       = 0.1           # Rohrrauhigkeit [mm]
U_W_PER_M2K     = 0.5           # Wärmedurchgangskoeffizient Rohr [W/(m²K)]
TEXT_K          = 283.15        # Erdreichtemperatur [K] (10 °C)
PIPE_LENGTH_KM  = 0.1           # Rohrsegmentlänge [km]
SECTIONS        = 5             # Diskretisierungsabschnitte je Rohr
QEXT_W          = [40_000,      # Wärmeleistung Verbraucher 1 [W]
                   50_000,      # Verbraucher 2 – Schlechtpunkt
                   35_000,      # Verbraucher 3
                   25_000]      # Verbraucher 4
P_MIN_BAR       = 0.5           # Mindest-Betriebsdruck [bar]

# Lagekoordinaten für Knoten [m]
X_POSITIONS   = [0, 100, 200, 300, 400]
ELEVATIONS_M  = [180, 195, 215, 205, 190]   # [m NN]
NODE_LABELS   = ["Erzeuger\n(S0/R0)", "Abnahme 1\n(S1/R1)",
                 "Abnahme 2\n(S2/R2)\n(Schlechtpunkt)", "Abnahme 3\n(S3/R3)",
                 "Abnahme 4\n(S4/R4)"]
CONSUMER_LABELS = ["HC 1\n(195 m)", "HC 2\n(215 m)\n[SP]",
                   "HC 3\n(205 m)", "HC 4\n(190 m)"]

RHO_WATER = 1000.0   # kg/m³ (bei ~70 °C leicht geringer – vereinfacht)
G         = 9.81     # m/s²
BAR_TO_M  = 1e5 / (RHO_WATER * G)   # Umrechnungsfaktor bar → m Wassersäule


# ---------------------------------------------------------------------------
# Netzaufbau
# ---------------------------------------------------------------------------
def build_network(with_elevation: bool) -> pp.pandapipesNet:
    """Erstellt ein pandapipes-Fernwärmenetz.

    :param with_elevation: Wenn ``True``, erhalten Junctions die realen
                           Geländehöhen als ``height_m``.  Andernfalls
                           ``height_m=0`` (flache Rechnung).
    :returns: Gelöstes pandapipesNet-Objekt
    """
    net = pp.create_empty_network(fluid="water")

    heights = ELEVATIONS_M if with_elevation else [0] * len(ELEVATIONS_M)

    # --- Vorlauf-Junctions S0 … S4 -----------------------------------------
    s_junctions = []
    for i, (x, z) in enumerate(zip(X_POSITIONS, heights)):
        jid = pp.create_junction(
            net, pn_bar=P_FLOW_BAR, tfluid_k=SUPPLY_TEMP_K,
            height_m=z, name=f"S{i}",
            geodata=(x, 2)   # y=2 für Plot-Versatz VL
        )
        s_junctions.append(jid)

    # --- Rücklauf-Junctions R0 … R4 ----------------------------------------
    r_junctions = []
    for i, (x, z) in enumerate(zip(X_POSITIONS, heights)):
        jid = pp.create_junction(
            net, pn_bar=P_FLOW_BAR - P_LIFT_BAR, tfluid_k=RETURN_TEMP_K,
            height_m=z, name=f"R{i}",
            geodata=(x, -2)  # y=-2 für Plot-Versatz RL
        )
        r_junctions.append(jid)

    # --- Vorlauf-Rohre S0→S1→S2→S3→S4 ------------------------------------
    for i in range(4):
        pp.create_pipe_from_parameters(
            net,
            from_junction=s_junctions[i],
            to_junction=s_junctions[i + 1],
            length_km=PIPE_LENGTH_KM,
            diameter_m=PIPE_DIAMETER_M,
            k_mm=PIPE_K_MM,
            u_w_per_m2k=U_W_PER_M2K,
            text_k=TEXT_K,
            sections=SECTIONS,
            name=f"VL-Rohr {i+1}"
        )

    # --- Rücklauf-Rohre R4→R3→R2→R1→R0 -----------------------------------
    for i in range(4, 0, -1):
        pp.create_pipe_from_parameters(
            net,
            from_junction=r_junctions[i],
            to_junction=r_junctions[i - 1],
            length_km=PIPE_LENGTH_KM,
            diameter_m=PIPE_DIAMETER_M,
            k_mm=PIPE_K_MM,
            u_w_per_m2k=U_W_PER_M2K,
            text_k=TEXT_K,
            sections=SECTIONS,
            name=f"RL-Rohr {i}"
        )

    # --- Wärmeverbraucher HC1 … HC4 ----------------------------------------
    for i, q_w in enumerate(QEXT_W, start=1):
        pp.create_heat_consumer(
            net,
            from_junction=s_junctions[i],
            to_junction=r_junctions[i],
            qext_w=q_w,
            treturn_k=RETURN_TEMP_K,
            name=f"HC {i}"
        )

    # --- Umwälzpumpe (druckgeregelt) an R0 → S0 ---------------------------
    pp.create_circ_pump_const_pressure(
        net,
        return_junction=r_junctions[0],
        flow_junction=s_junctions[0],
        p_flow_bar=P_FLOW_BAR,
        plift_bar=P_LIFT_BAR,
        t_flow_k=SUPPLY_TEMP_K,
        type="auto",
        name="Hauptpumpe"
    )

    # --- Berechnung --------------------------------------------------------
    pp.pipeflow(net, mode="bidirectional", iter=100)
    return net


# ---------------------------------------------------------------------------
# Ergebnisse extrahieren
# ---------------------------------------------------------------------------
def extract_results(net: pp.pandapipesNet):
    """Liest Drücke aus dem gelösten Netz aus.

    :returns: Dict mit ``p_vl``, ``p_rl``, ``dp_consumer``
    """
    p_vl = [net.res_junction.at[j, "p_bar"]
            for j in range(5)]             # S0 … S4
    p_rl = [net.res_junction.at[j, "p_bar"]
            for j in range(5, 10)]         # R0 … R4

    # Differenzdruck VL-RL an Verbrauchern (Junctions S1-S4 und R1-R4)
    dp_consumer = [p_vl[i] - p_rl[i] for i in range(1, 5)]

    return {"p_vl": p_vl, "p_rl": p_rl, "dp_consumer": dp_consumer}


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
COLOR_FLAT  = "#2196F3"   # Blau  – flache Rechnung
COLOR_ELEV  = "#E65100"   # Orange – mit Höhendaten
COLOR_VL    = "#D32F2F"   # Rot   – Vorlauf
COLOR_RL    = "#1565C0"   # Blau  – Rücklauf
COLOR_TERRAIN = "#8D6E63" # Braun – Gelände

def plot_all(net_flat, net_elev):
    """Erzeugt alle vier Vergleichsplots in einem Figure-Objekt."""
    res_flat = extract_results(net_flat)
    res_elev = extract_results(net_elev)

    x       = np.array(X_POSITIONS)
    z_m     = np.array(ELEVATIONS_M)
    x_cons  = x[1:]    # Verbraucher-Positionen

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle(
        "Höhendaten-Einfluss auf die Druckberechnung im Fernwärmenetz\n"
        f"Geländerelief: {min(ELEVATIONS_M)}–{max(ELEVATIONS_M)} m NN  |  "
        f"Δh = {max(ELEVATIONS_M) - min(ELEVATIONS_M)} m  |  "
        f"Δp_hydro ≈ {RHO_WATER * G * (max(ELEVATIONS_M)-min(ELEVATIONS_M)) / 1e5:.2f} bar",
        fontsize=13, fontweight="bold", y=0.98
    )

    # -----------------------------------------------------------------------
    # Plot 1: Druckdiagramm (Absolutdruck VL / RL)
    # -----------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1_twin = ax1.twinx()

    # Geländeprofil als Hintergrund
    ax1_twin.fill_between(x, 0, z_m, alpha=0.15, color=COLOR_TERRAIN, label="Gelände")
    ax1_twin.plot(x, z_m, color=COLOR_TERRAIN, linewidth=1.5, linestyle="--")
    ax1_twin.set_ylabel("Geländehöhe [m NN]", color=COLOR_TERRAIN)
    ax1_twin.tick_params(axis="y", labelcolor=COLOR_TERRAIN)
    ax1_twin.set_ylim(100, 280)

    # Drucklinien
    ax1.plot(x, res_flat["p_vl"], "o--", color=COLOR_VL,   alpha=0.5, linewidth=1.5,
             label="VL – ohne Höhe")
    ax1.plot(x, res_flat["p_rl"], "s--", color=COLOR_RL,   alpha=0.5, linewidth=1.5,
             label="RL – ohne Höhe")
    ax1.plot(x, res_elev["p_vl"], "o-",  color=COLOR_VL,   linewidth=2.5,
             label="VL – mit Höhe")
    ax1.plot(x, res_elev["p_rl"], "s-",  color=COLOR_RL,   linewidth=2.5,
             label="RL – mit Höhe")

    # Mindestdruck markieren
    ax1.axhline(P_MIN_BAR, color="red", linestyle=":", linewidth=1.5,
                label=f"p_min = {P_MIN_BAR} bar")

    ax1.set_xlabel("Position im Netz [m]")
    ax1.set_ylabel("Druck [bar]")
    ax1.set_title("① Drucklinienverlauf VL / RL")
    ax1.legend(loc="lower left", fontsize=8)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"x={xi}" for xi in x], rotation=15, fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax1.set_zorder(ax1_twin.get_zorder() + 1)
    ax1.patch.set_visible(False)

    # Schlechtpunkt annotieren
    sp_x, sp_p = x[2], res_elev["p_rl"][2]
    ax1.annotate(f"Schlechtpunkt\nRL: {sp_p:.2f} bar",
                 xy=(sp_x, sp_p), xytext=(sp_x + 30, sp_p + 0.8),
                 arrowprops=dict(arrowstyle="->", color="black"),
                 fontsize=8, color="black")

    # -----------------------------------------------------------------------
    # Plot 2: Piezometrische Druckhöhe (Energielinie)
    # -----------------------------------------------------------------------
    ax2 = axes[0, 1]

    def piezometric_head(p_bar, z_m):
        """Piezometrische Druckhöhe h = p/(ρg) + z [m]."""
        return np.array(p_bar) * BAR_TO_M + np.array(z_m)

    h_vl_flat = piezometric_head(res_flat["p_vl"], z_m)
    h_rl_flat = piezometric_head(res_flat["p_rl"], z_m)
    h_vl_elev = piezometric_head(res_elev["p_vl"], z_m)
    h_rl_elev = piezometric_head(res_elev["p_rl"], z_m)

    # Geländeprofil
    ax2.fill_between(x, 0, z_m, alpha=0.25, color=COLOR_TERRAIN, label="Gelände [m NN]")
    ax2.plot(x, z_m, color=COLOR_TERRAIN, linewidth=1.5, linestyle="--")

    ax2.plot(x, h_vl_flat, "o--", color=COLOR_VL, alpha=0.5, linewidth=1.5,
             label="VL – ohne Höhe")
    ax2.plot(x, h_rl_flat, "s--", color=COLOR_RL, alpha=0.5, linewidth=1.5,
             label="RL – ohne Höhe")
    ax2.plot(x, h_vl_elev, "o-",  color=COLOR_VL, linewidth=2.5,
             label="VL – mit Höhe")
    ax2.plot(x, h_rl_elev, "s-",  color=COLOR_RL, linewidth=2.5,
             label="RL – mit Höhe")

    # Bereich zwischen VL und RL (verfügbare Druckhöhe)
    ax2.fill_between(x, h_rl_elev, h_vl_elev, alpha=0.1, color="green",
                     label="Verfügbare Druckhöhe (mit Höhe)")

    ax2.set_xlabel("Position im Netz [m]")
    ax2.set_ylabel("Piezometrische Druckhöhe [m]")
    ax2.set_title("② Piezometrische Drucklinie (Energielinie)")
    ax2.legend(loc="upper right", fontsize=8)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"x={xi}" for xi in x], rotation=15, fontsize=8)
    ax2.grid(True, alpha=0.3)

    # -----------------------------------------------------------------------
    # Plot 3: Differenzdruck VL-RL je Verbraucher
    # -----------------------------------------------------------------------
    ax3 = axes[1, 0]

    bar_w = 30
    x_cons_flat = x_cons - bar_w / 2
    x_cons_elev = x_cons + bar_w / 2

    bars_flat = ax3.bar(x_cons_flat, res_flat["dp_consumer"], width=bar_w,
                        color=COLOR_FLAT, alpha=0.8, label="Ohne Höhendaten")
    bars_elev = ax3.bar(x_cons_elev, res_elev["dp_consumer"], width=bar_w,
                        color=COLOR_ELEV, alpha=0.8, label="Mit Höhendaten")

    # Wertebeschriftung
    for bar, val in zip(bars_flat, res_flat["dp_consumer"]):
        ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=8,
                 color=COLOR_FLAT, fontweight="bold")
    for bar, val in zip(bars_elev, res_elev["dp_consumer"]):
        ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=8,
                 color=COLOR_ELEV, fontweight="bold")

    ax3.set_xlabel("Position im Netz [m]")
    ax3.set_ylabel("Differenzdruck Δp_VL–RL [bar]")
    ax3.set_title("③ Verfügbarer Differenzdruck je Verbraucher")
    ax3.set_xticks(x_cons)
    ax3.set_xticklabels(CONSUMER_LABELS, fontsize=8)
    ax3.legend()
    ax3.axhline(0, color="red", linewidth=1.5, linestyle=":")
    ax3.grid(True, axis="y", alpha=0.3)

    # Differenz-Pfeile zwischen den Balken
    for xf, xe, vf, ve in zip(x_cons_flat, x_cons_elev,
                                res_flat["dp_consumer"], res_elev["dp_consumer"]):
        diff = ve - vf
        mid_x = (xf + xe) / 2
        ax3.annotate("", xy=(mid_x, ve), xytext=(mid_x, vf),
                     arrowprops=dict(arrowstyle="<->", color="gray", lw=1.5))
        ax3.text(mid_x + 12, (vf + ve) / 2, f"Δ={diff:+.2f}",
                 va="center", fontsize=7, color="gray")

    # -----------------------------------------------------------------------
    # Plot 4: Mindestdrucknachweis (Druckreserve)
    # -----------------------------------------------------------------------
    ax4 = axes[1, 1]

    # Druckreserve = p_junction - P_MIN_BAR
    all_labels = [f"S{i}\n({ELEVATIONS_M[i]} m)" for i in range(5)] + \
                 [f"R{i}\n({ELEVATIONS_M[i]} m)" for i in range(5)]

    reserve_flat = ([p - P_MIN_BAR for p in res_flat["p_vl"]] +
                    [p - P_MIN_BAR for p in res_flat["p_rl"]])
    reserve_elev = ([p - P_MIN_BAR for p in res_elev["p_vl"]] +
                    [p - P_MIN_BAR for p in res_elev["p_rl"]])

    x_idx = np.arange(10)
    ax4.bar(x_idx - 0.2, reserve_flat, 0.4, color=COLOR_FLAT, alpha=0.8,
            label="Ohne Höhendaten")
    ax4.bar(x_idx + 0.2, reserve_elev, 0.4, color=COLOR_ELEV, alpha=0.8,
            label="Mit Höhendaten")

    ax4.axhline(0, color="red", linewidth=2, linestyle="-",
                label=f"Mindestdruck p_min = {P_MIN_BAR} bar")

    # Kritische Knoten markieren
    for i, (rv, re) in enumerate(zip(reserve_flat, reserve_elev)):
        if re < 0.5:
            ax4.annotate(f"(!) {P_MIN_BAR + re:.2f} bar",
                         xy=(i + 0.2, re), xytext=(i + 0.5, re + 0.3),
                         arrowprops=dict(arrowstyle="->", color=COLOR_ELEV),
                         fontsize=7.5, color=COLOR_ELEV)

    ax4.set_xticks(x_idx)
    ax4.set_xticklabels(all_labels, fontsize=8, rotation=20)
    ax4.set_xlabel("Junction (VL: S0–S4 | RL: R0–R4)")
    ax4.set_ylabel(f"Druckreserve über p_min = {P_MIN_BAR} bar [bar]")
    ax4.set_title("④ Mindestdrucknachweis je Junction")
    ax4.legend(fontsize=9)
    ax4.grid(True, axis="y", alpha=0.3)

    # VL / RL Bereiche markieren
    ax4.axvspan(-0.5, 4.5, alpha=0.04, color="red",   label="Vorlauf")
    ax4.axvspan(4.5, 9.5,  alpha=0.04, color="blue",  label="Rücklauf")
    ax4.text(2,  ax4.get_ylim()[1] * 0.95, "Vorlauf",  ha="center",
             fontsize=9, color="darkred", alpha=0.7)
    ax4.text(7,  ax4.get_ylim()[1] * 0.95, "Rücklauf", ha="center",
             fontsize=9, color="navy", alpha=0.7)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig


# ---------------------------------------------------------------------------
# Konsolenausgabe
# ---------------------------------------------------------------------------
def print_summary(net_flat, net_elev):
    res_flat = extract_results(net_flat)
    res_elev = extract_results(net_elev)

    print("\n" + "=" * 70)
    print("  VERGLEICH: FLACHE vs. HÖHENKORRIGIERTE BERECHNUNG")
    print("=" * 70)
    print(f"  Pumpendruck:  p_VL = {P_FLOW_BAR} bar  |  dp_Pumpe = {P_LIFT_BAR} bar")
    print(f"  -> p_RL (Pumpe) = {P_FLOW_BAR - P_LIFT_BAR} bar")
    print(f"  Hoehenrelief: {min(ELEVATIONS_M)}-{max(ELEVATIONS_M)} m NN  "
          f"-> dh = {max(ELEVATIONS_M)-min(ELEVATIONS_M)} m  "
          f"-> dp_hydro ~ {RHO_WATER*G*(max(ELEVATIONS_M)-min(ELEVATIONS_M))/1e5:.2f} bar")
    print()

    header = f"{'Knoten':<8} {'z [m]':>7} | {'Flach VL':>10} {'Elev. VL':>10} "
    header += f"| {'Flach RL':>10} {'Elev. RL':>10}"
    print(header)
    print("-" * len(header))

    node_names = ["S0/R0", "S1/R1", "S2/R2", "S3/R3", "S4/R4"]
    for i, (name, z) in enumerate(zip(node_names, ELEVATIONS_M)):
        row = (f"{name:<8} {z:>7.0f} | "
               f"{res_flat['p_vl'][i]:>10.3f} {res_elev['p_vl'][i]:>10.3f} | "
               f"{res_flat['p_rl'][i]:>10.3f} {res_elev['p_rl'][i]:>10.3f}")
        # Warnung bei kritischen Drücken
        if res_elev['p_rl'][i] < P_MIN_BAR + 0.5:
            row += "  (!)"
        print(row)

    print()
    print(f"{'Verbraucher':<12} {'z [m]':>7} | {'ΔP flach':>10} {'ΔP elev.':>10} {'Fehler':>10}")
    print("-" * 56)
    for i, (label, z) in enumerate(zip(CONSUMER_LABELS, ELEVATIONS_M[1:])):
        err = res_elev["dp_consumer"][i] - res_flat["dp_consumer"][i]
        print(f"HC {i+1:<8} {z:>7.0f} | "
              f"{res_flat['dp_consumer'][i]:>10.3f} "
              f"{res_elev['dp_consumer'][i]:>10.3f} "
              f"{err:>+10.3f}")

    # Schlechtpunkt
    sp_idx    = np.argmin(res_elev["dp_consumer"])
    sp_dp     = res_elev["dp_consumer"][sp_idx]
    sp_dp_f   = res_flat["dp_consumer"][sp_idx]
    sp_rl_min = min(res_elev["p_rl"])
    print(f"\n  Schlechtpunkt: HC {sp_idx+1}  |  "
          f"dp (mit Hoehe) = {sp_dp:.3f} bar  |  "
          f"dp (ohne Hoehe) = {sp_dp_f:.3f} bar  |  Fehler = {sp_dp-sp_dp_f:+.3f} bar")
    print(f"  Niedrigster RL-Druck (mit Hoehe): {sp_rl_min:.3f} bar "
          f"(Reserve: {sp_rl_min - P_MIN_BAR:+.3f} bar)")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os

    print("Simuliere Netz ohne Höhendaten (height_m=0) …")
    net_flat = build_network(with_elevation=False)

    print("Simuliere Netz mit Höhendaten …")
    net_elev = build_network(with_elevation=True)

    print_summary(net_flat, net_elev)

    fig = plot_all(net_flat, net_elev)

    # Figur speichern
    script_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd()
    out_dir = os.path.join(script_dir, "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "22_elevation_comparison.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\nPlot gespeichert: {out_path}")

    plt.show()
