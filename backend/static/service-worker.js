// ─────────────────────────────────────────────
// FRC Scouting App — Service Worker
// Provides offline caching and background sync
// ─────────────────────────────────────────────

const CACHE_VERSION = 'frc-scout-v1';
const OFFLINE_URL = '/offline';

// Assets to cache immediately on install
const PRECACHE_ASSETS = [
    '/offline',
    '/static/pwa/icon-192.png',
    '/static/pwa/icon-512.png',
    '/static/manifest.json',
];

// CDN resources to cache on first load
const CDN_CACHE = 'frc-scout-cdn-v1';

// ─── INSTALL ───
self.addEventListener('install', (event) => {
    console.log('[SW] Installing service worker...');
    event.waitUntil(
        caches.open(CACHE_VERSION)
            .then(cache => cache.addAll(PRECACHE_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// ─── ACTIVATE ───
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating service worker...');
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== CACHE_VERSION && key !== CDN_CACHE)
                    .map(key => caches.delete(key))
            );
        }).then(() => self.clients.claim())
    );
});

// ─── FETCH ───
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests (POST submissions handled by background sync)
    if (request.method !== 'GET') return;

    // Strategy for CDN resources (TailwindCSS, Chart.js, Material Icons, etc.)
    if (url.origin !== location.origin) {
        event.respondWith(
            caches.open(CDN_CACHE).then(cache =>
                cache.match(request).then(cached => {
                    const fetchPromise = fetch(request).then(response => {
                        if (response.ok) cache.put(request, response.clone());
                        return response;
                    }).catch(() => cached);
                    return cached || fetchPromise;
                })
            )
        );
        return;
    }

    // Strategy for static assets — Cache First
    if (url.pathname.startsWith('/static/') || url.pathname.startsWith('/shared_assets/')) {
        event.respondWith(
            caches.open(CACHE_VERSION).then(cache =>
                cache.match(request).then(cached => {
                    if (cached) return cached;
                    return fetch(request).then(response => {
                        if (response.ok) cache.put(request, response.clone());
                        return response;
                    });
                })
            )
        );
        return;
    }

    // Strategy for API calls — Network Only (let them fail gracefully)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request).catch(() => {
                return new Response(JSON.stringify({ error: 'offline', message: 'You are offline. Data will sync when reconnected.' }), {
                    headers: { 'Content-Type': 'application/json' },
                    status: 503
                });
            })
        );
        return;
    }

    // Strategy for HTML pages — Network First, fallback to cache, then offline page
    event.respondWith(
        fetch(request)
            .then(response => {
                // Cache successful page loads for offline use
                if (response.ok && response.headers.get('content-type')?.includes('text/html')) {
                    const clone = response.clone();
                    caches.open(CACHE_VERSION).then(cache => cache.put(request, clone));
                }
                return response;
            })
            .catch(() => {
                return caches.match(request).then(cached => {
                    return cached || caches.match(OFFLINE_URL);
                });
            })
    );
});

// ─── BACKGROUND SYNC ───
// When a scouting form is submitted offline, it's queued in IndexedDB.
// When connectivity returns, the sync event fires and pushes the data.
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-scouting-data') {
        console.log('[SW] Background sync triggered: sync-scouting-data');
        event.waitUntil(syncScoutingData());
    }
});

async function syncScoutingData() {
    try {
        const db = await openDB();
        const tx = db.transaction('offline_queue', 'readonly');
        const store = tx.objectStore('offline_queue');
        const items = await getAllFromStore(store);

        for (const item of items) {
            try {
                const response = await fetch(item.url, {
                    method: 'POST',
                    headers: item.headers || { 'Content-Type': 'application/json' },
                    body: item.body,
                    credentials: 'include'
                });

                if (response.ok) {
                    // Remove from queue on success
                    const delTx = db.transaction('offline_queue', 'readwrite');
                    delTx.objectStore('offline_queue').delete(item.id);
                    console.log(`[SW] Synced offline item ${item.id}`);
                }
            } catch (e) {
                console.warn(`[SW] Failed to sync item ${item.id}, will retry`, e);
            }
        }
    } catch (e) {
        console.error('[SW] Sync failed:', e);
    }
}

// ─── IndexedDB Helpers ───
function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('frc_scout_offline', 1);
        request.onupgradeneeded = (e) => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains('offline_queue')) {
                db.createObjectStore('offline_queue', { keyPath: 'id', autoIncrement: true });
            }
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

function getAllFromStore(store) {
    return new Promise((resolve, reject) => {
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}
