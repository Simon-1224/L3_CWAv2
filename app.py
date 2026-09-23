"""Taiwan Weather Forecast - Interactive Weather Analytics Web Application.

Central Weather Administration (CWA) Open Data API x Python x SQLite x Streamlit.
"""

from __future__ import annotations

import datetime
import logging
from typing import Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

import config
import database
import data_processor
import map_utils
import weather_api

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit Page Config
st.set_page_config(
    page_title="Taiwan Weather Forecast | 臺灣氣象預報儀表板",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Clean Blue-White Tech Card UI)
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans TC', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 24px 32px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.25);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .main-header p {
        margin: 8px 0 0 0;
        font-size: 1.05rem;
        opacity: 0.9;
    }

    /* Metric Cards */
    .metric-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .metric-icon {
        font-size: 2rem;
        margin-bottom: 8px;
    }
    .metric-label {
        font-size: 0.9rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0F172A;
        margin: 4px 0;
    }

    /* Section Headers */
    .section-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1E293B;
        margin-top: 20px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* St.button style */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%);
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# Database Initialization & Data Loading Helpers
@st.cache_resource
def ensure_database_initialized() -> None:
    """Ensure database schema exists on application start."""
    try:
        database.init_database()
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)
        st.error("資料庫初始化失敗，請確認檔案讀寫權限。")


def fetch_and_save_weather() -> Tuple[bool, str]:
    """Fetch data from CWA API and persist to SQLite.

    Updates both 36h forecast (F-C0032-001) and real-time station observations (O-A0003-001).

    Returns:
        Tuple[bool, str]: Success flag and status message.
    """
    api_key = config.get_api_key()
    if not api_key:
        return False, "尚未設定 CWA API Key，請先設定 secrets.toml 或 .env 檔案。"

    try:
        # 1. Fetch & Store 36h Forecasts
        fc_json = weather_api.get_forecast_data(api_key=api_key)
        df_fc = data_processor.parse_forecast_json(fc_json)
        database.insert_weather_data(df_fc, table_name="TemperatureForecasts")

        # 2. Fetch & Store Real-time Observations (363 Stations)
        try:
            obs_json = weather_api.get_observation_data(api_key=api_key)
            df_obs = data_processor.parse_observation_json(obs_json)
            database.insert_weather_data(df_obs, table_name="StationObservations")
        except Exception as obs_err:
            logger.warning("Observation update warning: %s", obs_err)

        # Clear cached queries so dashboard refreshes
        load_weather_data.clear()
        load_observations.clear()
        return True, "天氣資料更新成功！"
    except weather_api.WeatherAPIError as exc:
        return False, str(exc)
    except Exception as exc:
        logger.error("Unexpected update failure: %s", exc)
        return False, f"更新過程發生錯誤：{exc}"


@st.cache_data(ttl=600)
def load_weather_data(region_name: Optional[str] = None) -> pd.DataFrame:
    """Load weather forecast records from SQLite with caching."""
    try:
        if region_name:
            return database.query_weather_by_region(region_name)
        return database.query_all_weather()
    except Exception as exc:
        logger.error("Database read error: %s", exc)
        st.error("資料庫讀取失敗。")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_observations(region_name: Optional[str] = None) -> pd.DataFrame:
    """Load station observations from SQLite with caching."""
    try:
        return database.query_all_observations(region_name=region_name)
    except Exception as exc:
        logger.error("Observation read error: %s", exc)
        return pd.DataFrame()


