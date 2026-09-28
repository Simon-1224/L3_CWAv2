const ALLOWED_DATASETS = new Set(["O-A0003-001", "F-C0032-001"]);
const ALLOWED_LOCATIONS = new Set([
  "臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市",
  "基隆市", "新竹市", "新竹縣", "苗栗縣", "彰化縣", "南投縣",
  "雲林縣", "嘉義市", "嘉義縣", "屏東縣", "宜蘭縣", "花蓮縣",
  "臺東縣", "澎湖縣", "金門縣", "連江縣",
]);
const CWA_API_BASE = "https://opendata.cwa.gov.tw/api/v1/rest/datastore";

module.exports = async function handler(req, res) {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return res.status(405).json({ error: "Only GET requests are supported." });
  }

  const apiKey = process.env.CWA_API_KEY;
  if (!apiKey) {
    return res.status(503).json({
      error: "Vercel 尚未設定 CWA_API_KEY。請在專案環境變數中設定後重新部署。",
    });
  }

  const dataset = req.query.dataset;
  if (typeof dataset !== "string" || !ALLOWED_DATASETS.has(dataset)) {
    return res.status(400).json({ error: "Unsupported weather dataset." });
  }

  const locationName = req.query.locationName;
  if (
    locationName !== undefined &&
    (typeof locationName !== "string" || !ALLOWED_LOCATIONS.has(locationName))
  ) {
    return res.status(400).json({ error: "Invalid locationName." });
  }

  const upstreamUrl = new URL(CWA_API_BASE + "/" + dataset);
  upstreamUrl.searchParams.set("Authorization", apiKey);
  if (locationName) {
    upstreamUrl.searchParams.set("locationName", locationName);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    const upstream = await fetch(upstreamUrl, { signal: controller.signal });
    if (!upstream.ok) {
      if (upstream.status === 401 || upstream.status === 403) {
        return res.status(502).json({
          error: "中央氣象署授權失敗，請確認 Vercel 的 CWA_API_KEY 設定。",
        });
      }
      return res.status(502).json({
        error: "中央氣象署 API 暫時無法使用（HTTP " + upstream.status + "）。",
      });
    }

    const payload = await upstream.json();
    res.setHeader("Cache-Control", "public, s-maxage=300, stale-while-revalidate=600");
    return res.status(200).json(payload);
  } catch (error) {
    if (error && error.name === "AbortError") {
      return res.status(504).json({ error: "中央氣象署 API 連線逾時。" });
    }
    return res.status(502).json({ error: "無法連線至中央氣象署 API。" });
  } finally {
    clearTimeout(timeout);
  }
};
