const PREFIX = `node-update-helper-${new URL(self.registration.scope).pathname}-`;
const CACHE = `${PREFIX}v6`;
const SHELL = ['./', './index.html', './styles.css', './app.js', './manifest.webmanifest', './icons/favicon.png', './icons/brand-logo.png', './icons/github.svg', './icons/gitlab.svg', './icons/icon-192.png', './icons/icon-512.png'];
self.addEventListener('install', event => { event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith(PREFIX) && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;
  // data.json is deliberately network-only. The UI owns its timestamped offline snapshot.
  if (url.pathname.endsWith('/data.json')) return;
  const known = SHELL.some(path => new URL(path, self.registration.scope).pathname === url.pathname);
  if (!known) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const response = await fetch(event.request);
      if (response.ok) await cache.put(event.request, response.clone());
      if (response.ok) return response;
      return (await cache.match(event.request)) || response;
    } catch {
      return (await cache.match(event.request)) || (event.request.mode === 'navigate' ? await cache.match('./index.html') : Response.error());
    }
  })());
});