def render_temperature_chart(df: pd.DataFrame, region_name: str) -> go.Figure:
    """Build an interactive Plotly temperature trend line chart."""
    fig = go.Figure()

    if df.empty:
        fig.add_annotation(
            text="目前沒有溫度預報資料",
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=16, color="#64748B"),
        )
        return fig

    # Format x-axis labels: e.g. "09/23 18:00 ~ 09/24 06:00"
    x_labels = []
    for _, row in df.iterrows():
        st_val = str(row["startTime"])[5:16]  # MM-DD HH:MM
        et_val = str(row["endTime"])[5:16]
        x_labels.append(f"{st_val} ~ {et_val}")

    # Highest Temperature Line (MaxT)
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["MaxT"],
            mode="lines+markers+text",
            name="最高溫 (MaxT)",
            line=dict(color="#EF4444", width=3, shape="spline"),
            marker=dict(size=9, color="#DC2626"),
            text=[f"{v:.0f}°C" for v in df["MaxT"]],
            textposition="top center",
            hovertemplate="時段: %{x}<br>最高溫: %{y:.1f} °C<extra></extra>",
        )
    )

    # Lowest Temperature Line (MinT)
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=df["MinT"],
            mode="lines+markers+text",
            name="最低溫 (MinT)",
            line=dict(color="#2563EB", width=3, shape="spline"),
            marker=dict(size=9, color="#1D4ED8"),
            text=[f"{v:.0f}°C" for v in df["MinT"]],
            textposition="bottom center",
            hovertemplate="時段: %{x}<br>最低溫: %{y:.1f} °C<extra></extra>",
        )
    )

    # Styling Layout
    fig.update_layout(
        title=f"📈 {region_name} - 未來溫度預報折線圖",
        title_font=dict(size=18, color="#0F172A", family="Inter, Noto Sans TC"),
        xaxis=dict(
            title="預報時段",
            gridcolor="#F1F5F9",
            tickangle=-15,
            titlefont=dict(size=14, color="#475569"),
        ),
        yaxis=dict(
            title="溫度 (°C)",
            gridcolor="#E2E8F0",
            zeroline=False,
            titlefont=dict(size=14, color="#475569"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=12),
        ),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=60),
    )
    return fig


