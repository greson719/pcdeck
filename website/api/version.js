export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const userAgent = req.headers['user-agent'] || 'unknown';
  const country = req.headers['x-vercel-ip-country'] || 'unknown';
  console.log(`[PCDeck Ping] Client: ${userAgent} | Country: ${country}`);

  return res.status(200).json({
    versionCode: 280,
    versionName: "2.8.0",
    exeSize: "37.5 MB",
    apkSize: "983 KB",
    apkUrl: "https://getpcdeck.com/PCDeck.apk",
    websiteUrl: "https://getpcdeck.com",
    playStoreUrl: "",
    msStoreUrl: "https://apps.microsoft.com/detail/9P4BK16LBGLS",
    msStoreDirectUrl: "https://get.microsoft.com/installer/download/9P4BK16LBGLS",
    releaseNotes: "• Resilient Pro Licensing: Automatic lowercase UUID normalization and instant local Wi-Fi auto-unlock\n• Native Microsoft Store Review: Instant review dialog trigger on PC with 3s debounce\n• Multi-PC Dedup: Clean recent computers list with intelligent generic name filtering\n• Asynchronous Licensing & Fast Media: Zero-blocking activation and full HTTP 206 byte-range streaming",
    minVersionCode: 1,
    publishedAt: "2026-11-01"
  });
}
