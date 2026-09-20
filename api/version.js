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
    versionCode: 271,
    versionName: "2.7.1",
    exeSize: "36.3 MB",
    apkSize: "691 KB",
    zipSize: "49.7 MB",
    apkUrl: "https://pcdeck.vercel.app/PCDeck.apk",
    websiteUrl: "https://pcdeck.vercel.app",
    playStoreUrl: "",
    releaseNotes: "• Real-time connection updates & direct community suggestions channels\n• Optimized above-the-fold download layout for Windows and Android\n• 100% Native 1.0x Resolution & fluid 1:1 sub-pixel touch scrolling\n• Full Spanish & Portuguese localized documentation\n• Instant QR-Code Web Controller for iPhone, iPad, Mac & Linux",
    minVersionCode: 1,
    publishedAt: "2026-09-20"
  });
}
