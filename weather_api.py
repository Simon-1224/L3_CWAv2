"""Module for interacting with Central Weather Administration (CWA) Open Data API.

Fetches real-time observations and weather forecasts securely using HTTP requests,
with comprehensive error handling, timeout controls, and payload validation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

# Enable requests in Pyodide / WebAssembly environment
try:
    import pyodide_http

    pyodide_http.patch_all()
except ImportError:
    pass

import requests

import config

logger = logging.getLogger(__name__)


class WeatherAPIError(Exception):
    """Custom exception raised when CWA API requests fail."""

    pass


def mask_key(key: Optional[str]) -> str:
    """Return a masked representation of an API key for safe logging.

    Args:
        key: The raw API key string.

    Returns:
        str: Masked string, e.g. 'CWA-55F...4FB2'.
    """
    if not key:
        return "<None>"
    if len(key) <= 8:
        return "***"
    return f"{key[:7]}...{key[-4:]}"


def get_weather_data(
    dataset_id: str = config.DEFAULT_DATASET,
    location_name: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = config.REQUEST_TIMEOUT,
) -> Dict[str, Any]:
    """Fetch raw weather data from CWA Open Data API.

    Args:
        dataset_id: CWA dataset identifier (e.g., 'O-A0003-001' or 'F-C0032-001').
        location_name: Optional filter for specific county/station name.
        api_key: Optional CWA API Key override. If None, loaded via config.get_api_key().
        timeout: HTTP request timeout in seconds.

    Returns:
        Dict[str, Any]: Parsed JSON response dictionary.

    Raises:
        WeatherAPIError: If API key is missing, network fails, status code != 200,
                         or response payload indicates failure.
    """
    token = api_key or config.get_api_key()
    if not token or not token.strip():
        raise WeatherAPIError(
            "尚未設定 CWA API Key，請先設定 secrets.toml 或 .env 檔案。"
        )

    url = f"{config.CWA_BASE_URL}/{dataset_id}"
    params: Dict[str, Any] = {
        "Authorization": token.strip(),
    }
    if location_name:
        params["locationName"] = location_name

    logger.info(
        "Requesting CWA API: dataset=%s, location=%s, key=%s",
        dataset_id,
        location_name or "ALL",
        mask_key(token),
    )

    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise WeatherAPIError(
            f"中央氣象署 API 連線逾時（超過 {timeout} 秒），請檢查網路狀態。"
        ) from exc
    except requests.exceptions.HTTPError as exc:
        status_code = response.status_code if "response" in locals() else None
        if status_code in (401, 403):
            raise WeatherAPIError(
                "中央氣象署 API 授權失敗（HTTP 401/403），請確認 API Key 是否正確且有效。"
            ) from exc
        if status_code == 404:
            raise WeatherAPIError(
                f"請求的氣象資料集不存在 (HTTP 404: {dataset_id})，請確認資料集代碼。"
            ) from exc
        raise WeatherAPIError(
            f"中央氣象署 API 回傳 HTTP 錯誤碼 {status_code}。"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise WeatherAPIError(
            f"無法連線至中央氣象署 API：{type(exc).__name__}，請確認網路連線。"
        ) from exc

    try:
        data: Dict[str, Any] = response.json()
    except ValueError as exc:
        raise WeatherAPIError("中央氣象署 API 回應內容非合法的 JSON 格式。") from exc

    # CWA APIs usually include a 'success' field ('true' or True)
    success = str(data.get("success", "")).lower()
    if success not in ("true", "1"):
        msg = data.get("message") or "API 回應指出查詢未成功"
        raise WeatherAPIError(f"中央氣象署 API 錯誤：{msg}")

    return data


def get_observation_data(
    location_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper to fetch real-time station observation data (O-A0003-001)."""
    return get_weather_data(
        dataset_id=config.DATASET_OBSERVATION,
        location_name=location_name,
        api_key=api_key,
    )


def get_forecast_data(
    location_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper to fetch 36-hour general weather forecast (F-C0032-001)."""
    return get_weather_data(
        dataset_id=config.DATASET_FORECAST,
        location_name=location_name,
        api_key=api_key,
    )
