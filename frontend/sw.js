/* Service Worker — Offline-First básico do Gestão Ágil */
const CACHE_NAME = "gestao-agil-v1";
const PRECACHE = [
  "/",
  "/static/style.css",
  "/static/app.js",
  "/manifest.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);
  // API: network-first (dados dinâmicos)
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request)
        .then((response) => response)
        .catch(() =>
          new Response(JSON.stringify({ detail: "Offline: API indisponível." }), {
            status: 503,
            headers: { "Content-Type": "application/json" },
          })
        )
    );
    return;
  }

  // Shell estático: cache-first
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
