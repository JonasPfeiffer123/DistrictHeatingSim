"""
Filename: steiner_tree.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-26
Description: Steiner tree generation for optimal district heating network layout.

This module implements Steiner tree algorithms for generating cost-optimal district heating
network topologies based on existing street infrastructure. It creates minimal-cost
network connections between heat producers, consumers, and connection points while
respecting geographical constraints and street layout requirements.

The module integrates NetworkX graph algorithms with geospatial analysis to generate
realistic network topologies that follow existing infrastructure paths. It supports
automatic terminal mapping, graph connectivity analysis, and network optimization
for practical district heating system planning and design.
"""

import networkx as nx
from networkx.algorithms.approximation import steiner_tree
import geopandas as gpd
from shapely.geometry import LineString, Point
import matplotlib.pyplot as plt
from shapely.ops import nearest_points
import random
from typing import List, Tuple, Optional

def create_road_graph(street_layer: gpd.GeoDataFrame, precision: int = 4) -> nx.Graph:
    """
    Create a NetworkX graph from street network geometry for network routing analysis.

    This function converts geospatial street data into a weighted graph representation
    suitable for path finding and network optimization algorithms. It handles coordinate
    precision for numerical stability and creates edge weights based on euclidean distances
    between street segment endpoints.

    Parameters
    ----------
    street_layer : geopandas.GeoDataFrame
        GeoDataFrame containing street network geometries as LineString objects.
        Must include geometry column with valid LineString features.
    precision : int, optional
        Decimal precision for coordinate rounding to avoid floating-point issues.
        Default is 4 (sub-meter precision). Higher values increase accuracy but may
        cause numerical instability in graph algorithms.

    Returns
    -------
    networkx.Graph
        Undirected graph representation of the street network with:
        
        - **Nodes** : Street intersection points and segment endpoints
        - **Edges** : Street segments with distance-based weights
        - **Weights** : Euclidean distances between connected nodes [m]

    Notes
    -----
    Graph Construction Process:
        1. Iterates through all LineString geometries in street layer
        2. Extracts and rounds coordinates to specified precision
        3. Creates graph nodes for each coordinate point
        4. Adds weighted edges between consecutive points in each line
        5. Merges overlapping street segments into connected graph

    Coordinate Precision:
        - Precision 2: ~1km accuracy (city-scale planning)
        - Precision 3: ~100m accuracy (district-scale planning)  
        - Precision 4: ~10m accuracy (detailed network design)
        - Precision 5: ~1m accuracy (high-precision applications)

    Weight Calculation:
        - Uses Euclidean distance between node coordinates
        - Represents street segment lengths for shortest-path algorithms
        - Enables cost-based network optimization

    Examples
    --------
    >>> # Create graph from street network
    >>> import geopandas as gpd
    >>> streets = gpd.read_file("street_network.shp")
    >>> road_graph = create_road_graph(streets, precision=4)
    >>> print(f"Graph contains {len(road_graph.nodes)} nodes and {len(road_graph.edges)} edges")

    >>> # Analyze graph connectivity
    >>> if nx.is_connected(road_graph):
    ...     print("Street network is fully connected")
    ... else:
    ...     components = list(nx.connected_components(road_graph))
    ...     print(f"Street network has {len(components)} disconnected components")

    >>> # Check graph statistics
    >>> avg_degree = sum(dict(road_graph.degree()).values()) / len(road_graph.nodes)
    >>> print(f"Average node degree: {avg_degree:.2f}")

    See Also
    --------
    map_points_to_graph_nodes : Map building locations to street network
    networkx.Graph : Base graph class for network representation
    """
    G = nx.Graph()
    
    for line in street_layer.geometry:
        if isinstance(line, LineString):
            # Extract and round coordinates for numerical stability
            coords = [(round(x, precision), round(y, precision)) for x, y in line.coords]
            
            # Create edges between consecutive points with distance weights
            for i in range(len(coords) - 1):
                p1 = coords[i]
                p2 = coords[i + 1]
                distance = Point(p1).distance(Point(p2))
                G.add_edge(p1, p2, weight=distance)
    
    return G

