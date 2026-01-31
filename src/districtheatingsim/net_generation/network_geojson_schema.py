"""
Unified GeoJSON schema for district heating networks with layered data model.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
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
    Unified GeoJSON schema for district heating networks with editable/protected data separation.
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
        
        :param state: Network state ('designed', 'calculated', or 'optimized')
        :type state: str
        :return: Metadata dictionary with version, timestamp, and edit levels
        :rtype: Dict[str, Any]
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
        
        :param geometry: Line geometry
        :type geometry: LineString
        :param layer: Layer type ('flow' or 'return')
        :type layer: str
        :param segment_id: Unique segment identifier
        :type segment_id: str
        :param color: Hex color code (default: #59DB7F for flow, #0C350A for return)
        :type color: str
        :param calculated_data: Calculation results (diameter, flow rate, etc.)
        :type calculated_data: Dict
        :return: GeoJSON Feature with style and calculated properties
        :rtype: Dict[str, Any]
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
        Create a building connection feature with protected building data.
        
        :param geometry: Connection line geometry
        :type geometry: LineString
        :param connection_id: Unique connection identifier
        :type connection_id: str
        :param building_data: Building data from CSV (protected)
        :type building_data: Dict[str, Any]
        :return: GeoJSON Feature with building metadata
        :rtype: Dict[str, Any]
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
        
        :param geometry: Connection line geometry
        :type geometry: LineString
        :param connection_id: Unique connection identifier
        :type connection_id: str
        :param generator_type: Generator type ('main' or 'secondary')
        :type generator_type: str
        :param location_index: Generator location index
        :type location_index: int
        :return: GeoJSON Feature with generator metadata
        :rtype: Dict[str, Any]
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
        
        :param flow_lines: Supply line network
        :type flow_lines: gpd.GeoDataFrame
        :param return_lines: Return line network
        :type return_lines: gpd.GeoDataFrame
        :param building_connections: Building connections with data
        :type building_connections: gpd.GeoDataFrame
        :param generator_connections: Generator connections
        :type generator_connections: gpd.GeoDataFrame
        :param state: Network state
        :type state: str
        :param calculated_data: Calculation results indexed by segment_id
        :type calculated_data: Dict
        :return: Complete GeoJSON FeatureCollection
        :rtype: Dict[str, Any]
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
        
        :param geojson: Network GeoJSON dictionary
        :type geojson: Dict[str, Any]
        :param filepath: Output file path
        :type filepath: str
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        print(f"✓ Exported unified network GeoJSON: {filepath}")
    
    @staticmethod
    def import_from_file(filepath: str) -> Dict[str, Any]:
        """
        Import network GeoJSON from file.
        
        :param filepath: Input file path
        :type filepath: str
        :return: Network GeoJSON dictionary
        :rtype: Dict[str, Any]
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
        
        :param geojson: Unified network GeoJSON
        :type geojson: Dict[str, Any]
        :return: (flow_lines, return_lines, building_connections, generator_connections)
        :rtype: Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]
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
        
        :param geojson: Unified network GeoJSON
        :type geojson: Dict[str, Any]
        :param flow_results: Calculation results for flow lines {segment_id: {diameter_mm, ...}}
        :type flow_results: Dict[str, Dict]
        :param return_results: Calculation results for return lines
        :type return_results: Dict[str, Dict]
        :return: Updated GeoJSON with calculation results
        :rtype: Dict[str, Any]
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
