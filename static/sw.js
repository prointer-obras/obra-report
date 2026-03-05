const CACHE = 'obra-report-v3';

self.addEventListener('install', e => {
  // Solo cachear assets estáticos locales (no CDN)
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(['/prointer-logo.jpg', '/icon-192.png', '/icon-512.png', '/manifest.json']))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  // Eliminar cachés antiguas
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = e.request.url;

  // API siempre a la red
  if (url.includes('/api/')) return;

  // HTML principal: siempre red primero (para recibir actualizaciones)
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then(resp => {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
          return resp;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // Resto: caché primero, red como fallback
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(resp => {
        if (resp && resp.status === 200) {
          caches.open(CACHE).then(c => c.put(e.request, resp.clone()));
        }
        return resp;
      });
    })
  );
});