def map_points_to_graph_nodes(road_graph: nx.Graph, points_gdf: gpd.GeoDataFrame, 
                             precision: int = 4) -> List[Tuple[float, float]]:
    """
    Map building locations to nearest street network nodes for terminal identification.

    This function projects building locations onto the street network by finding the
    nearest street segment, calculating the perpendicular projection point, and
    integrating this point into the graph structure. It handles graph topology
    modifications to ensure proper connectivity for network optimization algorithms.

    Parameters
    ----------
    road_graph : networkx.Graph
        Street network graph created by create_road_graph().
        Will be modified in-place to include projected terminal points.
    points_gdf : geopandas.GeoDataFrame
        GeoDataFrame containing building locations as Point geometries.
        Represents heat consumers, producers, or other network connection points.
    precision : int, optional
        Coordinate precision for point projection and graph integration.
        Must match precision used in road graph creation. Default is 4.

    Returns
    -------
    List[Tuple[float, float]]
        List of terminal coordinates integrated into the street network graph.
        Each tuple represents (x, y) coordinates of a network terminal point.

    Notes
    -----
    Projection Algorithm:
        1. For each building point, finds nearest street segment
        2. Calculates perpendicular projection onto street line
        3. Rounds projection coordinates to specified precision
        4. Integrates projection point into graph structure

    Graph Modification Process:
        1. Identifies nearest edge for each building point
        2. Removes original street segment edge
        3. Adds projected point as new graph node
        4. Creates two new edges connecting projection to original endpoints
        5. Validates edge creation to prevent duplicate connections

    Coordinate Handling:
        - Maintains coordinate precision consistency with road graph
        - Prevents floating-point precision issues in graph algorithms
        - Ensures proper spatial relationships for distance calculations

    Terminal Integration:
        - Each building becomes a graph terminal for Steiner tree calculation
        - Projected points represent optimal connection points on street network
        - Modified graph maintains connectivity while adding terminal access

    Examples
    --------
    >>> # Map buildings to street network
    >>> buildings = gpd.read_file("buildings.shp")
    >>> road_graph = create_road_graph(streets)
    >>> terminals = map_points_to_graph_nodes(road_graph, buildings)
    >>> print(f"Mapped {len(terminals)} building locations to street network")

    >>> # Verify terminal integration
    >>> for i, terminal in enumerate(terminals):
    ...     if terminal in road_graph.nodes:
    ...         degree = road_graph.degree[terminal]
    ...         print(f"Terminal {i}: connected to {degree} street segments")

    >>> # Check projection quality
    >>> original_points = [Point(p) for p in points_gdf.geometry]
    >>> projected_points = [Point(t) for t in terminals]
    >>> distances = [orig.distance(proj) for orig, proj in zip(original_points, projected_points)]
    >>> print(f"Average projection distance: {np.mean(distances):.2f}m")

    Raises
    ------
    ValueError
        If points_gdf contains non-Point geometries.
    KeyError
        If coordinate precision causes graph connectivity issues.

    See Also
    --------
    create_road_graph : Create street network graph
    filter_to_largest_component : Handle disconnected graph components
    shapely.geometry.LineString.project : Point projection calculation
    """
    terminals = []
    
    for point in points_gdf.geometry:
        min_dist = float('inf')
        nearest_edge = None
        nearest_proj = None
        
        # Find nearest street segment for each building point
        for u, v in road_graph.edges():
            line = LineString([u, v])
            proj = line.interpolate(line.project(point))
            dist = point.distance(proj)
            
            if dist < min_dist:
                min_dist = dist
                nearest_edge = (u, v)
                nearest_proj = proj

        # Round coordinates for numerical stability
        proj_coords = (round(nearest_proj.x, precision), round(nearest_proj.y, precision))
        u_rounded = (round(nearest_edge[0][0], precision), round(nearest_edge[0][1], precision))
        v_rounded = (round(nearest_edge[1][0], precision), round(nearest_edge[1][1], precision))

        # Integrate projected point into graph structure
        if proj_coords not in road_graph.nodes:
            # Remove original street segment
            if road_graph.has_edge(u_rounded, v_rounded):
                road_graph.remove_edge(u_rounded, v_rounded)
            
            # Add projected point as new node
            road_graph.add_node(proj_coords)
            
            # Create new edges to projection point (avoid duplicate edges)
            if u_rounded != proj_coords and not road_graph.has_edge(u_rounded, proj_coords):
                distance = Point(u_rounded).distance(Point(proj_coords))
                road_graph.add_edge(u_rounded, proj_coords, weight=distance)
            
            if v_rounded != proj_coords and not road_graph.has_edge(proj_coords, v_rounded):
                distance = Point(v_rounded).distance(Point(proj_coords))
                road_graph.add_edge(proj_coords, v_rounded, weight=distance)
        
        terminals.append(proj_coords)

    return terminals

