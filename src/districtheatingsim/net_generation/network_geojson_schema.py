"""
Network GeoJSON Schema Module
=============================

Unified GeoJSON schema for district heating networks with layered data model.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-12-19

This module provides a standardized GeoJSON format that combines network geometry,
building connections, and generator connections in a single file with clear
separation between editable and protected data.
"""

import json
import geopandas as gpd
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from shapely.geometry import LineString, Point
from datetime import datetime


class NetworkGeoJSONSchema:
    """
    Unified GeoJSON schema for district heating networks.
    
    Features:
    - Combines all network layers in single file
    - Clear separation: editable vs. protected data
    - Supports calculation results (diameters, pressures, etc.)
    - Backward compatible with legacy 4-file format
    """
    
    VERSION = "2.0"
    
    # Feature types
    FEATURE_TYPE_FLOW = "network_line_flow"
    FEATURE_TYPE_RETURN = "network_line_return"
    FEATURE_TYPE_BUILDING = "building_connection"
    FEATURE_TYPE_GENERATOR = "generator_connection"
    
    # Edit levels
    EDIT_LEVEL_EDITABLE = "editable"
    EDIT_LEVEL_GENERATED = "generated"
    EDIT_LEVEL_PROTECTED = "protected"
    
    @staticmethod
    def create_metadata(state: str = "designed") -> Dict[str, Any]:
        """
        Create metadata for network GeoJSON.
        
        Parameters
        ----------
        state : str
            Network state: "designed", "calculated", or "optimized"
            
        Returns
        -------
        dict
            Metadata dictionary
        """
        return {
            "version": NetworkGeoJSONSchema.VERSION,
            "created": datetime.now().isoformat(),
            "state": state,
            "edit_levels": {
                "network_geometry": NetworkGeoJSONSchema.EDIT_LEVEL_EDITABLE,
                "connections": NetworkGeoJSONSchema.EDIT_LEVEL_GENERATED,
                "building_data": NetworkGeoJSONSchema.EDIT_LEVEL_PROTECTED
            }
        }
    
    @staticmethod
    def create_network_line_feature(
        geometry: LineString,
        layer: str,
        segment_id: str,
        color: str = None,
        calculated_data: Dict = None
    ) -> Dict[str, Any]:
        """
        Create a network line feature (flow or return).
        
        Parameters
        ----------
        geometry : LineString
            Line geometry
        layer : str
            "flow" or "return"
        segment_id : str
            Unique segment identifier
        color : str, optional
            Hex color code
        calculated_data : dict, optional
            Calculation results (diameter, flow rate, etc.)
            
        Returns
        -------
        dict
            GeoJSON Feature
        """
        # Default colors
        if color is None:
            color = "#59DB7F" if layer == "flow" else "#0C350A"
        
        # Calculate length from geometry
        length_m = geometry.length
        
        feature = {
            "type": "Feature",
            "properties": {
                "feature_type": NetworkGeoJSONSchema.FEATURE_TYPE_FLOW if layer == "flow" else NetworkGeoJSONSchema.FEATURE_TYPE_RETURN,
                "layer": layer,
                "segment_id": segment_id,
                "editable": True,
                
                "style": {
                    "color": color,
                    "weight": 3,
                    "opacity": 1
                },
                
                "calculated": {
                    "length_m": length_m,
                    "diameter_mm": None,
                    "std_type": None,
                    "flow_rate_kg_s": None,
                    "pressure_loss_bar": None,
                    "velocity_m_s": None
                }
            },
            "geometry": geometry.__geo_interface__
        }
        
        # Add calculated data if provided
        if calculated_data:
            feature["properties"]["calculated"].update(calculated_data)
        
        return feature
    
    @staticmethod
    def create_building_connection_feature(
        geometry: LineString,
        connection_id: str,
        building_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a building connection feature.
        
        Parameters
        ----------
        geometry : LineString
            Connection line geometry
        connection_id : str
            Unique connection identifier
        building_data : dict
            Building data from CSV (protected)
            
        Returns
        -------
        dict
            GeoJSON Feature
        """
        feature = {
            "type": "Feature",
            "properties": {
                "feature_type": NetworkGeoJSONSchema.FEATURE_TYPE_BUILDING,
                "connection_id": connection_id,
                "editable": False,
                
                "building_data": {
                    key: (None if pd.isna(value) else value)
                    for key, value in building_data.items()
                },
                
                "style": {
                    "color": "#FF0000",
                    "weight": 2,
                    "opacity": 0.8
                }
            },
            "geometry": geometry.__geo_interface__
        }
        
        return feature
    
    @staticmethod
    def create_generator_connection_feature(
        geometry: LineString,
        connection_id: str,
        generator_type: str = "main",
        location_index: int = 0
    ) -> Dict[str, Any]:
        """
        Create a generator connection feature.
        
        Parameters
        ----------
        geometry : LineString
            Connection line geometry
        connection_id : str
            Unique connection identifier
        generator_type : str
            "main" or "secondary"
        location_index : int
            Generator location index
            
        Returns
        -------
        dict
            GeoJSON Feature
        """
        feature = {
            "type": "Feature",
            "properties": {
                "feature_type": NetworkGeoJSONSchema.FEATURE_TYPE_GENERATOR,
                "connection_id": connection_id,
                "editable": False,
                
                "generator_data": {
                    "type": generator_type,
                    "location_index": location_index
                },
                
                "style": {
                    "color": "#0000FF",
                    "weight": 2,
                    "opacity": 1
                }
            },
            "geometry": geometry.__geo_interface__
        }
        
        return feature
    
    @staticmethod
    def create_network_geojson(
        flow_lines: gpd.GeoDataFrame,
        return_lines: gpd.GeoDataFrame,
        building_connections: gpd.GeoDataFrame,
        generator_connections: gpd.GeoDataFrame,
        state: str = "designed",
        calculated_data: Dict = None
    ) -> Dict[str, Any]:
        """
        Create unified network GeoJSON from separate components.
        
        Parameters
        ----------
        flow_lines : GeoDataFrame
            Supply line network
        return_lines : GeoDataFrame
            Return line network
        building_connections : GeoDataFrame
            Building connections with data
        generator_connections : GeoDataFrame
            Generator connections
        state : str
            Network state
        calculated_data : dict, optional
            Calculation results indexed by segment_id
            
        Returns
        -------
        dict
            Complete GeoJSON FeatureCollection
        """
        features = []
        
        # Add flow lines
        for idx, row in flow_lines.iterrows():
            segment_id = f"flow_{idx:03d}"
            
            # Extract calculated data from row if present
            calc_data = {}
            if 'diameter_mm' in row and not pd.isna(row['diameter_mm']):
                calc_data['diameter_mm'] = float(row['diameter_mm'])
            if 'std_type' in row and not pd.isna(row['std_type']):
                calc_data['std_type'] = str(row['std_type'])
            if 'length_m' in row and not pd.isna(row['length_m']):
                calc_data['length_m'] = float(row['length_m'])
            if 'flow_rate_kg_s' in row and not pd.isna(row['flow_rate_kg_s']):
                calc_data['flow_rate_kg_s'] = float(row['flow_rate_kg_s'])
            if 'pressure_loss_bar' in row and not pd.isna(row['pressure_loss_bar']):
                calc_data['pressure_loss_bar'] = float(row['pressure_loss_bar'])
            if 'velocity_m_s' in row and not pd.isna(row['velocity_m_s']):
                calc_data['velocity_m_s'] = float(row['velocity_m_s'])
            
            # Override with explicitly provided calculated_data if available
            if calculated_data and segment_id in calculated_data:
                calc_data.update(calculated_data[segment_id])
            
            # Check if row has properties (after editing in Leaflet)
            color = None
            if 'color' in row:
                color = row['color']
            elif 'properties' in row and isinstance(row['properties'], dict):
                color = row['properties'].get('color')
            
            feature = NetworkGeoJSONSchema.create_network_line_feature(
                geometry=row.geometry,
                layer="flow",
                segment_id=segment_id,
                color=color,
                calculated_data=calc_data if calc_data else None
            )
            features.append(feature)
        
        # Add return lines
        for idx, row in return_lines.iterrows():
            segment_id = f"return_{idx:03d}"
            
            # Extract calculated data from row if present
            calc_data = {}
            if 'diameter_mm' in row and not pd.isna(row['diameter_mm']):
                calc_data['diameter_mm'] = float(row['diameter_mm'])
            if 'std_type' in row and not pd.isna(row['std_type']):
                calc_data['std_type'] = str(row['std_type'])
            if 'length_m' in row and not pd.isna(row['length_m']):
                calc_data['length_m'] = float(row['length_m'])
            if 'flow_rate_kg_s' in row and not pd.isna(row['flow_rate_kg_s']):
                calc_data['flow_rate_kg_s'] = float(row['flow_rate_kg_s'])
            if 'pressure_loss_bar' in row and not pd.isna(row['pressure_loss_bar']):
                calc_data['pressure_loss_bar'] = float(row['pressure_loss_bar'])
            if 'velocity_m_s' in row and not pd.isna(row['velocity_m_s']):
                calc_data['velocity_m_s'] = float(row['velocity_m_s'])
            
            # Override with explicitly provided calculated_data if available
            if calculated_data and segment_id in calculated_data:
                calc_data.update(calculated_data[segment_id])
            
            color = None
            if 'color' in row:
                color = row['color']
            elif 'properties' in row and isinstance(row['properties'], dict):
                color = row['properties'].get('color')
            
            feature = NetworkGeoJSONSchema.create_network_line_feature(
                geometry=row.geometry,
                layer="return",
                segment_id=segment_id,
                color=color,
                calculated_data=calc_data if calc_data else None
            )
            features.append(feature)
        
        # Add building connections
        for idx, row in building_connections.iterrows():
            connection_id = f"hast_{idx:03d}"
            
            # Extract building data from row
            building_data = {
                col: row[col] for col in row.index 
                if col != 'geometry' and not pd.isna(row[col])
            }
            
            feature = NetworkGeoJSONSchema.create_building_connection_feature(
                geometry=row.geometry,
                connection_id=connection_id,
                building_data=building_data
            )
            features.append(feature)
        
        # Add generator connections
        for idx, row in generator_connections.iterrows():
            connection_id = f"gen_{idx:03d}"
            
            feature = NetworkGeoJSONSchema.create_generator_connection_feature(
                geometry=row.geometry,
                connection_id=connection_id,
                generator_type="main" if idx == 0 else "secondary",
                location_index=idx
            )
            features.append(feature)
        
        # Create complete GeoJSON
        geojson = {
            "type": "FeatureCollection",
            "name": "Wärmenetz",
            "crs": {
                "type": "name",
                "properties": {
                    "name": "urn:ogc:def:crs:EPSG::25833"
                }
            },
            "metadata": NetworkGeoJSONSchema.create_metadata(state),
            "features": features
        }

        print(f"Erstelltes GeoJSON mit {len(features)} Features.")
        
        return geojson
    
    @staticmethod
    def export_to_file(geojson: Dict[str, Any], filepath: str) -> None:
        """
        Export network GeoJSON to file.
        
        Parameters
        ----------
        geojson : dict
            Network GeoJSON
        filepath : str
            Output file path
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        print(f"✓ Exported unified network GeoJSON: {filepath}")
    
    @staticmethod
    def import_from_file(filepath: str) -> Dict[str, Any]:
        """
        Import network GeoJSON from file.
        
        Parameters
        ----------
        filepath : str
            Input file path
            
        Returns
        -------
        dict
            Network GeoJSON
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            geojson = json.load(f)
        return geojson
    
    @staticmethod
    def split_to_legacy_format(
        geojson: Dict[str, Any]
    ) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """
        Split unified GeoJSON into legacy 4-file format.
        
        Parameters
        ----------
        geojson : dict
            Unified network GeoJSON
            
        Returns
        -------
        tuple
            (flow_lines, return_lines, building_connections, generator_connections)
        """
        flow_features = []
        return_features = []
        building_features = []
        generator_features = []
        
        for feature in geojson['features']:
            ftype = feature['properties'].get('feature_type')
            
            if ftype == NetworkGeoJSONSchema.FEATURE_TYPE_FLOW:
                flow_features.append(feature)
            elif ftype == NetworkGeoJSONSchema.FEATURE_TYPE_RETURN:
                return_features.append(feature)
            elif ftype == NetworkGeoJSONSchema.FEATURE_TYPE_BUILDING:
                building_features.append(feature)
            elif ftype == NetworkGeoJSONSchema.FEATURE_TYPE_GENERATOR:
                generator_features.append(feature)
        
        # Convert to GeoDataFrames
        flow_gdf = gpd.GeoDataFrame.from_features(flow_features, crs="EPSG:25833") if flow_features else gpd.GeoDataFrame()
        return_gdf = gpd.GeoDataFrame.from_features(return_features, crs="EPSG:25833") if return_features else gpd.GeoDataFrame()
        building_gdf = gpd.GeoDataFrame.from_features(building_features, crs="EPSG:25833") if building_features else gpd.GeoDataFrame()
        generator_gdf = gpd.GeoDataFrame.from_features(generator_features, crs="EPSG:25833") if generator_features else gpd.GeoDataFrame()
        
        return flow_gdf, return_gdf, building_gdf, generator_gdf
    
    @staticmethod
    def update_calculated_data(
        geojson: Dict[str, Any],
        flow_results: Dict[str, Dict],
        return_results: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        Update calculated data in unified GeoJSON after network dimensioning.
        
        Parameters
        ----------
        geojson : dict
            Unified network GeoJSON
        flow_results : dict
            Calculation results for flow lines {segment_id: {diameter_mm, flow_rate_kg_s, ...}}
        return_results : dict
            Calculation results for return lines
            
        Returns
        -------
        dict
            Updated GeoJSON with calculation results
        """
        updated_geojson = geojson.copy()
        updated_geojson['metadata']['state'] = 'calculated'
        
        for feature in updated_geojson['features']:
            segment_id = feature['properties'].get('segment_id')
            
            if not segment_id:
                continue
            
            # Update flow line results
            if segment_id.startswith('flow_') and segment_id in flow_results:
                feature['properties']['calculated'].update(flow_results[segment_id])
            
            # Update return line results
            elif segment_id.startswith('return_') and segment_id in return_results:
                feature['properties']['calculated'].update(return_results[segment_id])
        
        return updated_geojson