def main() -> None:
    """Main application lifecycle."""
    ensure_database_initialized()

    # If database is completely empty on launch, attempt initial fetch automatically
    df_check = load_weather_data()
    if df_check.empty and config.get_api_key():
        fetch_and_save_weather()

    # ------------------ SIDEBAR ------------------
    st.sidebar.markdown("## 🌤️ Weather Forecast")
    st.sidebar.markdown("---")

    # 1. County Selection
    selected_region = st.sidebar.selectbox(
        "📍 選擇台灣地區",
        options=config.TAIWAN_COUNTIES,
        index=3,  # Default: 臺中市
    )

    # 2. Date Selection (derived from available dates in DB)
    all_df = load_weather_data(selected_region)
    available_dates = (
        sorted(all_df["dataDate"].unique().tolist())
        if not all_df.empty
        else [datetime.date.today().strftime("%Y-%m-%d")]
    )
    selected_date = st.sidebar.selectbox(
        "📅 選擇日期",
        options=available_dates,
        index=0,
    )

    # 3. Manual Refresh Button
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔄 資料同步")
    if st.sidebar.button("🔄 更新氣象資料"):
        with st.spinner("正在向中央氣象署請求最新天氣資料..."):
            success, msg = fetch_and_save_weather()
            if success:
                st.sidebar.success(msg)
                st.rerun()
            else:
                st.sidebar.error(msg)

    # 4. Last Updated Timestamp
    last_update = database.get_latest_updated_time()
    if last_update:
        st.sidebar.caption(f"🕒 資料最後更新時間：\n**{last_update}**")
    else:
        st.sidebar.caption("🕒 資料狀態：尚未建立資料")

    st.sidebar.markdown("---")
    st.sidebar.info(
        "💡 **資料來源說明**：\n"
        "- 中央氣象署 (CWA) Open Data API\n"
        "- 資料集：`O-A0003-001` (全台測站實測) & `F-C0032-001` (36h各縣市預報)\n"
        "- SQLite 本地快取加速"
    )

    # ------------------ MAIN DASHBOARD ------------------
    # Header Banner
    st.markdown(
        """
        <div class="main-header">
            <h1>🌤️ Taiwan Weather Forecast</h1>
            <p>中央氣象署資料 × Python × SQLite × Streamlit 互動式天氣資料分析系統</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Query filtered data for selected region & date
    region_df = load_weather_data(selected_region)

    if region_df.empty:
        st.warning("⚠️ 目前資料庫中沒有可顯示的天氣資料，請先點選側邊欄「🔄 更新氣象資料」按鈕。")
        return

    # Filter by selected date if matches exist, else show all forecast rows for region
    date_filtered_df = region_df[region_df["dataDate"] == selected_date]
    display_df = date_filtered_df if not date_filtered_df.empty else region_df

    # Extract current latest metric indicators
    latest_row = display_df.iloc[0]
    cur_maxt = latest_row.get("MaxT", 28.0)
    cur_mint = latest_row.get("MinT", 22.0)
    cur_pop = latest_row.get("PoP", 0.0)
    cur_wx = latest_row.get("Wx", "晴時多雲")

    # Region Display Title
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
            <h2 style="margin: 0; color: #1E3A8A; font-size: 1.6rem;">
                📍 目前選擇地區：<span style="color: #2563EB;">{selected_region}</span>
                <span style="font-size: 1rem; color: #64748B; font-weight: normal; margin-left: 8px;">({selected_date})</span>
            </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4 Metric Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">🌡️</div>
                <div class="metric-label">最高溫 (MaxT)</div>
                <div class="metric-value" style="color: #DC2626;">{cur_maxt:.0f} °C</div>
                <div style="font-size: 0.8rem; color: #94A3B8;">今日高溫預測</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">❄️</div>
                <div class="metric-label">最低溫 (MinT)</div>
                <div class="metric-value" style="color: #2563EB;">{cur_mint:.0f} °C</div>
                <div style="font-size: 0.8rem; color: #94A3B8;">今日低溫預測</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">☔</div>
                <div class="metric-label">降雨機率 (PoP)</div>
                <div class="metric-value" style="color: #0284C7;">{cur_pop:.0f} %</div>
                <div style="font-size: 0.8rem; color: #94A3B8;">降水機率評估</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">☁️</div>
                <div class="metric-label">天氣現象 (Wx)</div>
                <div class="metric-value" style="color: #475569; font-size: 1.45rem;">{cur_wx}</div>
                <div style="font-size: 0.8rem; color: #94A3B8;">天候狀況綜覽</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br/>", unsafe_allow_html=True)

    # ------------------ CHART & TABLE TABS ------------------
    tab1, tab2, tab3 = st.tabs(["📈 未來溫度預報圖", "📊 天氣資料表", "🗺️ 臺灣天氣地圖"])

    with tab1:
        st.markdown('<div class="section-title">📈 未來溫度預報</div>', unsafe_allow_html=True)
        fig = render_temperature_chart(region_df, selected_region)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown('<div class="section-title">📊 預報天氣資料表</div>', unsafe_allow_html=True)
        # Format clean presentation DataFrame
        table_df = region_df.copy()
        table_df["日期"] = table_df["dataDate"]
        table_df["預報區間"] = table_df["startTime"].str[5:16] + " ~ " + table_df["endTime"].str[5:16]
        table_df["天氣"] = table_df["Wx"]
        table_df["最低溫 (°C)"] = table_df["MinT"].apply(lambda x: f"{x:.0f}°C")
        table_df["最高溫 (°C)"] = table_df["MaxT"].apply(lambda x: f"{x:.0f}°C")
        table_df["降雨機率"] = table_df["PoP"].apply(lambda x: f"{x:.0f}%")

        display_cols = ["日期", "預報區間", "天氣", "最低溫 (°C)", "最高溫 (°C)", "降雨機率"]
        st.dataframe(
            table_df[display_cols],
            use_container_width=True,
            hide_index=True,
        )

    with tab3:
        st.markdown('<div class="section-title">🗺️ Taiwan Weather Map (全臺天氣地圖)</div>', unsafe_allow_html=True)
        st.caption("點擊地圖上的各縣市或觀測站標記，可查看詳細氣溫、天氣狀況與降雨評估。")

        obs_df = load_observations()
        all_forecast_df = load_weather_data()

        taiwan_map = map_utils.create_taiwan_weather_map(
            forecast_df=all_forecast_df,
            observation_df=obs_df,
            selected_region=selected_region,
            show_stations=True,
        )

        st_folium(
            taiwan_map,
            width="100%",
            height=580,
            returned_objects=[],
        )


if __name__ == "__main__":
    main()