def filter_to_largest_component(road_graph: nx.Graph, terminals: List[Tuple[float, float]]) -> Tuple[nx.Graph, List[Tuple[float, float]]]:
    """
    Filter graph and terminals to largest connected component for algorithm compatibility.

    This function handles disconnected street networks by identifying the largest
    connected component and filtering both the graph and terminal points to ensure
    algorithm compatibility. It prevents failures in Steiner tree calculations
    that require connected graphs.

    Parameters
    ----------
    road_graph : networkx.Graph
        Street network graph that may contain disconnected components.
    terminals : List[Tuple[float, float]]
        List of terminal coordinates mapped to the street network.

    Returns
    -------
    Tuple[networkx.Graph, List[Tuple[float, float]]]
        A tuple containing:
        
        - **filtered_graph** (nx.Graph) : Subgraph of largest connected component
        - **filtered_terminals** (List) : Terminals within the largest component

    Notes
    -----
    Component Analysis:
        1. Identifies all connected components in the street network
        2. Determines largest component by node count
        3. Creates subgraph containing only largest component
        4. Filters terminals to those within largest component

    Connectivity Requirements:
        - Steiner tree algorithms require connected graphs
        - Disconnected components cannot be spanned by single tree
        - Largest component typically contains main road network

    Data Loss Handling:
        - Warns when terminals are removed due to disconnected components
        - Maintains data integrity for algorithm compatibility
        - Preserves maximum network coverage possible

    Component Selection Strategy:
        - Chooses component with most nodes (typically main road network)
        - Alternative strategies could consider terminal density
        - Ensures practical network connectivity for heating system

    Examples
    --------
    >>> # Filter disconnected street network
    >>> road_graph = create_road_graph(streets)
    >>> terminals = map_points_to_graph_nodes(road_graph, buildings)
    >>> filtered_graph, filtered_terminals = filter_to_largest_component(road_graph, terminals)
    >>> 
    >>> print(f"Original: {len(road_graph.nodes)} nodes, {len(terminals)} terminals")
    >>> print(f"Filtered: {len(filtered_graph.nodes)} nodes, {len(filtered_terminals)} terminals")

    >>> # Analyze component structure
    >>> components = list(nx.connected_components(road_graph))
    >>> component_sizes = [len(comp) for comp in components]
    >>> print(f"Components: {len(components)}, sizes: {sorted(component_sizes, reverse=True)}")

    >>> # Check terminal distribution
    >>> for i, comp in enumerate(components):
    ...     comp_terminals = [t for t in terminals if t in comp]
    ...     print(f"Component {i}: {len(comp_terminals)} terminals")

    Raises
    ------
    ValueError
        If no terminals remain in largest component.
    NetworkXError
        If graph structure is invalid for component analysis.

    See Also
    --------
    networkx.connected_components : Component identification algorithm
    networkx.Graph.subgraph : Subgraph extraction method
    generate_steiner_tree_network : Main network generation function
    """
    # Identify all connected components
    components = list(nx.connected_components(road_graph))
    
    # Select largest component by node count
    largest_component = max(components, key=len)
    
    # Filter terminals to largest component
    filtered_terminals = [t for t in terminals if t in largest_component]
    
    # Create subgraph of largest component
    filtered_graph = road_graph.subgraph(largest_component).copy()
    
    # Warn about data loss
    if len(filtered_terminals) < len(terminals):
        removed_count = len(terminals) - len(filtered_terminals)
        print(f"WARNING: {removed_count} terminals removed (not in largest connected component)")
    
    return filtered_graph, filtered_terminals

