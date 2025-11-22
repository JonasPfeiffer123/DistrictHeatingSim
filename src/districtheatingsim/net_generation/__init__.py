"""
Network Generation Module
==========================

This module provides various algorithms for generating district heating network topologies.

Available Methods
-----------------

**OSMnx-based Generation** (Recommended for street-based networks):
    - Uses OpenStreetMap street network data
    - Steiner Tree optimization for minimal network length
    - Edge-splitting algorithm with exact coordinate matching
    - Dead-end removal with connection protection
    - Suitable for urban areas with existing street data

**Minimal Spanning Tree**:
    - Connects all buildings with minimal total pipe length
    - No consideration of existing infrastructure
    - Suitable for greenfield sites or initial planning

**Steiner Tree** (Direct):
    - Approximation of optimal connection tree
    - May include Steiner points (additional junction nodes)
    - Suitable for open-area planning

**Import and Create Layers**:
    - Import existing GeoJSON network data
    - Create network layers from geometries
    - Suitable for working with pre-existing network designs

Examples
--------
Generate network using OSMnx:

>>> from districtheatingsim.net_generation.osmnx_steiner_network import generate_osmnx_network
>>> import geopandas as gpd
>>> 
>>> buildings = gpd.read_file('buildings.csv')
>>> result = generate_osmnx_network(
...     buildings=buildings,
...     generator_coords=(480219, 5711597),
...     output_dir='output/'
... )

See Also
--------
osmnx_steiner_network : OSMnx-based network generation (recommended)
minimal_spanning_tree : Minimal spanning tree generation
steiner_tree : Direct Steiner tree generation
"""

from .osmnx_steiner_network import (
    generate_osmnx_network,
    generate_and_export_osmnx_layers,
    download_street_graph,
    create_steiner_tree,
    connect_terminals_with_edge_splitting,
    build_network_from_split_edges,
    remove_dead_ends,
    create_connection_lines,
    create_return_network,
    create_hast_connections,
    create_generator_connection
)

__all__ = [
    # Main generation functions
    'generate_osmnx_network',
    'generate_and_export_osmnx_layers',
    
    # Step-by-step functions
    'download_street_graph',
    'create_steiner_tree',
    'connect_terminals_with_edge_splitting',
    'build_network_from_split_edges',
    'remove_dead_ends',
    'create_connection_lines',
    'create_return_network',
    'create_hast_connections',
    'create_generator_connection',
]
