const CACHE = "expense-tracker-v2";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => caches.delete(k)))
    )
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/")) return;
  if (event.request.method !== "GET") return;

  // Always fetch fresh app code so login protection stays in sync.
  event.respondWith(
    fetch(event.request).catch(() => caches.open(CACHE).then((c) => c.match(event.request)))
  );
});
