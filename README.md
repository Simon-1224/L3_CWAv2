# 🌤️ Taiwan Weather Forecast Dashboard

> **AI 創新微課程 ── Homework 1**
>
> 學生：＿＿＿＿＿ ／ 學號：＿＿＿＿＿ ／ 繳交日期：2026-09-23

---

## 📋 一、作業資訊 (Assignment Info)

| 項目 | 內容 |
|------|------|
| 課程名稱 | AI 創新微課程 |
| 作業編號 | Homework 1 |
| 作業主題 | 氣象開放資料串接與互動式 Dashboard 實作 |
| 使用語言 | Python 3.11+ |
| 繳交方式 | GitHub Repository |

---

## 📌 二、作業目標 (Objective)

本作業旨在透過串接**中央氣象署（CWA）Open Data API**，實作一套完整的氣象資料擷取、儲存與視覺化流程，並以 Streamlit 建立互動式 Web Dashboard，達成以下學習目標：

1. 了解 RESTful API 串接方式（`requests`、JSON 解析）
2. 使用 `Pandas` 進行資料清洗與轉換
3. 使用 `SQLite` 進行本地資料持久化儲存（CRUD、SQL 查詢）
4. 以 `Streamlit` 建立互動式 Web 應用程式
5. 整合 `Plotly` 折線圖與 `Folium` 互動地圖進行資料視覺化

---

## 🏗️ 三、系統架構 (System Architecture)

### 整體資料流程

```
CWA Open Data API
  ├── O-A0003-001（全台 363 自動氣象站即時觀測）
  └── F-C0032-001（22 縣市今明 36 小時天氣預報）
        ↓ requests.get()
    weather_api.py（API 連線層）
        ↓ JSON Response
    data_processor.py（資料解析 & Pandas 轉換層）
        ↓ DataFrame
    database.py（SQLite 持久化層）
        ↓ SQL Query
    app.py（Streamlit Dashboard 呈現層）
        ↓
    Plotly 折線圖 + Folium 互動地圖 + 資料表
```

### 專案目錄結構

```
HW1/
│
├── app.py               # Streamlit 主應用程式（UI 渲染與互動）
├── weather_api.py       # CWA API 連線模組（requests + 錯誤處理）
├── data_processor.py    # JSON 解析 & DataFrame 轉換
├── database.py          # SQLite CRUD 操作（資料表初始化、查詢）
├── map_utils.py         # Folium 互動地圖生成
├── config.py            # 設定集中管理（API Key、縣市清單、座標）
│
├── data/                # 資料目錄
├── data.db              # SQLite 資料庫（gitignored）
│
├── .streamlit/
│   ├── secrets.toml         # 🔐 API Key（gitignored）
│   └── secrets.toml.example
│
├── requirements.txt         # Python 依賴套件清單
├── .gitignore
├── README.md                # 本報告文件
│
├── test_cwa_api.py          # 單元測試：API 連線
├── test_data_processor.py   # 單元測試：JSON→DataFrame
└── test_database.py         # 單元測試：SQLite SQL 查詢
```

---

## 🛠️ 四、技術棧 (Tech Stack)

| 層次 | 技術 / 套件 | 版本要求 | 用途說明 |
|------|-------------|----------|----------|
| 語言 | **Python** | 3.11+ | 主要開發語言 |
| Web 框架 | **Streamlit** | ≥ 1.64 | 互動式 Dashboard |
| API 連線 | **Requests** | ≥ 2.34 | HTTP GET 呼叫 CWA API |
| 資料處理 | **Pandas** | ≥ 3.0 | JSON 解析、DataFrame 轉換 |
| 資料庫 | **SQLite** | 內建 | 本地持久化儲存，無需額外安裝 |
| 圖表 | **Plotly** | ≥ 7.1 | 互動式溫度折線圖 |
| 地圖 | **Folium** + **streamlit-folium** | ≥ 0.20 | 全台天氣互動地圖 |
| 機密管理 | **python-dotenv** | ≥ 1.2 | API Key 安全載入 |
| 資料來源 | **CWA Open Data API** | — | 氣象原始資料 |

---

## ✨ 五、功能說明 (Features)

