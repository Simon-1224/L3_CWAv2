"""Module for parsing, cleaning, and transforming raw CWA JSON data into Pandas DataFrames.

Handles data cleansing, type conversions, missing values, and formatting
for both weather forecasts (F-C0032-001) and station observations (O-A0003-001).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """Safely convert a value to float, returning default if invalid or -99 (CWA sensor error)."""
    if val is None or val == "" or val == "-99" or val == -99 or val == "-99.0":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def parse_forecast_json(raw_json: Dict[str, Any]) -> pd.DataFrame:
    """Parse CWA Forecast JSON (F-C0032-001) into a structured Pandas DataFrame.

    Output Schema:
        regionName | dataDate | startTime | endTime | Wx | PoP | MinT | MaxT

    Args:
        raw_json: Parsed response from CWA F-C0032-001 API.

    Returns:
        pd.DataFrame: Cleaned DataFrame conforming to the project specification.
    """
    records = raw_json.get("records", {})
    locations = records.get("location", [])

    rows: List[Dict[str, Any]] = []

    for loc in locations:
        region_name = loc.get("locationName", "").strip()
        weather_elements = loc.get("weatherElement", [])

        # Map elementName -> list of {startTime, endTime, parameter}
        element_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for elem in weather_elements:
            elem_name = elem.get("elementName")
            times = elem.get("time", [])
            for t in times:
                st = t.get("startTime", "")
                et = t.get("endTime", "")
                param = t.get("parameter", {})
                time_key = f"{st}|{et}"
                if time_key not in element_map:
                    element_map[time_key] = {
                        "startTime": st,
                        "endTime": et,
                    }
                element_map[time_key][elem_name] = param

        for time_key, data in element_map.items():
            start_time = data.get("startTime", "")
            end_time = data.get("endTime", "")
            # Derive dataDate (YYYY-MM-DD) from startTime
            data_date = start_time.split(" ")[0] if " " in start_time else start_time[:10]

            wx_param = data.get("Wx", {})
            wx = wx_param.get("parameterName", "多雲") if isinstance(wx_param, dict) else str(wx_param)

            pop_param = data.get("PoP", {})
            pop_val = pop_param.get("parameterName") if isinstance(pop_param, dict) else pop_param
            pop = safe_float(pop_val, default=0.0)

            mint_param = data.get("MinT", {})
            mint_val = mint_param.get("parameterName") if isinstance(mint_param, dict) else mint_param
            mint = safe_float(mint_val, default=20.0)

            maxt_param = data.get("MaxT", {})
            maxt_val = maxt_param.get("parameterName") if isinstance(maxt_param, dict) else maxt_param
            maxt = safe_float(maxt_val, default=28.0)

            rows.append({
                "regionName": region_name,
                "dataDate": data_date,
                "startTime": start_time,
                "endTime": end_time,
                "Wx": wx,
                "PoP": pop,
                "MinT": mint,
                "MaxT": maxt,
            })

    if not rows:
        return pd.DataFrame(columns=[
            "regionName", "dataDate", "startTime", "endTime", "Wx", "PoP", "MinT", "MaxT"
        ])

    df = pd.DataFrame(rows)
    # Deduplicate & sort
    df = df.drop_duplicates(subset=["regionName", "startTime", "endTime"])
    df = df.sort_values(by=["regionName", "startTime"]).reset_index(drop=True)
    return df


def parse_observation_json(raw_json: Dict[str, Any]) -> pd.DataFrame:
    """Parse CWA Observation JSON (O-A0003-001) into a structured Pandas DataFrame.

    Converts station observations into table rows with county-level metrics
    as well as station-level metadata (coordinates, current temperature, etc.).

    Args:
        raw_json: Parsed response from CWA O-A0003-001 API.

    Returns:
        pd.DataFrame: Observation records with station details and county forecasts.
    """
    records = raw_json.get("records", {})
    stations = records.get("Station", [])

    rows: List[Dict[str, Any]] = []

    for st in stations:
        geo = st.get("GeoInfo", {})
        county = geo.get("CountyName", "").strip()
        town = geo.get("TownName", "").strip()
        st_name = st.get("StationName", "").strip()
        st_id = st.get("StationId", "").strip()

        # Coordinates (WGS84 preferred)
        coords = geo.get("Coordinates", [])
        lat, lon = None, None
        for coord in coords:
            if coord.get("CoordinateName") == "WGS84":
                lat = safe_float(coord.get("StationLatitude"))
                lon = safe_float(coord.get("StationLongitude"))
                break
        if lat is None and coords:
            lat = safe_float(coords[0].get("StationLatitude"))
            lon = safe_float(coords[0].get("StationLongitude"))

        obs_time = st.get("ObsTime", {}).get("DateTime", "")
        # Format: 2026-09-23T19:20:00+08:00
        data_date = obs_time[:10] if len(obs_time) >= 10 else ""
        formatted_time = obs_time.replace("T", " ")[:19] if "T" in obs_time else obs_time

        we = st.get("WeatherElement", {})
        wx = we.get("Weather", "") or "多雲"
        temp = safe_float(we.get("AirTemperature"))
        humidity = safe_float(we.get("RelativeHumidity"), default=0.0)

        # Rain / Precip
        now_info = we.get("Now", {})
        precip = safe_float(now_info.get("Precipitation")) if isinstance(now_info, dict) else 0.0

        # Daily extremes (MaxT, MinT)
        daily = we.get("DailyExtreme", {})
        maxt_info = daily.get("DailyHigh", {}).get("TemperatureInfo", {}) if isinstance(daily, dict) else {}
        mint_info = daily.get("DailyLow", {}).get("TemperatureInfo", {}) if isinstance(daily, dict) else {}

        maxt = safe_float(maxt_info.get("AirTemperature")) if isinstance(maxt_info, dict) else None
        mint = safe_float(mint_info.get("AirTemperature")) if isinstance(mint_info, dict) else None

        # Fallbacks if extremes not yet populated
        if maxt is None and temp is not None:
            maxt = temp
        if mint is None and temp is not None:
            mint = temp

        rows.append({
            "regionName": county if county else st_name,
            "dataDate": data_date,
            "startTime": formatted_time,
            "endTime": formatted_time,
            "Wx": wx,
            "PoP": humidity,  # Observation proxy for moisture / PoP
            "MinT": mint if mint is not None else 20.0,
            "MaxT": maxt if maxt is not None else 28.0,
            "temp": temp,
            "stationName": st_name,
            "stationId": st_id,
            "townName": town,
            "latitude": lat,
            "longitude": lon,
            "precipitation": precip,
        })

    if not rows:
        return pd.DataFrame(columns=[
            "regionName", "dataDate", "startTime", "endTime", "Wx", "PoP", "MinT", "MaxT",
            "temp", "stationName", "stationId", "townName", "latitude", "longitude", "precipitation"
        ])

    df = pd.DataFrame(rows)
    return df
