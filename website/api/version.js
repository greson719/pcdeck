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
    versionCode: 270,
    versionName: "2.7.0",
    exeSize: "36.3 MB",
    apkSize: "687 KB",
    zipSize: "49.7 MB",
    apkUrl: "https://pcdeck.vercel.app/PCDeck.apk",
    websiteUrl: "https://pcdeck.vercel.app",
    playStoreUrl: "",
    releaseNotes: "• Refined high-contrast official icon with pure solid black background (#000000) for all Android launchers\n• Over 50% lighter APK footprint and optimized standalone executable\n• Dynamic AI-Adaptive Bitrate & Quality (Auto-adapts to 2.4GHz / 5GHz / 6GHz Wi-Fi / Dongle latency)\n• Zero physical PC cursor flicker & fluid 1:1 touch scrolling\n• Instant QR-Code Web Controller for iPhone, iPad, Mac & Linux",
    minVersionCode: 1,
    publishedAt: "2026-09-06"
  });
}