| # | 功能 | 說明 |
|---|------|------|
| 1 | 📍 地區選擇 | 下拉選單選擇全台 22 縣市 |
| 2 | 📅 日期篩選 | 依可用日期篩選預報資料 |
| 3 | 🌡️ 最高溫 (MaxT) | 顯示選定地區當日最高氣溫預測 |
| 4 | ❄️ 最低溫 (MinT) | 顯示選定地區當日最低氣溫預測 |
| 5 | ☔ 降雨機率 (PoP) | 各時段降雨機率百分比 |
| 6 | ☁️ 天氣現象 (Wx) | 天氣描述（晴、多雲、陰雨等） |
| 7 | 📈 溫度折線圖 | Plotly 互動式 MaxT / MinT 折線圖 |
| 8 | 📊 天氣資料表 | 結構化時段預報表格 |
| 9 | 🗺️ 台灣天氣地圖 | Folium 互動地圖，22 縣市標記 + 363 觀測站群聚圖層 |
| 10 | 🔄 手動更新 | 點擊按鈕即時向 CWA API 取得最新資料 |
| 11 | 🕒 更新時間戳 | 顯示資料最後更新時間 |

---

## 📡 六、資料流程詳述 (Data Flow)

### Step 1 — API 資料擷取（`weather_api.py`）

```python
# 取得 36 小時天氣預報（22 縣市）
fc_json = weather_api.get_forecast_data(api_key=api_key)

# 取得全台 363 自動氣象站即時觀測
obs_json = weather_api.get_observation_data(api_key=api_key)
```

- 使用 `requests.get()` 發送 HTTP GET 請求
- 包含完整錯誤處理（HTTP 狀態碼、Timeout、API 錯誤回應）

### Step 2 — 資料清洗與轉換（`data_processor.py`）

```python
df_fc  = data_processor.parse_forecast_json(fc_json)
# → DataFrame: regionName, dataDate, startTime, endTime, MaxT, MinT, PoP, Wx

df_obs = data_processor.parse_observation_json(obs_json)
# → DataFrame: stationId, stationName, county, lat, lon, Temperature, ...
```

- 處理缺值、欄位型別轉換、重複資料去除

### Step 3 — 資料持久化（`database.py`）

```sql
-- 天氣預報表
CREATE TABLE TemperatureForecasts (
    regionName TEXT, dataDate TEXT, startTime TEXT, endTime TEXT,
    MaxT REAL, MinT REAL, PoP REAL, Wx TEXT,
    UNIQUE (regionName, startTime, endTime)   -- 防止重複寫入
);

-- 觀測站資料表
CREATE TABLE StationObservations (
    stationId TEXT, stationName TEXT, county TEXT,
    lat REAL, lon REAL, Temperature REAL, ...
);
```

### Step 4 — SQL 查詢與 Dashboard 呈現（`app.py`）

```sql
SELECT * FROM TemperatureForecasts
WHERE regionName = ?
ORDER BY startTime;
```

---

## 📦 七、各模組說明 (Module Details)

| 模組 | 功能 |
|------|------|
| `app.py` | Streamlit 主程式，整合所有模組，負責 UI 渲染與使用者互動。包含 4 張 Metric Card、Plotly 圖表、資料表與 Folium 地圖 |
| `weather_api.py` | 封裝 CWA API 呼叫，提供 `get_observation_data()` 與 `get_forecast_data()`，內含完整錯誤處理與自訂 `WeatherAPIError` 例外 |
| `data_processor.py` | 將 CWA JSON 解析為結構化 Pandas DataFrame，處理缺值、型別轉換與重複資料 |
| `database.py` | SQLite CRUD 操作、資料表初始化、SQL 查詢函式（依地區 / 日期查詢）、UNIQUE constraint 防止重複寫入 |
| `map_utils.py` | 以 Folium 生成互動式台灣天氣地圖，縣市標記顏色依氣溫動態變化，並提供 363 觀測站群聚圖層 |
| `config.py` | 集中管理 API 端點、資料集代碼、22 縣市清單、座標辭典、安全金鑰讀取邏輯 |

---

## 🚀 八、環境建置與啟動 (Installation & Run)

### 1. 建立虛擬環境

```bash
python -m venv .venv
```

**Windows：**
```bash
.venv\Scripts\activate
```

**macOS / Linux：**
```bash
source .venv/bin/activate
```

### 2. 安裝依賴套件

```bash
pip install -r requirements.txt
```

### 3. 設定 CWA API Key

