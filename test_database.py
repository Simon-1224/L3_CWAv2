"""Verification test for database.py (DataFrame -> SQLite -> SQL Query)."""

from __future__ import annotations

import sys
import config
import database
import data_processor
import weather_api


def test_database_operations() -> bool:
    print("=" * 60)
    print(" Testing database: DataFrame -> SQLite -> SQL Query")
    print("=" * 60)

    # 1. Initialize Database
    print("1. Initializing database schema...")
    database.init_database()
    assert config.DB_PATH.exists(), f"Database file not created at {config.DB_PATH}"
    print(f"   [PASS] Database initialized at: {config.DB_PATH}")

    # 2. Fetch data & Parse into DataFrames
    print("-" * 60)
    print("2. Fetching & parsing data for database insertion...")
    fc_json = weather_api.get_forecast_data()
    df_fc = data_processor.parse_forecast_json(fc_json)

    obs_json = weather_api.get_observation_data()
    df_obs = data_processor.parse_observation_json(obs_json)

    # 3. Test Insertion
    print("3. Testing insert_weather_data()...")
    fc_count1 = database.insert_weather_data(df_fc, table_name="TemperatureForecasts")
    obs_count1 = database.insert_weather_data(df_obs, table_name="StationObservations")
    print(f"   [PASS] Inserted {fc_count1} forecast rows and {obs_count1} observation rows.")

    # Test Deduplication (re-insert should update, not duplicate)
    fc_count2 = database.insert_weather_data(df_fc, table_name="TemperatureForecasts")
    df_all = database.query_all_weather()
    assert len(df_all) == fc_count1, f"Deduplication failed! Expected {fc_count1}, got {len(df_all)}"
    print(f"   [PASS] Deduplication verified: Re-insert maintains exact count ({len(df_all)} rows).")

    # 4. Test Region Query
    print("-" * 60)
    test_region = "臺中市"
    print(f"4. Testing query_weather_by_region('{test_region}')...")
    df_region = database.query_weather_by_region(test_region)
    print(f"   [PASS] Returned {len(df_region)} forecast records for {test_region}.")
    assert len(df_region) > 0, f"No records returned for {test_region}"
    print(f"   Sample forecast:\n{df_region[['startTime', 'Wx', 'MinT', 'MaxT', 'PoP']].head(2)}")

    # 5. Test Date Query
    print("-" * 60)
    first_date = df_region.iloc[0]["dataDate"]
    print(f"5. Testing query_weather_by_date('{first_date}')...")
    df_date = database.query_weather_by_date(first_date)
    print(f"   [PASS] Returned {len(df_date)} records across regions for date {first_date}.")
    assert len(df_date) > 0, "No records returned for date query"

    # 6. Test Observations Query
    print("-" * 60)
    print("6. Testing query_all_observations()...")
    df_stations = database.query_all_observations()
    print(f"   [PASS] Returned {len(df_stations)} observation stations from SQLite.")
    assert len(df_stations) > 0, "No station observations found"

    # 7. Test Latest Timestamp
    updated_time = database.get_latest_updated_time()
    print(f"   [PASS] Latest updated timestamp: {updated_time}")
    assert updated_time is not None, "Latest timestamp is None"

    print("=" * 60)
    print(">>> STEP 8 TEST PASSED: Database & SQL Pipeline Verified! <<<")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_database_operations()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[FAIL] Error during database testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
