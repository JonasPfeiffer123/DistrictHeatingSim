import matplotlib.pyplot as plt
import networkx as nx

def draw_graph():
    G = nx.read_graphml("districtheatsim\\project_data\\Bad Muskau\\results\\graph.graphml")
    pos = {node: (node[0], node[1]) for node in G.nodes()}  # Annahme: Knoten sind (x, y)-Koordinaten
    nx.draw(G, pos, node_size=50, with_labels=True, node_color='lightblue')
    plt.show()

draw_graph()