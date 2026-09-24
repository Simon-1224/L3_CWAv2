"""Central configuration module for Taiwan Weather Forecast application.

Handles environment variables, API endpoints, dataset IDs, database path,
and geographic reference constants for Taiwan counties and cities.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Base Directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STREAMLIT_SECRETS_PATH = BASE_DIR / ".streamlit" / "secrets.toml"
ENV_PATH = BASE_DIR / ".env"

# Database Configuration
DB_PATH = BASE_DIR / "data.db"

# CWA API Endpoints & Datasets
CWA_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
# O-A0003-001: 中央氣象署自動氣象站(氣象觀測資料) - 全台363個觀測站即時觀測資料
DATASET_OBSERVATION = "O-A0003-001"
# F-C0032-001: 一般天氣預報-今明36小時天氣預報 (包含 22 縣市 Wx, PoP, MinT, MaxT)
DATASET_FORECAST = "F-C0032-001"
DEFAULT_DATASET = DATASET_OBSERVATION

# HTTP Client Settings
REQUEST_TIMEOUT = 15  # seconds

# 臺灣 22 縣市標準清單 (照地理分區排列)
TAIWAN_COUNTIES: List[str] = [
    "臺北市",
    "新北市",
    "桃園市",
    "臺中市",
    "臺南市",
    "高雄市",
    "基隆市",
    "新竹市",
    "新竹縣",
    "苗栗縣",
    "彰化縣",
    "南投縣",
    "雲林縣",
    "嘉義市",
    "嘉義縣",
    "屏東縣",
    "宜蘭縣",
    "花蓮縣",
    "臺東縣",
    "澎湖縣",
    "金門縣",
    "連江縣",
]

# 22 縣市代表性地理經緯度座標 (WGS84 [緯度 Latitude, 經度 Longitude])
COUNTY_COORDINATES: Dict[str, Tuple[float, float]] = {
    "臺北市": (25.0375, 121.5637),
    "新北市": (25.0118, 121.4658),
    "桃園市": (24.9936, 121.3010),
    "臺中市": (24.1627, 120.6473),
    "臺南市": (22.9997, 120.2270),
    "高雄市": (22.6273, 120.3014),
    "基隆市": (25.1276, 121.7392),
    "新竹市": (24.8138, 120.9675),
    "新竹縣": (24.8387, 121.0177),
    "苗栗縣": (24.5602, 120.8214),
    "彰化縣": (24.0817, 120.5385),
    "南投縣": (23.9037, 120.6859),
    "雲林縣": (23.7092, 120.4313),
    "嘉義市": (23.4800, 120.4491),
    "嘉義縣": (23.4518, 120.2559),
    "屏東縣": (22.6761, 120.4941),
    "宜蘭縣": (24.7021, 121.7377),
    "花蓮縣": (23.9922, 121.6016),
    "臺東縣": (22.7583, 121.1444),
    "澎湖縣": (23.5712, 119.5793),
    "金門縣": (24.4493, 118.3766),
    "連江縣": (26.1505, 119.9499),
}


def get_api_key() -> Optional[str]:
    """Retrieve the CWA API Key from session_state, environment, .streamlit/secrets.toml, or .env.

    Resolution precedence:
    0. st.session_state["user_cwa_api_key"] (for WebAssembly / stlite user input)
    1. os.environ["CWA_API_KEY"]
    2. .streamlit/secrets.toml
    3. .env file

    Returns:
        Optional[str]: The API key string if found, otherwise None.
    """
    # 0. Check Streamlit session_state & secrets (crucial for stlite WebAssembly)
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx(suppress_warning=True) is not None:
            if "user_cwa_api_key" in st.session_state and st.session_state["user_cwa_api_key"]:
                key_candidate = str(st.session_state["user_cwa_api_key"]).strip()
                if key_candidate:
                    return key_candidate
            if hasattr(st, "secrets") and "CWA_API_KEY" in st.secrets:
                key_candidate = str(st.secrets["CWA_API_KEY"]).strip()
                if key_candidate:
                    return key_candidate
    except Exception:
        pass

    # 1. Check os.environ
    env_key = os.environ.get("CWA_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    # 2. Try loading from .streamlit/secrets.toml
    if STREAMLIT_SECRETS_PATH.exists():
        try:
            import tomllib

            content = STREAMLIT_SECRETS_PATH.read_text(encoding="utf-8")
            secrets_data = tomllib.loads(content)
            key = secrets_data.get("CWA_API_KEY")
            if key and str(key).strip():
                return str(key).strip()
        except Exception:
            pass

    # 3. Try parsing .env manually or with dotenv
    if ENV_PATH.exists():
        try:
            for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "CWA_API_KEY":
                        val = v.strip().strip("'\"")
                        if val:
                            return val
        except Exception:
            pass

    return None
