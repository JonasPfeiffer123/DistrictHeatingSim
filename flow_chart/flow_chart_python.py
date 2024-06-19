import matplotlib.pyplot as plt
import networkx as nx

def create_structured_flow_chart():
    G = nx.DiGraph()

    # Ausgangsdatenebene hinzufügen
    G.add_node("Ausgangsdatenebene", pos=(0, 3), shape='box')
    G.add_node("TRY-Daten", pos=(-1, 2), shape='box')
    G.add_node("COP-Daten", pos=(0, 2), shape='box')
    G.add_node("Preisdaten", pos=(1, 2), label="Gaspreis, Strompreis, Holzpreis", shape='box')
    G.add_node("Standortdaten", pos=(2, 2), shape='box')

    # Erzeugerebene hinzufügen
    G.add_node("Erzeugerebene", pos=(0, 1), shape='box')
    G.add_node("Solarthermie", pos=(-2, 0), shape='box')
    G.add_node("BHKW", pos=(-1.5, 0), shape='box')
    G.add_node("Biomassekessel", pos=(-1, 0), shape='box')
    G.add_node("Geothermie", pos=(-0.5, 0), shape='box')
    G.add_node("Abwärmepumpen", pos=(0, 0), shape='box')
    G.add_node("Flusswasserwärmepumpen", pos=(0.5, 0), shape='box')
    G.add_node("Gaskessel", pos=(1, 0), shape='box')

    # Berechnungsebene hinzufügen
    G.add_node("Berechnungsebene", pos=(0, -1), shape='box')
    G.add_node("Erzeugermix-Fkt.", pos=(0, -2), shape='box')
    G.add_node("Berechnung", pos=(0, -3), label="Berechnung der Zins- und Preissteigerungsfaktoren, Initialisierung der Ergebnisse, Iteration durch die Erzeuger, Technolog.-spezifische Berechnungen, Aktualisierung der Ergebnisse, Optimierung und Entfernen ungültiger Technologien", shape='box')

    # Optimierungsebene hinzufügen
    G.add_node("Optimierungsebene", pos=(2, -1), shape='box')
    G.add_node("Optimierungs-Fkt.", pos=(2, -2), shape='box')
    G.add_node("Optimierung", pos=(2, -3), label="Initialisierung der Variablen, Definition der Zielfunktion, Durchführung der Optimierung, Aktualisierung der Parameter", shape='box')

    # Ergebnisse hinzufügen
    G.add_node("Ergebnisse", pos=(0, -4), shape='box')
    G.add_node("Ergebnisse Details", pos=(1, -4), label="Berechnete Leistungskennzahlen, Wirtschaftlichkeitsmetriken, optimierte Parameter, Wärmemengen, WGK, CO2-Emissionen", shape='box')

    # Kanten hinzufügen
    G.add_edge("Ausgangsdatenebene", "TRY-Daten")
    G.add_edge("Ausgangsdatenebene", "COP-Daten")
    G.add_edge("Ausgangsdatenebene", "Preisdaten")
    G.add_edge("Ausgangsdatenebene", "Standortdaten")

    G.add_edge("Erzeugerebene", "Solarthermie")
    G.add_edge("Erzeugerebene", "BHKW")
    G.add_edge("Erzeugerebene", "Biomassekessel")
    G.add_edge("Erzeugerebene", "Geothermie")
    G.add_edge("Erzeugerebene", "Abwärmepumpen")
    G.add_edge("Erzeugerebene", "Flusswasserwärmepumpen")
    G.add_edge("Erzeugerebene", "Gaskessel")

    G.add_edge("Solarthermie", "Erzeugermix-Fkt.")
    G.add_edge("BHKW", "Erzeugermix-Fkt.")
    G.add_edge("Biomassekessel", "Erzeugermix-Fkt.")
    G.add_edge("Geothermie", "Erzeugermix-Fkt.")
    G.add_edge("Abwärmepumpen", "Erzeugermix-Fkt.")
    G.add_edge("Flusswasserwärmepumpen", "Erzeugermix-Fkt.")
    G.add_edge("Gaskessel", "Erzeugermix-Fkt.")

    G.add_edge("Erzeugermix-Fkt.", "Berechnungsebene")
    G.add_edge("Berechnungsebene", "Berechnung")

    G.add_edge("Optimierungsebene", "Optimierungs-Fkt.")
    G.add_edge("Optimierungs-Fkt.", "Optimierung")

    G.add_edge("Berechnung", "Ergebnisse")
    G.add_edge("Optimierung", "Ergebnisse")

    G.add_edge("Ergebnisse", "Ergebnisse Details")

    pos = nx.get_node_attributes(G, 'pos')
    labels = nx.get_node_attributes(G, 'label')

    plt.figure(figsize=(20, 15))
    nx.draw(G, pos, with_labels=True, labels=labels, node_shape='s', node_color='lightblue', node_size=5000, font_size=10, font_weight='bold', arrows=True)
    plt.title('Strukturiertes Erzeugermix Flussdiagramm')
    plt.show()

create_structured_flow_chart()
