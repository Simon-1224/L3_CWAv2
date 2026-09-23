# 🌤️ Taiwan Weather Forecast

> **AI 創新微課程作業** ── 中央氣象署 Open Data API × Python × SQLite × Streamlit 互動式天氣資料分析 Web App

---

## 📌 專案簡介 (Project Introduction)

本專案以中央氣象署（CWA）Open Data API 為資料來源，建立一個完整的氣象資料流程：

```
CWA Open Data API (O-A0003-001 / F-C0032-001)
    ↓ requests
JSON 解析 & 清洗
    ↓ Pandas
SQLite 資料庫儲存
    ↓ SQL Query
Streamlit Web Dashboard
    ↓
Plotly 折線圖 + Folium 互動地圖 + 資料表
```

---

## ✨ 功能特色 (Features)

| 功能 | 說明 |
|------|------|
| 📍 地區選擇 | 下拉選單選擇全台 22 縣市 |
| 🌡️ 溫度預報 | 查看最高溫 / 最低溫 |
| ☔ 降雨機率 | 查看各時段降雨機率 (%) |
| ☁️ 天氣現象 | 顯示天氣描述（晴、多雲、雨等） |
| 📈 溫度折線圖 | Plotly 互動式 MaxT/MinT 折線圖 |
| 📊 天氣資料表 | 結構化時段預報表格 |
| 🗺️ 台灣天氣地圖 | Folium 互動地圖，22 縣市溫度標記 + 363 觀測站 |
| 🔄 手動更新 | 點擊按鈕即時向 CWA API 取得最新資料 |
| 🕒 更新時間 | 顯示資料最後更新時間 |

---

## 🏗️ 系統架構 (System Architecture)

```
taiwan-weather/
│
├── app.py              # Streamlit 主應用程式 (Dashboard UI)
├── weather_api.py      # CWA API 連線模組 (requests + error handling)
├── data_processor.py   # JSON 解析 & Pandas DataFrame 轉換
├── database.py         # SQLite 資料庫操作 (CRUD + SQL Queries)
├── map_utils.py        # Folium 互動地圖生成
├── config.py           # 設定集中管理 (API Key、縣市常數、座標)
│
├── data/               # 資料目錄 (git tracked)
│   └── .gitkeep
│
├── .streamlit/
│   ├── secrets.toml         # 🔐 API Key (gitignored)
│   └── secrets.toml.example # 設定範本 (可 commit)
│
├── requirements.txt    # Python 依賴套件
├── .gitignore          # 排除敏感資料與快取
├── README.md           # 本說明文件
├── data.db             # SQLite 資料庫 (gitignored)
│
├── test_cwa_api.py         # API 連線測試
├── test_data_processor.py  # JSON→DataFrame 測試
└── test_database.py        # SQLite SQL 查詢測試
```

---

## 🛠️ 技術棧 (Technologies)

| 層次 | 技術 |
|------|------|
| 語言 | **Python 3.11+** |
| Web 框架 | **Streamlit 1.64** |
| API 連線 | **Requests** |
| 資料格式 | **JSON** |
| 資料處理 | **Pandas** |
| 資料庫 | **SQLite** (內建，無需安裝) |
| 查詢語言 | **SQL** |
| 圖表 | **Plotly** |
| 地圖 | **Folium** + **streamlit-folium** |
| 機密管理 | **python-dotenv** |
| 資料來源 | **CWA Open Data API** |

---

## 🚀 安裝與啟動 (Installation)

### 1. 建立虛擬環境

```bash
python -m venv .venv
```

**Windows 啟動：**
```bash
.venv\Scripts\activate
```

**macOS / Linux 啟動：**
```bash
source .venv/bin/activate
```

### 2. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 3. 設定 CWA API Key（見下節）

### 4. 啟動應用程式

```bash
streamlit run app.py
```

