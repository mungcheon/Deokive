const CACHE_VERSION = 'deokive-offline-v8';
const APP_SHELL_CACHE = `${CACHE_VERSION}-shell`;
const RUNTIME_CACHE = `${CACHE_VERSION}-runtime`;
const APP_SHELL_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.png',
  '/flutter.js',
  '/flutter_bootstrap.js',
  '/main.dart.js',
  '/assets/AssetManifest.bin.json',
  '/assets/FontManifest.json',
];
const API_PREFIXES = ['/health', '/auth', '/profile', '/catalog', '/board', '/banners', '/admin'];

function isApiRequest(url) {
  return API_PREFIXES.some((prefix) => url.pathname.startsWith(prefix));
}

function isCatalogImageRequest(url) {
  return url.pathname.includes('/catalog_images/');
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(APP_SHELL_CACHE).then((cache) => cache.addAll(APP_SHELL_URLS)),
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
            .filter((key) => !key.startsWith(CACHE_VERSION))
            .map((key) => caches.delete(key)),
      ),
    ),
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  if (isApiRequest(url)) {
    return;
  }

  if (isCatalogImageRequest(url)) {
    event.respondWith(fetch(request));
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
          .then((response) => {
            const copy = response.clone();
            caches.open(RUNTIME_CACHE).then((cache) => cache.put(request, copy));
            return response;
          })
          .catch(async () => {
            const cachedPage = await caches.match(request);
            if (cachedPage) {
              return cachedPage;
            }
            return caches.match('/index.html');
          }),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      const networkFetch = fetch(request)
          .then((response) => {
            if (response.ok) {
              const copy = response.clone();
              caches.open(RUNTIME_CACHE).then((cache) => cache.put(request, copy));
            }
            return response;
          })
          .catch(() => cached);

      return cached || networkFetch;
    }),
  );
});
