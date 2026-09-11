export const config = {
  runtime: 'edge',
};

export default async function handler(req) {
  const targetUrl = 'https://github.com/greson719/pcdeck/releases/download/v2.7.0/PCDeck-Setup.exe';
  const res = await fetch(targetUrl, {
    redirect: 'follow',
  });

  const headers = new Headers();
  headers.set('Content-Type', 'application/octet-stream');
  headers.set('Content-Disposition', 'attachment; filename="PCDeck-Setup.exe"');
  const len = res.headers.get('content-length');
  if (len) {
    headers.set('Content-Length', len);
  }
  headers.set('Cache-Control', 'public, max-age=86400');

  return new Response(res.body, {
    status: 200,
    headers,
  });
}
