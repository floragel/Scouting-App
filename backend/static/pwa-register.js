// ─────────────────────────────────────────────
// FRC Scouting App — PWA Registration & Offline Queue
// Include this script on every page
// ─────────────────────────────────────────────

(function () {
    'use strict';

    // ─── SERVICE WORKER REGISTRATION ───
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/service-worker.js', { scope: '/' })
                .then(reg => {
                    console.log('[PWA] Service Worker registered, scope:', reg.scope);
                    // Check for updates periodically
                    setInterval(() => reg.update(), 60 * 60 * 1000); // Every hour
                })
                .catch(err => console.warn('[PWA] SW registration failed:', err));
        });
    }

    // ─── ONLINE/OFFLINE STATUS INDICATOR ───
    function createStatusBanner() {
        const banner = document.createElement('div');
        banner.id = 'pwa-offline-banner';
        banner.innerHTML = `
      <span class="material-symbols-outlined" style="font-size:18px">cloud_off</span>
      <span>You are offline — data will sync when reconnected</span>
    `;
        Object.assign(banner.style, {
            display: 'none',
            position: 'fixed',
            bottom: '20px',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)',
            color: 'white',
            padding: '10px 24px',
            borderRadius: '50px',
            fontSize: '13px',
            fontWeight: '600',
            fontFamily: 'Inter, system-ui, sans-serif',
            zIndex: '99999',
            boxShadow: '0 8px 32px rgba(220, 38, 38, 0.4)',
            gap: '8px',
            alignItems: 'center',
            transition: 'all 0.3s ease',
            backdropFilter: 'blur(10px)'
        });
        document.body.appendChild(banner);
        return banner;
    }

    function createSyncBanner() {
        const banner = document.createElement('div');
        banner.id = 'pwa-sync-banner';
        banner.innerHTML = `
      <span class="material-symbols-outlined" style="font-size:18px">cloud_done</span>
      <span>Back online — syncing data...</span>
    `;
        Object.assign(banner.style, {
            display: 'none',
            position: 'fixed',
            bottom: '20px',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
            color: 'white',
            padding: '10px 24px',
            borderRadius: '50px',
            fontSize: '13px',
            fontWeight: '600',
            fontFamily: 'Inter, system-ui, sans-serif',
            zIndex: '99999',
            boxShadow: '0 8px 32px rgba(5, 150, 105, 0.4)',
            gap: '8px',
            alignItems: 'center',
            transition: 'all 0.3s ease',
            backdropFilter: 'blur(10px)'
        });
        document.body.appendChild(banner);
        return banner;
    }

    window.addEventListener('DOMContentLoaded', () => {
        const offlineBanner = createStatusBanner();
        const syncBanner = createSyncBanner();

        function updateOnlineStatus() {
            if (!navigator.onLine) {
                offlineBanner.style.display = 'flex';
                syncBanner.style.display = 'none';
            } else {
                offlineBanner.style.display = 'none';
                // If we just came back online, show sync banner briefly
                if (offlineBanner.dataset.wasOffline === 'true') {
                    syncBanner.style.display = 'flex';
                    triggerSync();
                    setTimeout(() => { syncBanner.style.display = 'none'; }, 4000);
                }
            }
            offlineBanner.dataset.wasOffline = (!navigator.onLine).toString();
        }

        window.addEventListener('online', updateOnlineStatus);
        window.addEventListener('offline', updateOnlineStatus);
        updateOnlineStatus();
    });

    // ─── OFFLINE DATA QUEUE (IndexedDB) ───
    const DB_NAME = 'frc_scout_offline';
    const DB_VERSION = 1;
    const STORE_NAME = 'offline_queue';

    function openDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);
            request.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
                }
            };
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // Queue a failed POST request for later sync
    window.queueOfflineSubmission = async function (url, data, contentType) {
        try {
            const db = await openDB();
            const tx = db.transaction(STORE_NAME, 'readwrite');
            const store = tx.objectStore(STORE_NAME);

            const item = {
                url: url,
                body: typeof data === 'string' ? data : JSON.stringify(data),
                headers: { 'Content-Type': contentType || 'application/json' },
                timestamp: Date.now()
            };

            store.add(item);
            console.log('[PWA] Queued offline submission for:', url);

            // Request background sync if available
            if ('serviceWorker' in navigator && 'SyncManager' in window) {
                const reg = await navigator.serviceWorker.ready;
                await reg.sync.register('sync-scouting-data');
            }

            return true;
        } catch (e) {
            console.error('[PWA] Failed to queue offline submission:', e);
            return false;
        }
    };

    // Manually trigger sync (called when coming back online)
    async function triggerSync() {
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
            try {
                const reg = await navigator.serviceWorker.ready;
                await reg.sync.register('sync-scouting-data');
                console.log('[PWA] Sync triggered');
            } catch (e) {
                console.warn('[PWA] Sync registration failed, trying manual sync:', e);
                manualSync();
            }
        } else {
            manualSync();
        }
    }

    // Fallback: manually sync queued items (for browsers without Background Sync API)
    async function manualSync() {
        try {
            const db = await openDB();
            const tx = db.transaction(STORE_NAME, 'readonly');
            const store = tx.objectStore(STORE_NAME);
            const request = store.getAll();

            request.onsuccess = async () => {
                const items = request.result;
                if (items.length === 0) return;

                console.log(`[PWA] Manual sync: ${items.length} items to send`);

                for (const item of items) {
                    try {
                        const response = await fetch(item.url, {
                            method: 'POST',
                            headers: item.headers,
                            body: item.body,
                            credentials: 'include'
                        });

                        if (response.ok) {
                            const delTx = db.transaction(STORE_NAME, 'readwrite');
                            delTx.objectStore(STORE_NAME).delete(item.id);
                            console.log(`[PWA] Synced item ${item.id} to ${item.url}`);
                        }
                    } catch (e) {
                        console.warn(`[PWA] Failed to sync item ${item.id}:`, e);
                    }
                }
            };
        } catch (e) {
            console.error('[PWA] Manual sync error:', e);
        }
    }

    // ─── INSTALL PROMPT ───
    let deferredPrompt = null;

    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        showInstallButton();
    });

    function showInstallButton() {
        // Only show if not already installed
        if (window.matchMedia('(display-mode: standalone)').matches) return;

        const btn = document.createElement('button');
        btn.id = 'pwa-install-btn';
        btn.innerHTML = `
      <span class="material-symbols-outlined" style="font-size:16px">install_mobile</span>
      Install App
    `;
        Object.assign(btn.style, {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            background: 'linear-gradient(135deg, #0d6cf2 0%, #0952b8 100%)',
            color: 'white',
            border: 'none',
            padding: '12px 20px',
            borderRadius: '50px',
            fontSize: '13px',
            fontWeight: '700',
            fontFamily: 'Inter, system-ui, sans-serif',
            cursor: 'pointer',
            zIndex: '99998',
            boxShadow: '0 8px 32px rgba(13, 108, 242, 0.4)',
            display: 'flex',
            gap: '8px',
            alignItems: 'center',
            transition: 'all 0.2s ease',
        });

        btn.addEventListener('mouseenter', () => {
            btn.style.transform = 'scale(1.05)';
            btn.style.boxShadow = '0 12px 40px rgba(13, 108, 242, 0.5)';
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'scale(1)';
            btn.style.boxShadow = '0 8px 32px rgba(13, 108, 242, 0.4)';
        });

        btn.addEventListener('click', async () => {
            if (!deferredPrompt) return;
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            console.log('[PWA] Install prompt outcome:', outcome);
            deferredPrompt = null;
            btn.remove();
        });

        document.body.appendChild(btn);
    }

    // Hide install button if already installed as PWA
    window.addEventListener('appinstalled', () => {
        const btn = document.getElementById('pwa-install-btn');
        if (btn) btn.remove();
        deferredPrompt = null;
        console.log('[PWA] App installed successfully');
    });

})();
