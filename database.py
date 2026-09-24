"""SQLite database access module for Taiwan Weather Forecast application.

Manages connection pooling, schema initialization, and SQL operations
for temperature forecasts and weather station observations.
Provides seamless in-memory fallback if sqlite3 is unavailable (e.g. WebAssembly stlite).
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

import config

logger = logging.getLogger(__name__)

# Detect whether native sqlite3 engine is available and functional
try:
    import sqlite3

    _test_conn = sqlite3.connect(":memory:")
    _test_conn.execute("CREATE TABLE _t (x INT)")
    _test_conn.execute("INSERT INTO _t VALUES (1)")
    _test_res = _test_conn.execute("SELECT x FROM _t").fetchone()
    _test_conn.close()
    HAS_NATIVE_SQLITE = bool(_test_res and _test_res[0] == 1)
except Exception as _exc:
    sqlite3 = None
    HAS_NATIVE_SQLITE = False
    logger.info("Native sqlite3 not available (%s), using in-memory weather storage fallback.", _exc)

# In-memory storage fallback
_IN_MEMORY_FORECASTS: List[Dict[str, Any]] = []
_IN_MEMORY_OBSERVATIONS: List[Dict[str, Any]] = []
_LATEST_UPDATED_TIME: Optional[str] = None


class _MockCursor:
    """Mock cursor for environments where sqlite3 is unavailable."""

    def __init__(self, conn: Any) -> None:
        self.conn = conn
        self.description = None
        self._rows: List[Any] = []

    def execute(self, sql: str, params: Any = None) -> _MockCursor:
        return self

    def executemany(self, sql: str, seq_of_params: Any) -> _MockCursor:
        return self

    def fetchone(self) -> Any:
        return None

    def fetchall(self) -> List[Any]:
        return []

    def close(self) -> None:
        pass


class _MockConnection:
    """Mock database connection for environments without native sqlite3."""

    row_factory: Any = None

    def __enter__(self) -> _MockConnection:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def cursor(self) -> _MockCursor:
        return _MockCursor(self)

    def execute(self, sql: str, params: Any = None) -> _MockCursor:
        return _MockCursor(self)

    def executemany(self, sql: str, seq_of_params: Any) -> _MockCursor:
        return _MockCursor(self)

    def commit(self) -> None:
        pass

    def close(self) -> None:
        pass


def get_db_connection(db_path: Optional[Union[str, Path]] = None) -> Any:
    """Create and return a new SQLite database connection or in-memory mock.

    Args:
        db_path: Path to SQLite database file. Defaults to config.DB_PATH.

    Returns:
        Connection object configured with Row factory, or _MockConnection.
    """
    if HAS_NATIVE_SQLITE and sqlite3 is not None:
        path = Path(db_path or config.DB_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        return conn
    return _MockConnection()


def init_database(db_path: Optional[Union[str, Path]] = None) -> None:
    """Initialize database tables with appropriate constraints and indices.

    Creates:
    - TemperatureForecasts: Stores forecast intervals (regionName, dataDate, startTime, etc.)
    - StationObservations: Stores real-time station observations and coordinates.
    """
    if HAS_NATIVE_SQLITE and sqlite3 is not None:
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
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_forecast_region ON TemperatureForecasts(regionName)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_forecast_date ON TemperatureForecasts(dataDate)"
                )

                # 2. StationObservations table
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
    else:
        logger.info("Initializing in-memory weather storage fallback (native sqlite3 unavailable).")


def insert_weather_data(
    df: pd.DataFrame,
    db_path: Optional[Union[str, Path]] = None,
    table_name: str = "TemperatureForecasts",
) -> int:
    """Insert or update weather records into SQLite or in-memory storage fallback.

    Args:
        df: Cleaned Pandas DataFrame.
        db_path: Path to SQLite DB.
        table_name: Target table ('TemperatureForecasts' or 'StationObservations').

    Returns:
        int: Number of rows successfully inserted or updated.
    """
    if df.empty:
        return 0

    if HAS_NATIVE_SQLITE and sqlite3 is not None:
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
            return inserted_count
        finally:
            conn.close()

    # In-memory storage fallback
    global _IN_MEMORY_FORECASTS, _IN_MEMORY_OBSERVATIONS, _LATEST_UPDATED_TIME
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _LATEST_UPDATED_TIME = now_str

    if table_name == "TemperatureForecasts":
        existing_map = {
            (r["regionName"], r["startTime"], r["endTime"]): i
            for i, r in enumerate(_IN_MEMORY_FORECASTS)
        }
        for _, row in df.iterrows():
            rec = {
                "id": len(_IN_MEMORY_FORECASTS) + 1,
                "regionName": str(row.get("regionName", "")),
                "dataDate": str(row.get("dataDate", "")),
                "startTime": str(row.get("startTime", "")),
                "endTime": str(row.get("endTime", "")),
                "Wx": str(row.get("Wx", "多雲")),
                "PoP": float(row.get("PoP", 0.0)) if pd.notna(row.get("PoP")) else 0.0,
                "MinT": float(row.get("MinT", 20.0)) if pd.notna(row.get("MinT")) else 20.0,
                "MaxT": float(row.get("MaxT", 28.0)) if pd.notna(row.get("MaxT")) else 28.0,
                "temp": float(row.get("temp", 0.0)) if pd.notna(row.get("temp")) else None,
                "updatedAt": now_str,
            }
            key = (rec["regionName"], rec["startTime"], rec["endTime"])
            if key in existing_map:
                _IN_MEMORY_FORECASTS[existing_map[key]] = rec
            else:
                existing_map[key] = len(_IN_MEMORY_FORECASTS)
                _IN_MEMORY_FORECASTS.append(rec)
        return len(df)

    elif table_name == "StationObservations":
        existing_map = {
            r["stationId"]: i
            for i, r in enumerate(_IN_MEMORY_OBSERVATIONS)
        }
        for _, row in df.iterrows():
            st_id = str(row.get("stationId", ""))
            if not st_id:
                continue
            rec = {
                "id": len(_IN_MEMORY_OBSERVATIONS) + 1,
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
                "updatedAt": now_str,
            }
            if st_id in existing_map:
                _IN_MEMORY_OBSERVATIONS[existing_map[st_id]] = rec
            else:
                existing_map[st_id] = len(_IN_MEMORY_OBSERVATIONS)
                _IN_MEMORY_OBSERVATIONS.append(rec)
        return len(df)

    return 0


def query_weather_by_region(
    region_name: str,
    db_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """Query weather forecasts for a specific region/county."""
    if HAS_NATIVE_SQLITE and sqlite3 is not None:
        try:
            conn = get_db_connection(db_path)
            try:
                query = """
                    SELECT id, regionName, dataDate, startTime, endTime, Wx, PoP, MinT, MaxT, temp, updatedAt
                    FROM TemperatureForecasts
                    WHERE regionName = ?
                    ORDER BY startTime ASC
                """
                return pd.read_sql_query(query, conn, params=(region_name,))
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("SQLite query failed, falling back to in-memory: %s", exc)

    records = [r for r in _IN_MEMORY_FORECASTS if r.get("regionName") == region_name]
    cols = ["id", "regionName", "dataDate", "startTime", "endTime", "Wx", "PoP", "MinT", "MaxT", "temp", "updatedAt"]
    if not records:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(records)
    return df.sort_values(by="startTime").reset_index(drop=True)


def query_weather_by_date(
    date_str: str,
    db_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """Query weather forecasts for a specific date (YYYY-MM-DD)."""
    if HAS_NATIVE_SQLITE and sqlite3 is not None:
        try:
            conn = get_db_connection(db_path)
            try:
                query = """
                    SELECT id, regionName, dataDate, startTime, endTime, Wx, PoP, MinT, MaxT, temp, updatedAt
                    FROM TemperatureForecasts
                    WHERE dataDate = ?
                    ORDER BY regionName, startTime ASC
                """
                return pd.read_sql_query(query, conn, params=(date_str,))
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("SQLite query failed, falling back to in-memory: %s", exc)

    records = [r for r in _IN_MEMORY_FORECASTS if r.get("dataDate") == date_str]
    cols = ["id", "regionName", "dataDate", "startTime", "endTime", "Wx", "PoP", "MinT", "MaxT", "temp", "updatedAt"]
    if not records:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(records)
    return df.sort_values(by=["regionName", "startTime"]).reset_index(drop=True)


def query_all_weather(
    db_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """Query all weather forecast records from SQLite or in-memory fallback."""
    if HAS_NATIVE_SQLITE and sqlite3 is not None:
        try:
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
        except Exception as exc:
            logger.warning("SQLite query failed, falling back to in-memory: %s", exc)

    cols = ["id", "regionName", "dataDate", "startTime", "endTime", "Wx", "PoP", "MinT", "MaxT", "temp", "updatedAt"]
    if not _IN_MEMORY_FORECASTS:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(_IN_MEMORY_FORECASTS)
    return df.sort_values(by=["regionName", "startTime"]).reset_index(drop=True)


def query_all_observations(
    region_name: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """Query real-time station observations with geographic coordinates."""
    if HAS_NATIVE_SQLITE and sqlite3 is not None:
        try:
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
        except Exception as exc:
            logger.warning("SQLite query failed, falling back to in-memory: %s", exc)

    cols = [
        "id", "stationId", "stationName", "regionName", "townName", "dataDate",
        "startTime", "endTime", "Wx", "temp", "MinT", "MaxT", "PoP", "precipitation",
        "latitude", "longitude", "updatedAt"
    ]
    if not _IN_MEMORY_OBSERVATIONS:
        return pd.DataFrame(columns=cols)

    if region_name:
        records = [r for r in _IN_MEMORY_OBSERVATIONS if r.get("regionName") == region_name]
        if not records:
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame(records)
        return df.sort_values(by="temp", ascending=False).reset_index(drop=True)
    else:
        df = pd.DataFrame(_IN_MEMORY_OBSERVATIONS)
        return df.sort_values(by=["regionName", "stationName"]).reset_index(drop=True)


def get_latest_updated_time(db_path: Optional[Union[str, Path]] = None) -> Optional[str]:
    """Retrieve the most recent update timestamp from SQLite or in-memory fallback."""
    if HAS_NATIVE_SQLITE and sqlite3 is not None:
        try:
            conn = get_db_connection(db_path)
            try:
                cur = conn.cursor()
                cur.execute("SELECT MAX(updatedAt) FROM TemperatureForecasts")
                row = cur.fetchone()
                if row and row[0]:
                    return str(row[0])
                cur.execute("SELECT MAX(updatedAt) FROM StationObservations")
                row = cur.fetchone()
                if row and row[0]:
                    return str(row[0])
            finally:
                conn.close()
        except Exception:
            pass

    return _LATEST_UPDATED_TIME


def clear_old_data(db_path: Optional[Union[str, Path]] = None) -> None:
    """Clear all records from database tables or in-memory fallback."""
    if HAS_NATIVE_SQLITE and sqlite3 is not None:
        try:
            conn = get_db_connection(db_path)
            try:
                with conn:
                    conn.execute("DELETE FROM TemperatureForecasts")
                    conn.execute("DELETE FROM StationObservations")
            finally:
                conn.close()
        except Exception:
            pass

    global _IN_MEMORY_FORECASTS, _IN_MEMORY_OBSERVATIONS, _LATEST_UPDATED_TIME
    _IN_MEMORY_FORECASTS.clear()
    _IN_MEMORY_OBSERVATIONS.clear()
    _LATEST_UPDATED_TIME = None
