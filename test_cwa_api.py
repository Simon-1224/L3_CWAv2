"""Diagnostic test script for verifying CWA Open Data API connection and payloads."""

from __future__ import annotations

import sys
import time

import config
import weather_api


def run_tests() -> bool:
    print("=" * 60)
    print(" CWA Open Data API Verification Test")
    print("=" * 60)

    # 1. Check API Key
    key = config.get_api_key()
    if not key:
        print("[FAIL] CWA API Key is missing! Please configure .env or secrets.toml.")
        return False
    print(f"[PASS] API Key loaded successfully: {weather_api.mask_key(key)}")

    all_passed = True

    # 2. Test Dataset O-A0003-001 (Observation)
    print("-" * 60)
    print(f"Testing Dataset: {config.DATASET_OBSERVATION} (實測觀測資料)...")
    start_time = time.time()
    try:
        data_obs = weather_api.get_observation_data()
        elapsed = time.time() - start_time
        records = data_obs.get("records", {})
        stations = records.get("Station", [])
        print(f"[PASS] HTTP 200 OK (Latency: {elapsed:.2f}s)")
        print(f"       Total Stations Retrieved: {len(stations)}")
        if stations:
            sample = stations[0]
            st_name = sample.get("StationName")
            county = sample.get("GeoInfo", {}).get("CountyName")
            temp = sample.get("WeatherElement", {}).get("AirTemperature")
            weather = sample.get("WeatherElement", {}).get("Weather")
            print(f"       Sample: 測站={st_name}, 縣市={county}, 氣溫={temp}°C, 天氣={weather}")
    except Exception as exc:
        print(f"[FAIL] Error fetching {config.DATASET_OBSERVATION}: {exc}")
        all_passed = False

    # 3. Test Dataset F-C0032-001 (Forecast)
    print("-" * 60)
    print(f"Testing Dataset: {config.DATASET_FORECAST} (各縣市一般天氣預報)...")
    start_time = time.time()
    try:
        data_fc = weather_api.get_forecast_data()
        elapsed = time.time() - start_time
        records = data_fc.get("records", {})
        locations = records.get("location", [])
        print(f"[PASS] HTTP 200 OK (Latency: {elapsed:.2f}s)")
        print(f"       Total Locations Retrieved: {len(locations)}")
        if locations:
            sample = locations[0]
            loc_name = sample.get("locationName")
            elements = [e.get("elementName") for e in sample.get("weatherElement", [])]
            print(f"       Sample: 縣市={loc_name}, 預報元素={elements}")
    except Exception as exc:
        print(f"[FAIL] Error fetching {config.DATASET_FORECAST}: {exc}")
        all_passed = False

    # 4. Test Error Handling (Invalid Token)
    print("-" * 60)
    print("Testing Error Handling: Invalid Token rejection...")
    try:
        weather_api.get_weather_data(api_key="CWA-INVALID-TEST-KEY")
        print("[FAIL] Invalid key unexpectedly succeeded!")
        all_passed = False
    except weather_api.WeatherAPIError as exc:
        print(f"[PASS] Expected exception caught: {exc}")

    print("=" * 60)
    if all_passed:
        print(">>> ALL CWA API TESTS PASSED SUCCESSFULLY! <<<")
    else:
        print(">>> SOME TESTS FAILED. PLEASE CHECK LOGS. <<<")
    print("=" * 60)
    return all_passed


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