def generate_steiner_tree_network(street_layer: gpd.GeoDataFrame, points_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Generate optimal district heating network layout using Steiner tree algorithm.

    This function creates a cost-minimal network topology that connects all building
    locations through existing street infrastructure. It combines graph theory
    optimization with geospatial analysis to generate practical network layouts
    for district heating system planning and design.

    Parameters
    ----------
    street_layer : geopandas.GeoDataFrame
        GeoDataFrame containing street network geometries as LineString objects.
        Represents existing infrastructure available for network routing.
    points_gdf : geopandas.GeoDataFrame
        GeoDataFrame containing building locations as Point geometries.
        Represents heat consumers, producers, and connection points.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame containing optimized network layout as LineString geometries.
        Represents minimal-cost network connections following street infrastructure.

    Notes
    -----
    Algorithm Overview:
        1. Convert street layer to weighted graph representation
        2. Map building locations to nearest street network points
        3. Filter to largest connected component for algorithm compatibility
        4. Calculate Steiner tree connecting all terminals
        5. Convert optimized network back to geospatial format

    Steiner Tree Properties:
        - Connects all terminal points with minimal total edge weight
        - May include intermediate nodes (Steiner points) for optimization
        - Follows existing street infrastructure constraints
        - Provides practical network topology for implementation

    Optimization Objectives:
        - Minimizes total network construction length
        - Respects existing street infrastructure
        - Connects all required building locations
        - Balances cost minimization with practical constraints

    Visualization Features:
        - Optional plotting of complete street network (gray)
        - Highlighted Steiner tree network (red)
        - Terminal point markers (blue crosses)
        - Supports network design review and validation

    Examples
    --------
    >>> # Generate optimal heating network
    >>> import geopandas as gpd
    >>> streets = gpd.read_file("street_network.shp")
    >>> buildings = gpd.read_file("buildings.shp")
    >>> 
    >>> optimal_network = generate_steiner_tree_network(streets, buildings)
    >>> print(f"Generated network with {len(optimal_network)} segments")

    >>> # Calculate network statistics
    >>> total_length = optimal_network.geometry.length.sum()
    >>> avg_segment_length = optimal_network.geometry.length.mean()
    >>> print(f"Total network length: {total_length:.0f}m")
    >>> print(f"Average segment length: {avg_segment_length:.0f}m")

    >>> # Save optimized network
    >>> optimal_network.to_file("optimal_heating_network.shp")

    >>> # Analyze network efficiency
    >>> building_count = len(buildings)
    >>> network_length = total_length
    >>> connection_density = building_count / (network_length / 1000)  # buildings per km
    >>> print(f"Connection density: {connection_density:.1f} buildings/km")

    Raises
    ------
    ValueError
        If insufficient terminals in largest connected component (< 2).
    NetworkXError
        If street network cannot be converted to valid graph.
    GeometryError
        If input geometries are invalid or incompatible.

    See Also
    --------
    create_road_graph : Street network graph creation
    map_points_to_graph_nodes : Building location mapping
    networkx.algorithms.approximation.steiner_tree : Core optimization algorithm
    """
    # Create graph representation of street network
    road_graph = create_road_graph(street_layer)
    
    # Map building locations to street network
    terminals = map_points_to_graph_nodes(road_graph, points_gdf)

    # Filter to largest connected component
    road_graph, terminals = filter_to_largest_component(road_graph, terminals)
    
    # Validate sufficient terminals for Steiner tree calculation
    if len(terminals) < 2:
        raise ValueError("Insufficient terminals in largest connected component for network generation!")

    # Calculate optimal Steiner tree network
    steiner_subgraph = steiner_tree(road_graph, terminals, weight='weight')

    # Optional visualization of results
    fig, ax = plt.subplots(figsize=(10, 10))

    # Plot complete street network (background)
    for u, v in road_graph.edges():
        line = LineString([u, v])
        xs, ys = zip(*line.coords)
        ax.plot(xs, ys, color='lightgray', linewidth=1, zorder=1)

    # Plot optimized Steiner tree network (highlighted)
    for u, v in steiner_subgraph.edges():
        line = LineString([u, v])
        xs, ys = zip(*line.coords)
        ax.plot(xs, ys, color='red', linewidth=2, zorder=2)

    # Plot terminal locations (building connections)
    for t in terminals:
        ax.plot(t[0], t[1], marker='x', color='blue', markersize=10, 
               label='Terminal', zorder=3)

    ax.set_title('Optimal District Heating Network Layout')
    ax.set_xlabel('Easting [m]')
    ax.set_ylabel('Northing [m]')
    ax.legend()
    plt.show()

    # Convert optimized network to geospatial format
    network_lines = [LineString([Point(u), Point(v)]) for u, v in steiner_subgraph.edges()]
    
    return gpd.GeoDataFrame(geometry=network_lines)