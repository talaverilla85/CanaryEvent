// Admin PWA: a separate /admin/ service-worker registration, with NO offline caching of
// login screens, authenticated responses, or private assets. All requests use the network.
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
