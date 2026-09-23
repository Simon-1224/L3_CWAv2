"""SQLite database access module for Taiwan Weather Forecast application.

Manages connection pooling, schema initialization, and SQL operations
for temperature forecasts and weather station observations.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

import config

logger = logging.getLogger(__name__)


def get_db_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Create and return a new SQLite database connection.

    Args:
        db_path: Path to SQLite database file. Defaults to config.DB_PATH.

    Returns:
        sqlite3.Connection: Database connection configured with Row factory.
    """
    path = Path(db_path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: Optional[Union[str, Path]] = None) -> None:
    """Initialize database tables with appropriate constraints and indices.

    Creates:
    - TemperatureForecasts: Stores forecast intervals (regionName, dataDate, startTime, etc.)
    - StationObservations: Stores real-time station observations and coordinates.
    """
    conn = get_db_connection(db_path)
    try:
        with conn:
            # 1. TemperatureForecasts table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS TemperatureForecasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    regionName TEXT NOT NULL,
                    dataDate TEXT NOT NULL,
                    startTime TEXT NOT NULL,
                    endTime TEXT NOT NULL,
                    Wx TEXT,
                    PoP REAL,
                    MinT REAL,
                    MaxT REAL,
                    temp REAL,
                    updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_region_time UNIQUE (regionName, startTime, endTime)
                )
                """
            )

            # Indices for fast queries
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_forecast_region ON TemperatureForecasts(regionName)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_forecast_date ON TemperatureForecasts(dataDate)"
            )

            # 2. StationObservations table (for O-A0003-001 observation map & details)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS StationObservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stationId TEXT UNIQUE NOT NULL,
                    stationName TEXT NOT NULL,
                    regionName TEXT NOT NULL,
                    townName TEXT,
                    dataDate TEXT,
                    startTime TEXT,
                    endTime TEXT,
                    Wx TEXT,
                    temp REAL,
                    MinT REAL,
                    MaxT REAL,
                    PoP REAL,
                    precipitation REAL,
                    latitude REAL,
                    longitude REAL,
                    updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_station_region ON StationObservations(regionName)"
            )
    finally:
        conn.close()


def insert_weather_data(
    df: pd.DataFrame,
    db_path: Optional[Union[str, Path]] = None,
    table_name: str = "TemperatureForecasts",
) -> int:
    """Insert or update weather records into SQLite from a DataFrame.

    Uses INSERT OR REPLACE to prevent duplicate entries while updating existing keys.

    Args:
        df: Cleaned Pandas DataFrame.
        db_path: Path to SQLite DB.
        table_name: Target table ('TemperatureForecasts' or 'StationObservations').

    Returns:
        int: Number of rows successfully inserted or updated.
    """
    if df.empty:
        return 0

    conn = get_db_connection(db_path)
    inserted_count = 0
    try:
        with conn:
            if table_name == "TemperatureForecasts":
                sql = """
                    INSERT INTO TemperatureForecasts
                    (regionName, dataDate, startTime, endTime, Wx, PoP, MinT, MaxT, temp)
                    VALUES (:regionName, :dataDate, :startTime, :endTime, :Wx, :PoP, :MinT, :MaxT, :temp)
                    ON CONFLICT(regionName, startTime, endTime) DO UPDATE SET
                        dataDate=excluded.dataDate,
                        Wx=excluded.Wx,
                        PoP=excluded.PoP,
                        MinT=excluded.MinT,
                        MaxT=excluded.MaxT,
                        temp=excluded.temp,
                        updatedAt=CURRENT_TIMESTAMP
                """
                records = []
                for _, row in df.iterrows():
                    records.append({
                        "regionName": str(row.get("regionName", "")),
                        "dataDate": str(row.get("dataDate", "")),
                        "startTime": str(row.get("startTime", "")),
                        "endTime": str(row.get("endTime", "")),
                        "Wx": str(row.get("Wx", "多雲")),
                        "PoP": float(row.get("PoP", 0.0)) if pd.notna(row.get("PoP")) else 0.0,
                        "MinT": float(row.get("MinT", 20.0)) if pd.notna(row.get("MinT")) else 20.0,
                        "MaxT": float(row.get("MaxT", 28.0)) if pd.notna(row.get("MaxT")) else 28.0,
                        "temp": float(row.get("temp", 0.0)) if pd.notna(row.get("temp")) else None,
                    })
                conn.executemany(sql, records)
                inserted_count = len(records)

            elif table_name == "StationObservations":
                sql = """
                    INSERT INTO StationObservations
                    (stationId, stationName, regionName, townName, dataDate, startTime, endTime,
                     Wx, temp, MinT, MaxT, PoP, precipitation, latitude, longitude)
                    VALUES
                    (:stationId, :stationName, :regionName, :townName, :dataDate, :startTime, :endTime,
                     :Wx, :temp, :MinT, :MaxT, :PoP, :precipitation, :latitude, :longitude)
                    ON CONFLICT(stationId) DO UPDATE SET
                        stationName=excluded.stationName,
                        regionName=excluded.regionName,
                        townName=excluded.townName,
                        dataDate=excluded.dataDate,
                        startTime=excluded.startTime,
                        endTime=excluded.endTime,
                        Wx=excluded.Wx,
                        temp=excluded.temp,
                        MinT=excluded.MinT,
                        MaxT=excluded.MaxT,
                        PoP=excluded.PoP,
                        precipitation=excluded.precipitation,
                        latitude=excluded.latitude,
                        longitude=excluded.longitude,
                        updatedAt=CURRENT_TIMESTAMP
                """
                records = []
                for _, row in df.iterrows():
                    st_id = str(row.get("stationId", ""))
                    if not st_id:
                        continue
                    records.append({
                        "stationId": st_id,
                        "stationName": str(row.get("stationName", "")),
                        "regionName": str(row.get("regionName", "")),
                        "townName": str(row.get("townName", "")),
                        "dataDate": str(row.get("dataDate", "")),
                        "startTime": str(row.get("startTime", "")),
                        "endTime": str(row.get("endTime", "")),
                        "Wx": str(row.get("Wx", "多雲")),
                        "temp": float(row.get("temp")) if pd.notna(row.get("temp")) else None,
                        "MinT": float(row.get("MinT")) if pd.notna(row.get("MinT")) else None,
                        "MaxT": float(row.get("MaxT")) if pd.notna(row.get("MaxT")) else None,
                        "PoP": float(row.get("PoP")) if pd.notna(row.get("PoP")) else None,
                        "precipitation": float(row.get("precipitation")) if pd.notna(row.get("precipitation")) else 0.0,
                        "latitude": float(row.get("latitude")) if pd.notna(row.get("latitude")) else None,
                        "longitude": float(row.get("longitude")) if pd.notna(row.get("longitude")) else None,
                    })
                conn.executemany(sql, records)
                inserted_count = len(records)
    finally:
        conn.close()

    return inserted_count


def query_weather_by_region(
    region_name: str,
    db_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """Query weather forecasts for a specific region/county.

    SQL:
        SELECT * FROM TemperatureForecasts WHERE regionName = ? ORDER BY startTime;
    """
    conn = get_db_connection(db_path)
    try:
        query = """
            SELECT id, regionName, dataDate, startTime, endTime, Wx, PoP, MinT, MaxT, temp, updatedAt
            FROM TemperatureForecasts
            WHERE regionName = ?
            ORDER BY startTime ASC
        """
        df = pd.read_sql_query(query, conn, params=(region_name,))
        return df
    finally:
        conn.close()


def query_weather_by_date(
    date_str: str,
    db_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """Query weather forecasts for a specific date (YYYY-MM-DD).

    SQL:
        SELECT * FROM TemperatureForecasts WHERE dataDate = ? ORDER BY regionName, startTime;
    """
    conn = get_db_connection(db_path)
    try:
        query = """
            SELECT id, regionName, dataDate, startTime, endTime, Wx, PoP, MinT, MaxT, temp, updatedAt
            FROM TemperatureForecasts
            WHERE dataDate = ?
            ORDER BY regionName, startTime ASC
        """
        df = pd.read_sql_query(query, conn, params=(date_str,))
        return df
    finally:
        conn.close()


def query_all_weather(
    db_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """Query all weather forecast records from SQLite."""
    conn = get_db_connection(db_path)
    try:
        query = """
            SELECT id, regionName, dataDate, startTime, endTime, Wx, PoP, MinT, MaxT, temp, updatedAt
            FROM TemperatureForecasts
            ORDER BY regionName, startTime ASC
        """
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def query_all_observations(
    region_name: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """Query real-time station observations with geographic coordinates.

    Used by Folium map and local detailed station cards.
    """
    conn = get_db_connection(db_path)
    try:
        if region_name:
            query = """
                SELECT * FROM StationObservations
                WHERE regionName = ?
                ORDER BY temp DESC
            """
            return pd.read_sql_query(query, conn, params=(region_name,))
        else:
            query = "SELECT * FROM StationObservations ORDER BY regionName, stationName"
            return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def get_latest_updated_time(db_path: Optional[Union[str, Path]] = None) -> Optional[str]:
    """Retrieve the most recent update timestamp from the database."""
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT MAX(updatedAt) FROM TemperatureForecasts")
        row = cur.fetchone()
        if row and row[0]:
            return str(row[0])
        cur.execute("SELECT MAX(updatedAt) FROM StationObservations")
        row = cur.fetchone()
        return str(row[0]) if row and row[0] else None
    finally:
        conn.close()


def clear_old_data(db_path: Optional[Union[str, Path]] = None) -> None:
    """Clear all records from database tables."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM TemperatureForecasts")
            conn.execute("DELETE FROM StationObservations")
    finally:
        conn.close()
