// Daily TED — Service Worker
//
// キャッシュ戦略:
//   - HTML ナビゲーション   : network-first(オンライン時は常に最新。普通のサイトと同じ挙動)
//   - data/*               : network-first(Cloud Task が毎日更新するため最新優先)
//   - 静的アセット(icon等) : stale-while-revalidate(即表示しつつ裏で更新)
//   - オフライン時          : いずれもキャッシュにフォールバック
//
// CACHE_NAME を変更すると activate で旧キャッシュを破棄する。
// アプリ本体(index.html)を cache-first にすると更新が永久に反映されないため禁止。

const CACHE_NAME = 'daily-ted-v3';
const APP_SHELL = [
  './',
  './index.html',
  './public/manifest.json',
  './public/icon-192.svg',
  './public/icon-512.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// network-first: 取得できたらキャッシュを更新して返す。失敗時はキャッシュ。
function networkFirst(req, fallbackKey) {
  return fetch(req)
    .then((res) => {
      if (res && res.ok) {
        const clone = res.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
      }
      return res;
    })
    .catch(() =>
      caches.match(req).then((cached) =>
        cached || (fallbackKey ? caches.match(fallbackKey) : Response.error())
      )
    );
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // 自オリジン以外(YouTube 埋め込み・サムネイル等)は介入しない
  if (url.origin !== self.location.origin) return;

  // HTML ナビゲーション → network-first(訪問のたびに最新アプリを取得)
  if (req.mode === 'navigate') {
    event.respondWith(networkFirst(req, './index.html'));
    return;
  }

  // data/* → network-first
  if (url.pathname.includes('/data/')) {
    event.respondWith(networkFirst(req));
    return;
  }

  // 静的アセット → stale-while-revalidate
  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          }
          return res;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
