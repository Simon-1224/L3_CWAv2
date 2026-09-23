"""Verification test for data_processor.py (JSON -> Pandas DataFrame)."""

from __future__ import annotations

import sys
import pandas as pd
import data_processor
import weather_api


def test_parsing() -> bool:
    print("=" * 60)
    print(" Testing data_processor: JSON -> DataFrame")
    print("=" * 60)

    # 1. Test Forecast Parsing (F-C0032-001)
    print("1. Testing Forecast Parsing (F-C0032-001)...")
    fc_json = weather_api.get_forecast_data()
    df_fc = data_processor.parse_forecast_json(fc_json)
    print(f"   [PASS] Forecast DataFrame created: shape={df_fc.shape}")
    expected_cols = ["regionName", "dataDate", "startTime", "endTime", "Wx", "PoP", "MinT", "MaxT"]
    for col in expected_cols:
        assert col in df_fc.columns, f"Missing column: {col}"
    print(f"   [PASS] All expected columns present: {expected_cols}")
    print(f"   Sample rows:\n{df_fc[['regionName', 'dataDate', 'Wx', 'MinT', 'MaxT', 'PoP']].head(3)}")

    # Check numeric types
    assert pd.api.types.is_numeric_dtype(df_fc["MinT"]), "MinT is not numeric"
    assert pd.api.types.is_numeric_dtype(df_fc["MaxT"]), "MaxT is not numeric"
    assert pd.api.types.is_numeric_dtype(df_fc["PoP"]), "PoP is not numeric"
    print("   [PASS] Numeric conversions validated successfully.")

    # 2. Test Observation Parsing (O-A0003-001)
    print("-" * 60)
    print("2. Testing Observation Parsing (O-A0003-001)...")
    obs_json = weather_api.get_observation_data()
    df_obs = data_processor.parse_observation_json(obs_json)
    print(f"   [PASS] Observation DataFrame created: shape={df_obs.shape}")
    print(f"   Sample rows:\n{df_obs[['regionName', 'stationName', 'temp', 'Wx', 'MinT', 'MaxT']].head(3)}")
    assert len(df_obs) > 0, "Observation DataFrame is empty"
    print(f"   [PASS] Successfully parsed {len(df_obs)} station records.")

    print("=" * 60)
    print(">>> STEP 6 TEST PASSED: JSON -> DataFrame Verified! <<<")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_parsing()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[FAIL] Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