前往 [中央氣象署 Open Data 平台](https://opendata.cwa.gov.tw/) 申請免費 API 授權碼，並選擇下列其中一種方式設定：

**方式 A：`.streamlit/secrets.toml`（推薦於雲端部署）**
```toml
CWA_API_KEY = "CWA-YOUR-API-KEY-HERE"
```

**方式 B：`.env`（推薦於本機開發）**
```env
CWA_API_KEY=CWA-YOUR-API-KEY-HERE
```

> ⚠️ **安全提醒：請勿將 API Key 上傳至 GitHub！**
> `.gitignore` 已預設排除 `.env` 與 `.streamlit/secrets.toml`。

### 4. 啟動應用程式

```bash
streamlit run app.py
```

瀏覽器開啟 [http://localhost:8501](http://localhost:8501)

---

## 🧪 九、測試說明 (Testing)

本作業包含三支單元測試腳本，覆蓋核心功能：

| 測試腳本 | 測試範圍 |
|----------|----------|
| `test_cwa_api.py` | CWA API 連線、HTTP 回應狀態碼、JSON 結構驗證 |
| `test_data_processor.py` | JSON → Pandas DataFrame 轉換、欄位完整性、型別正確性 |
| `test_database.py` | SQLite 資料表初始化、資料寫入、SQL 查詢正確性 |

執行測試：
```bash
python -m pytest test_cwa_api.py test_data_processor.py test_database.py -v
```

---

## 🌐 十、版本控制說明 (Git)

```bash
# 初始化並提交
git init
git add .
git commit -m "feat: HW1 Taiwan Weather Forecast Dashboard"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git
git push -u origin main
```

> **注意：** 執行 `git push` 前，請先以 `git status` 確認以下檔案**未**出現在 Changes 清單：
> - `.env`
> - `.streamlit/secrets.toml`
> - `data.db`

---

## ☁️ 十一、Streamlit Cloud 部署 (Deployment)

1. 前往 [https://streamlit.io/cloud](https://streamlit.io/cloud) 並登入
2. 點選 **New app** → 選擇 GitHub Repository
3. 設定 Main file path：`app.py`
4. 點選 **Advanced settings → Secrets** 頁籤，貼入：

```toml
CWA_API_KEY = "CWA-YOUR-API-KEY-HERE"
```

5. 點選 **Deploy!**

---

## 📝 十二、心得與學習反思 (Reflection)

> 請在此填寫你的作業心得（100 字以上）：

```
（請在此填寫）
- 本次作業學習到了哪些新技術或概念？
- 遇到了哪些困難？如何解決？
- 對資料流程（API → 資料庫 → 視覺化）的理解與感想
```

---

## 📚 十三、參考資料 (References)

1. [中央氣象署 Open Data 平台](https://opendata.cwa.gov.tw/)
2. [Streamlit 官方文件](https://docs.streamlit.io/)
3. [Plotly Python 圖表庫](https://plotly.com/python/)
4. [Folium 互動地圖](https://python-visualization.github.io/folium/)
5. [SQLite 官方文件](https://www.sqlite.org/docs.html)
6. [Pandas 使用手冊](https://pandas.pydata.org/docs/)
7. [Requests 使用手冊](https://requests.readthedocs.io/)

---

## 📄 授權聲明 (License)

本專案僅供個人學習與課堂作業使用。氣象資料版權歸屬**中央氣象署**，使用須遵守 [CWA Open Data 使用規範](https://opendata.cwa.gov.tw/about)。
��央氣象署 CWA Open Data API
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

## ⚡ Vercel (stlite / WebAssembly) 部署說明

本專案支援免伺服器 (Serverless) 的純靜態 WebAssembly (stlite) 部署於 Vercel：

1. 專案已打包包含 `index.html`（使用 `@stlite/mountable`）與 `vercel.json`（單頁路由重寫）。
2. 在 [Vercel](https://vercel.com/) 點選 **Add New...** → **Project**。
3. 匯入本 GitHub Repository。
4. Framework Preset 選擇 **Other**，Build Command 與 Output Directory 保留空白預設。
5. 點選 **Deploy** 即完成部署！
6. 開啟部署網址後，若瀏覽器端未預設金鑰，可於側邊欄輸入中央氣象署 API 授權碼，點擊「🔄 更新氣象資料」即可由瀏覽器端直接連線 CWA API 載入全台即時氣象資訊！

---

## 📝 授權 (License)

本專案僅供個人學習與課堂作業使用。氣象資料版權歸屬中央氣象署，使用須遵守 [CWA Open Data 使用規範](https://opendata.cwa.gov.tw/about)。