瀏覽器開啟 [http://localhost:8501](http://localhost:8501)

---

## 🔑 CWA API Key 設定 (API Key Setup)

### 取得 API Key

1. 前往 [中央氣象署 Open Data 平台](https://opendata.cwa.gov.tw/)
2. 點選右上角「**登入 / 會員中心**」
3. 註冊帳號並登入
4. 至「**API 授權碼**」頁面申請授權碼（免費）

### 設定 API Key（擇一方式）

**方式 A：`.streamlit/secrets.toml`（推薦用於 Streamlit Cloud 部署）**

```toml
# .streamlit/secrets.toml
CWA_API_KEY = "CWA-YOUR-API-KEY-HERE"
```

**方式 B：`.env`（推薦用於本機開發）**

```env
CWA_API_KEY=CWA-YOUR-API-KEY-HERE
```

> ⚠️ **重要安全提醒：請勿將 API Key 上傳至 GitHub！**
> 本專案的 `.gitignore` 已預設排除 `.env` 與 `.streamlit/secrets.toml`，
> 請確認 `git status` 中看不到這兩個檔案，再執行 `git push`。

---

## 📦 各模組說明 (Project Structure)

| 檔案 | 功能說明 |
|------|----------|
| `app.py` | Streamlit 主程式，整合所有模組，負責 UI 渲染與使用者互動 |
| `weather_api.py` | 封裝所有 CWA API 呼叫，提供 `get_observation_data()` 與 `get_forecast_data()`，包含完整錯誤處理 |
| `data_processor.py` | 將 CWA JSON 解析為結構化 Pandas DataFrame，處理缺值、型別轉換與重複資料 |
| `database.py` | SQLite CRUD 操作、資料表初始化、SQL 查詢函式（依地區 / 日期查詢） |
| `map_utils.py` | 以 Folium 生成互動式台灣天氣地圖，含縣市標記（圖示顏色依氣溫）與 363 觀測站群聚圖層 |
| `config.py` | 集中管理 API 端點、資料集代碼、22 縣市清單、座標辭典、安全金鑰載入 |

---

## 📡 資料流程 (Data Flow)

```
1. 中央氣象署 CWA Open Data API
   ├── O-A0003-001: 全台 363 自動氣象站即時觀測資料
   └── F-C0032-001: 22 縣市今明 36 小時天氣預報

2. weather_api.py → requests.get() → HTTP 200 → JSON

3. data_processor.py
   ├── parse_observation_json() → 觀測站 DataFrame (15 欄)
   └── parse_forecast_json() → 預報 DataFrame (8 欄)

4. database.py → SQLite (data.db)
   ├── StationObservations (363 rows)
   └── TemperatureForecasts (66 rows)
       UNIQUE constraint 防止重複寫入

5. SQL Query
   SELECT * FROM TemperatureForecasts WHERE regionName = ? ORDER BY startTime;

6. app.py → Streamlit Dashboard
   ├── 4 張 Metric Card (MaxT / MinT / PoP / Wx)
   ├── Plotly 溫度折線圖
   ├── 天氣資料表 (st.dataframe)
   └── Folium 台灣互動地圖
```

---

## 🌐 GitHub 部署說明

### 初始化 Git Repository

```bash
git init
git add .
git commit -m "feat: initial Taiwan Weather Forecast project"
git branch -M main
```

### 連接遠端 Repository

```bash
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git
git push -u origin main
```

> **注意：** 執行 `git push` 前，請先執行 `git status` 確認：
> - `.env` 未出現在 Changes 清單中
> - `.streamlit/secrets.toml` 未出現在 Changes 清單中
> - `data.db` 未出現在 Changes 清單中

---

## ☁️ Streamlit Cloud 部署說明

1. 前往 [https://streamlit.io/cloud](https://streamlit.io/cloud) 登入
2. 點選 **New app** → 選擇你的 GitHub Repository
3. 設定 Main file path：`app.py`
4. 點選 **Advanced settings** → **Secrets** 頁籤
5. 貼入以下內容（填入你的真實 API Key）：

```toml
CWA_API_KEY = "CWA-YOUR-API-KEY-HERE"
```

6. 點選 **Deploy!**

---

## 📝 授權 (License)

本專案僅供個人學習與課堂作業使用。氣象資料版權歸屬中央氣象署，使用須遵守 [CWA Open Data 使用規範](https://opendata.cwa.gov.tw/about)。
# L3_CWAv2
