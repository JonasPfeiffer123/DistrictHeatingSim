"""
Plot-data extraction for the interactive network plot (Plotly-free, GUI-free).
=============================================================================

Pulls the data the interactive Plotly plot needs *out* of a pandapipes net into plain
Python structures, so the rendering layer (``interactive_network_plot``) no longer
mixes pandapipes queries with Plotly trace building (BACKLOG B1/B3). Being Plotly- and
GUI-free, this layer is unit-testable through the network test seam.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from dataclasses import dataclass

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

from districtheatingsim.constants import KELVIN_OFFSET


@dataclass
class JunctionPlotData:
    """Everything the renderer needs to draw the junction markers — no pandapipes."""

    lats: np.ndarray
    lons: np.ndarray
    hover_texts: list[str]
    values: np.ndarray | None  # per-junction colour values, or None if not colour-coded
    ids: np.ndarray


def junction_geodata_wgs84(net, crs) -> gpd.GeoDataFrame:
    """Junction coordinates as a WGS84 GeoDataFrame (for Plotly mapbox)."""
    gdf = gpd.GeoDataFrame(
        net.junction_geodata,
        geometry=[Point(xy) for xy in zip(
            net.junction_geodata['x'], net.junction_geodata['y'], strict=False
        )],
        crs=crs,
    )
    return gdf.to_crs('EPSG:4326')


def junction_plot_data(net, crs, parameter: str | None = None) -> JunctionPlotData:
    """
    Extract junction marker data (coords, hover text, colour values) from the net.

    :param net: pandapipes network (duck-typed: ``junction_geodata``, ``junction``,
        optional ``res_junction``).
    :param crs: source CRS of the junction geodata (reprojected to WGS84).
    :param parameter: ``res_junction`` column to colour by, or ``None``.
    :rtype: JunctionPlotData
    """
    gdf = junction_geodata_wgs84(net, crs)

    hover_texts = []
    for idx in gdf.index:
        junction = net.junction.loc[idx]
        text = f"<b>{junction['name']}</b><br>"
        if hasattr(net, 'res_junction'):
            res = net.res_junction.loc[idx]
            text += f"Druck: {res['p_bar']:.2f} bar<br>"
            text += f"Temperatur: {res['t_k'] - KELVIN_OFFSET:.1f} °C<br>"
        hover_texts.append(text)

    values = None
    if parameter and hasattr(net, 'res_junction'):
        values = net.res_junction.loc[gdf.index, parameter].values

    return JunctionPlotData(
        lats=gdf.geometry.y.values,
        lons=gdf.geometry.x.values,
        hover_texts=hover_texts,
        values=values,
        ids=gdf.index.values,
    )


_PARAMETER_LABELS = {
    'p_bar': 'Druck [bar]',
    't_k': 'Temperatur [K]',
    'v_mean_m_per_s': 'Geschwindigkeit [m/s]',
    'mdot_from_kg_per_s': 'Massenstrom [kg/s]',
    'reynolds': 'Reynolds-Zahl [-]',
    'lambda': 'Reibungsbeiwert [-]',
    'qext_w': 'Wärmebedarf [W]',
    'deltap_bar': 'Druckdifferenz [bar]',
}


def parameter_label(parameter: str) -> str:
    """German display label (with unit) for a result parameter."""
    return _PARAMETER_LABELS.get(parameter, parameter)


def parameter_value(res_df, idx, parameter):
    """
    Value of ``parameter`` for component ``idx``, computing the derived ``dt_k`` /
    ``dp_bar`` from the from/to columns. Returns ``None`` if unavailable.
    """
    if parameter == 'dt_k':
        if 't_from_k' in res_df.columns and 't_to_k' in res_df.columns:
            return res_df.loc[idx, 't_from_k'] - res_df.loc[idx, 't_to_k']
    elif parameter == 'dp_bar':
        if 'p_from_bar' in res_df.columns and 'p_to_bar' in res_df.columns:
            return res_df.loc[idx, 'p_from_bar'] - res_df.loc[idx, 'p_to_bar']
    elif parameter in res_df.columns:
        return res_df.loc[idx, parameter]
    return None


@dataclass
class PipeSegment:
    """One pipe drawn as a from→mid→to polyline, with hover text and colour value."""

    from_lat: float
    from_lon: float
    mid_lat: float
    mid_lon: float
    to_lat: float
    to_lon: float
    hover_text: str
    value: float | None
    idx: object
    name: str


@dataclass
class PipePlotData:
    segments: list[PipeSegment]
    vmin: float | None  # colour range over all segment values (None if not colour-coded)
    vmax: float | None
    center_lat: float   # network centre, for the colorbar carrier marker
    center_lon: float


def _pipe_hover_text(net, idx, pipe, parameter, value, has_res) -> str:
    text = f"<b>{pipe['name']}</b><br>"
    text += f"Typ: {pipe['std_type']}<br>"
    text += f"Länge: {pipe['length_km']:.3f} km<br>"
    if has_res:
        res = net.res_pipe.loc[idx]
        if 'mdot_from_kg_per_s' in res.index:
            text += f"Massenstrom: {res['mdot_from_kg_per_s']:.2f} kg/s<br>"
        if 'v_mean_m_per_s' in res.index:
            text += f"Geschwindigkeit: {res['v_mean_m_per_s']:.2f} m/s<br>"
        if 't_from_k' in res.index and 't_to_k' in res.index:
            text += f"ΔT: {res['t_from_k'] - res['t_to_k']:.1f} K<br>"
        if 'p_from_bar' in res.index and 'p_to_bar' in res.index:
            text += f"Δp: {res['p_from_bar'] - res['p_to_bar']:.2f} bar<br>"
        if value is not None and parameter:
            text += f"{parameter_label(parameter)}: {value:.2f}<br>"
    return text


def pipe_plot_data(net, junctions_wgs84, parameter: str | None = None) -> PipePlotData:
    """
    Extract pipe polyline data (endpoint/mid coords, hover, colour values) from the net.

    :param net: pandapipes network (duck-typed: ``pipe``, optional ``res_pipe``).
    :param junctions_wgs84: WGS84 junction GeoDataFrame (from :func:`junction_geodata_wgs84`).
    :param parameter: ``res_pipe`` column (or derived ``dt_k``/``dp_bar``) to colour by.
    :rtype: PipePlotData
    """
    if not hasattr(net, 'pipe') or len(net.pipe) == 0:
        return PipePlotData([], None, None, 0.0, 0.0)

    has_res = hasattr(net, 'res_pipe')
    center_lat = float(junctions_wgs84.geometry.y.mean())
    center_lon = float(junctions_wgs84.geometry.x.mean())

    segments: list[PipeSegment] = []
    values: list[float] = []
    for idx in net.pipe.index:
        pipe = net.pipe.loc[idx]
        try:
            fc = junctions_wgs84.loc[pipe['from_junction']].geometry
            tc = junctions_wgs84.loc[pipe['to_junction']].geometry
        except KeyError:
            continue
        value = parameter_value(net.res_pipe, idx, parameter) if (parameter and has_res) else None
        if value is not None:
            values.append(value)
        segments.append(PipeSegment(
            from_lat=fc.y, from_lon=fc.x,
            mid_lat=(fc.y + tc.y) / 2, mid_lon=(fc.x + tc.x) / 2,
            to_lat=tc.y, to_lon=tc.x,
            hover_text=_pipe_hover_text(net, idx, pipe, parameter, value, has_res),
            value=value, idx=idx, name=pipe.get('name', f'Pipe {idx}'),
        ))

    vmin = vmax = None
    if values:
        vmin, vmax = min(values), max(values)
        if vmax - vmin < 1e-10:
            vmax = vmin + 1  # avoid divide-by-zero in colour normalisation
    return PipePlotData(segments, vmin, vmax, center_lat, center_lon)


def _heat_consumer_hover_text(net, idx, hc, parameter, value, has_res) -> str:
    text = f"<b>{hc['name']}</b><br>"
    text += f"Wärmebedarf: {hc['qext_w'] / 1000:.1f} kW<br>"
    if has_res:
        res = net.res_heat_consumer.loc[idx]
        if 'mdot_from_kg_per_s' in res.index:
            text += f"Massenstrom: {res['mdot_from_kg_per_s']:.2f} kg/s<br>"
        if 't_from_k' in res.index:
            text += f"Vorlauftemp.: {res['t_from_k'] - KELVIN_OFFSET:.1f} °C<br>"
        if 't_to_k' in res.index:
            text += f"Rücklauftemp.: {res['t_to_k'] - KELVIN_OFFSET:.1f} °C<br>"
        if 'dt_k' in res.index:
            text += f"ΔT: {res['dt_k']:.1f} K<br>"
        elif 't_from_k' in res.index and 't_to_k' in res.index:
            text += f"ΔT: {res['t_from_k'] - res['t_to_k']:.1f} K<br>"
        if 'p_from_bar' in res.index:
            text += f"Vorlaufdruck: {res['p_from_bar']:.2f} bar<br>"
        if 'p_to_bar' in res.index:
            text += f"Rücklaufdruck: {res['p_to_bar']:.2f} bar<br>"
        if 'deltap_bar' in res.index:
            text += f"Δp: {res['deltap_bar']:.2f} bar<br>"
        elif 'p_from_bar' in res.index and 'p_to_bar' in res.index:
            text += f"Δp: {res['p_from_bar'] - res['p_to_bar']:.2f} bar<br>"
        if value is not None and parameter:
            text += f"{parameter_label(parameter)}: {value:.2f}<br>"
    return text


def heat_consumer_plot_data(net, junctions_wgs84, parameter: str | None = None) -> PipePlotData:
    """
    Extract heat-consumer polyline data (coords, hover, colour values) from the net.

    Same line structure as :func:`pipe_plot_data`; the hover fields are
    consumer-specific (heat demand, supply/return temperatures and pressures).
    """
    if not hasattr(net, 'heat_consumer') or len(net.heat_consumer) == 0:
        return PipePlotData([], None, None, 0.0, 0.0)

    has_res = hasattr(net, 'res_heat_consumer')
    center_lat = float(junctions_wgs84.geometry.y.mean())
    center_lon = float(junctions_wgs84.geometry.x.mean())

    segments: list[PipeSegment] = []
    values: list[float] = []
    for idx in net.heat_consumer.index:
        hc = net.heat_consumer.loc[idx]
        try:
            fc = junctions_wgs84.loc[hc['from_junction']].geometry
            tc = junctions_wgs84.loc[hc['to_junction']].geometry
        except KeyError:
            continue
        value = parameter_value(net.res_heat_consumer, idx, parameter) if (parameter and has_res) else None
        if value is not None:
            values.append(value)
        segments.append(PipeSegment(
            from_lat=fc.y, from_lon=fc.x,
            mid_lat=(fc.y + tc.y) / 2, mid_lon=(fc.x + tc.x) / 2,
            to_lat=tc.y, to_lon=tc.x,
            hover_text=_heat_consumer_hover_text(net, idx, hc, parameter, value, has_res),
            value=value, idx=idx, name=hc.get('name', f'Heat Consumer {idx}'),
        ))

    vmin = vmax = None
    if values:
        vmin, vmax = min(values), max(values)
        if vmax - vmin < 1e-10:
            vmax = vmin + 1
    return PipePlotData(segments, vmin, vmax, center_lat, center_lon)


def available_plot_parameters(net) -> dict[str, list[str]]:
    """
    The result parameters available for colour-coding per component type.

    Inspects the net's ``res_*`` tables and returns the parameters the plot can offer
    for each component (junction, pipe, heat_consumer, pump, flow_control). Empty lists
    for components without results yet.

    :param net: A pandapipes network (duck-typed: read ``res_*`` tables).
    :return: ``{component_type: [parameter, …]}``.
    :rtype: dict[str, list[str]]
    """
    params: dict[str, list[str]] = {
        'junction': [],
        'pipe': [],
        'heat_consumer': [],
        'pump': [],
        'flow_control': [],
    }

    # Junction parameters - Pressure and Temperature
    if hasattr(net, 'res_junction'):
        params['junction'] = [
            'p_bar',  # Pressure [bar]
            't_k',    # Temperature [K]
        ]

    # Pipe parameters - Only most relevant ones
    if hasattr(net, 'res_pipe'):
        available_pipe_params = []
        res_pipe = net.res_pipe

        # Core flow parameters
        if 'mdot_from_kg_per_s' in res_pipe.columns:
            available_pipe_params.append('mdot_from_kg_per_s')  # Mass flow [kg/s]
        if 'v_mean_m_per_s' in res_pipe.columns:
            available_pipe_params.append('v_mean_m_per_s')      # Velocity [m/s]

        # Differential parameters (most useful for analysis)
        if 't_from_k' in res_pipe.columns and 't_to_k' in res_pipe.columns:
            available_pipe_params.append('dt_k')                # Temperature difference [K]
        if 'p_from_bar' in res_pipe.columns and 'p_to_bar' in res_pipe.columns:
            available_pipe_params.append('dp_bar')              # Pressure loss [bar]

        params['pipe'] = available_pipe_params

    # Heat consumer parameters - Only most relevant ones
    if hasattr(net, 'res_heat_consumer'):
        available_hc_params = []
        res_hc = net.res_heat_consumer

        if 'qext_w' in res_hc.columns:
            available_hc_params.append('qext_w')                # Heat demand [W]
        if 'mdot_from_kg_per_s' in res_hc.columns:
            available_hc_params.append('mdot_from_kg_per_s')    # Mass flow [kg/s]

        # Differential parameters (most useful for analysis)
        if 't_from_k' in res_hc.columns and 't_to_k' in res_hc.columns:
            available_hc_params.append('dt_k')                  # Temperature difference [K]
        if 'p_from_bar' in res_hc.columns and 'p_to_bar' in res_hc.columns:
            available_hc_params.append('dp_bar')                # Pressure drop [bar]

        params['heat_consumer'] = available_hc_params

    # Pump parameters - Only most relevant ones
    if hasattr(net, 'res_circ_pump_pressure') or hasattr(net, 'res_circ_pump_mass'):
        available_pump_params = []

        # Pressure pump results
        if hasattr(net, 'res_circ_pump_pressure') and len(net.res_circ_pump_pressure) > 0:
            res_pump = net.res_circ_pump_pressure
            if 'mdot_from_kg_per_s' in res_pump.columns:
                available_pump_params.append('mdot_from_kg_per_s')  # Mass flow [kg/s]
            if 'deltap_bar' in res_pump.columns:
                available_pump_params.append('deltap_bar')          # Pressure increase [bar]

            # Temperature difference
            if 't_from_k' in res_pump.columns and 't_to_k' in res_pump.columns:
                available_pump_params.append('dt_k')                # Temperature difference [K]

        # Mass pump results (if exists)
        if hasattr(net, 'res_circ_pump_mass') and len(net.res_circ_pump_mass) > 0:
            res_pump_mass = net.res_circ_pump_mass
            if 'mdot_from_kg_per_s' in res_pump_mass.columns and 'mdot_from_kg_per_s' not in available_pump_params:
                available_pump_params.append('mdot_from_kg_per_s')

        params['pump'] = list(set(available_pump_params))  # Remove duplicates

    # Flow control parameters
    if hasattr(net, 'res_flow_control') and len(net.flow_control) > 0:
        available_fc_params = []
        res_fc = net.res_flow_control

        if 'mdot_from_kg_per_s' in res_fc.columns:
            available_fc_params.append('mdot_from_kg_per_s')    # Mass flow [kg/s]
        if 'deltap_bar' in res_fc.columns:
            available_fc_params.append('deltap_bar')            # Pressure difference [bar]
        if 't_from_k' in res_fc.columns:
            available_fc_params.append('t_from_k')              # From temperature [K]
        if 't_to_k' in res_fc.columns:
            available_fc_params.append('t_to_k')                # To temperature [K]
        if 'p_from_bar' in res_fc.columns:
            available_fc_params.append('p_from_bar')            # From pressure [bar]
        if 'p_to_bar' in res_fc.columns:
            available_fc_params.append('p_to_bar')              # To pressure [bar]

        params['flow_control'] = available_fc_params

    return params
