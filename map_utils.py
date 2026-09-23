"""Taiwan Weather Map generator using Folium.

Generates responsive, interactive maps with customized markers for Taiwan
counties and real-time automated weather stations.
"""

from __future__ import annotations

import logging
from typing import Optional

import folium
from folium.plugins import MarkerCluster
import pandas as pd

import config

logger = logging.getLogger(__name__)


def get_marker_color(temp: Optional[float]) -> str:
    """Return a marker color based on Celsius temperature."""
    if temp is None:
        return "gray"
    if temp >= 32:
        return "red"
    if temp >= 28:
        return "orange"
    if temp >= 22:
        return "green"
    if temp >= 16:
        return "blue"
    return "darkblue"


def get_weather_icon(wx: str) -> str:
    """Return a FontAwesome icon name for weather conditions."""
    if not wx:
        return "cloud"
    if "晴" in wx:
        return "sun"
    if "雨" in wx:
        return "cloud-rain"
    if "陰" in wx:
        return "cloud"
    if "雷" in wx:
        return "bolt"
    if "霧" in wx:
        return "smog"
    return "cloud-sun"


def create_taiwan_weather_map(
    forecast_df: Optional[pd.DataFrame] = None,
    observation_df: Optional[pd.DataFrame] = None,
    selected_region: Optional[str] = None,
    show_stations: bool = True,
) -> folium.Map:
    """Generate an interactive Taiwan Weather Map using Folium.

    Args:
        forecast_df: DataFrame of county forecasts (regionName, temp/MaxT/MinT, Wx, PoP).
        observation_df: DataFrame of station observations with lat/lon.
        selected_region: Optional regionName to highlight and center on.
        show_stations: If True, include cluster of detailed observation stations.

    Returns:
        folium.Map: Ready-to-render Folium Map object.
    """
    # Default Taiwan Center
    center_lat, center_lon = 23.7, 120.95
    zoom_start = 8

    # If selected_region has coordinates, adjust center
    if selected_region and selected_region in config.COUNTY_COORDINATES:
        c_lat, c_lon = config.COUNTY_COORDINATES[selected_region]
        center_lat, center_lon = c_lat, c_lon
        zoom_start = 10

    taiwan_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    # 1. Add County Overview Markers
    county_summary: dict[str, dict] = {}
    if forecast_df is not None and not forecast_df.empty:
        # Group by regionName and take the latest/first record
        for region, group in forecast_df.groupby("regionName"):
            first_row = group.iloc[0]
            temp_val = first_row.get("temp")
            if pd.isna(temp_val) or temp_val is None:
                # Estimate from (MinT + MaxT) / 2
                mint = first_row.get("MinT", 20.0)
                maxt = first_row.get("MaxT", 28.0)
                temp_val = round((float(mint) + float(maxt)) / 2, 1) if pd.notna(mint) and pd.notna(maxt) else 25.0

            county_summary[region] = {
                "temp": float(temp_val),
                "Wx": str(first_row.get("Wx", "多雲")),
                "MinT": float(first_row.get("MinT", 20.0)) if pd.notna(first_row.get("MinT")) else 20.0,
                "MaxT": float(first_row.get("MaxT", 28.0)) if pd.notna(first_row.get("MaxT")) else 28.0,
                "PoP": float(first_row.get("PoP", 0.0)) if pd.notna(first_row.get("PoP")) else 0.0,
            }

    for county, (lat, lon) in config.COUNTY_COORDINATES.items():
        info = county_summary.get(county, {
            "temp": 25.0,
            "Wx": "多雲",
            "MinT": 22.0,
            "MaxT": 28.0,
            "PoP": 20.0,
        })
        temp = info["temp"]
        wx = info["Wx"]
        color = get_marker_color(temp)

        is_selected = (county == selected_region)
        border_style = "border: 3px solid #1E88E5; transform: scale(1.15);" if is_selected else ""

        html_popup = f"""
        <div style="font-family: 'Helvetica Neue', Arial, sans-serif; min-width: 170px; padding: 6px; {border_style}">
            <h4 style="margin: 0 0 6px 0; color: #1565C0; font-size: 16px;">{county}</h4>
            <div style="font-size: 22px; font-weight: bold; color: #D32F2F; margin-bottom: 4px;">
                {temp:.1f} °C
            </div>
            <div style="font-size: 13px; color: #424242; line-height: 1.5;">
                <b>天氣狀況：</b> {wx}<br/>
                <b>氣溫區間：</b> {info['MinT']:.0f}°C ~ {info['MaxT']:.0f}°C<br/>
                <b>降雨機率：</b> {info['PoP']:.0f}%
            </div>
        </div>
        """

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(html_popup, max_width=260),
            tooltip=f"{county}: {temp:.1f}°C ({wx})",
            icon=folium.Icon(
                color=color,
                icon=get_weather_icon(wx),
                prefix="fa",
            ),
        ).add_to(taiwan_map)

    # 2. Add Detailed Station Markers (if observation data present)
    if show_stations and observation_df is not None and not observation_df.empty:
        station_cluster = MarkerCluster(name="自動氣象觀測站 (363 站)").add_to(taiwan_map)
        valid_stations = observation_df.dropna(subset=["latitude", "longitude", "temp"])

        for _, row in valid_stations.iterrows():
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            st_name = row.get("stationName", "測站")
            county = row.get("regionName", "")
            town = row.get("townName", "")
            st_temp = float(row["temp"])
            st_wx = str(row.get("Wx", "觀測中"))
            precip = float(row.get("precipitation", 0.0))

            station_popup = f"""
            <div style="font-family: sans-serif; font-size: 12px; min-width: 140px;">
                <b style="color: #0288D1;">{st_name} 測站</b> ({county} {town})<br/>
                <b>即時氣溫：</b> {st_temp:.1f} °C<br/>
                <b>天氣現象：</b> {st_wx}<br/>
                <b>當前雨量：</b> {precip:.1f} mm
            </div>
            """

            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color="#0288D1",
                fill=True,
                fill_color="#29B6F6",
                fill_opacity=0.7,
                popup=folium.Popup(station_popup, max_width=200),
                tooltip=f"{st_name}: {st_temp:.1f}°C",
            ).add_to(station_cluster)

        folium.LayerControl().add_to(taiwan_map)

    return taiwan_map
