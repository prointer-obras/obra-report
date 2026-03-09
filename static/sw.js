const CACHE = 'obra-report-v13';
const ASSETS = [
  '/',
  '/manifest.json',
  '/prointer-logo.jpg',
  '/icon-192.png',
  '/icon-512.png',
  'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = e.request.url;

  // API siempre a la red (envio de correo)
  if (url.includes('/api/')) return;

  // Cache primero, red como fallback (funciona offline)
  e.respondWith(
    caches.match(e.request).then(function(cached) {
      if (cached) return cached;
      return fetch(e.request).then(function(resp) {
        if (resp && resp.status === 200) {
          caches.open(CACHE).then(function(c) { c.put(e.request, resp.clone()); });
        }
        return resp;
      }).catch(function() { return cached; });
    })
  );
});
