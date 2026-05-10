// Daily TED — minimal Service Worker
// install: cache app shell
// fetch: data/* は network-first(常に最新を取りに行く、失敗したらキャッシュ)
//        その他は cache-first(高速起動、ネット無しでも動く)

const CACHE_NAME = 'daily-ted-v2';
const APP_SHELL = [
  './',
  './index.html',
  './public/manifest.json',
  './public/icon-192.svg',
  './public/icon-512.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // data/ 配下は network-first(Cloud Task が更新するので最新優先)
  if (url.pathname.includes('/data/')) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // それ以外は cache-first
  event.respondWith(
    caches.match(req).then((cached) => cached || fetch(req).then((res) => {
      if (res.ok && (url.origin === self.location.origin)) {
        const clone = res.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
      }
      return res;
    }))
  );
});
