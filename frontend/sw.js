/* Omnivaleur service worker — enables install-to-homescreen (PWA) and a light
 * offline shell. Deliberately conservative: it NEVER caches API responses or
 * anything auth-sensitive, only the static app shell and assets. */
const VERSION = 'ov-v1';
const SHELL = [
  '/app',
  '/logo.png',
  '/manifest.webmanifest',
  '/assets/pwa/icon-192.png',
  '/assets/pwa/icon-512.png',
];

self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL).catch(() => {})));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  const url = new URL(req.url);

  // Only handle same-origin GETs. Never touch API calls, auth, or POSTs —
  // those must always hit the network so data is live and never stale-served.
  if (req.method !== 'GET' || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/')) return;

  // App navigations: network-first, fall back to the cached shell when offline
  // so the user at least sees the app frame instead of a browser error page.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req).catch(() => caches.match('/app').then((r) => r || caches.match(req)))
    );
    return;
  }

  // Static assets (icons, logo, manifest): cache-first, refresh in background.
  e.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(VERSION).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
