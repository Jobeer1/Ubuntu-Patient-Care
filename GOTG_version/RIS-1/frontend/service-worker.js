/**
 * GOTG-RIS Service Worker
 * Handles offline caching, background sync, and push notifications
 */

const CACHE_VERSION = 'gotg-ris-v1';
const CACHE_STRATEGY = 'cache-first'; // Use cached data first, then network

// URLs to cache on install
const URLS_TO_CACHE = [
  '/',
  '/index.html',
  '/css/styles.css',
  '/js/app.js',
  '/js/service-worker-client.js',
  '/offline.html',
  '/manifest.json'
];

// =============================================
// Install Event
// =============================================

self.addEventListener('install', (event) => {
  console.log('🔧 Service Worker: Installing...');

  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => {
      console.log('📦 Service Worker: Caching app shell');
      return cache.addAll(URLS_TO_CACHE).catch((error) => {
        console.warn('⚠️ Service Worker: Some files failed to cache:', error);
        // Don't fail install if cache fails
      });
    }).then(() => {
      // Skip waiting to activate immediately
      self.skipWaiting();
    })
  );
});

// =============================================
// Activate Event
// =============================================

self.addEventListener('activate', (event) => {
  console.log('🔄 Service Worker: Activating...');

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((cacheName) => cacheName !== CACHE_VERSION)
          .map((cacheName) => {
            console.log('🗑️ Service Worker: Removing old cache:', cacheName);
            return caches.delete(cacheName);
          })
      );
    }).then(() => {
      // Claim all clients
      return self.clients.claim();
    })
  );
});

// =============================================
// Fetch Event
// =============================================

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests
  if (url.origin !== location.origin) {
    return;
  }

  // API requests - Network first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    return event.respondWith(
      networkFirstStrategy(request)
    );
  }

  // Static assets - Cache first with network fallback
  if (
    url.pathname.endsWith('.js') ||
    url.pathname.endsWith('.css') ||
    url.pathname.endsWith('.woff2') ||
    url.pathname.endsWith('.png') ||
    url.pathname.endsWith('.jpg')
  ) {
    return event.respondWith(
      cacheFirstStrategy(request)
    );
  }

  // HTML pages - Network first
  if (request.headers.get('Accept')?.includes('text/html')) {
    return event.respondWith(
      networkFirstStrategy(request)
    );
  }
});

// =============================================
// Cache Strategies
// =============================================

async function cacheFirstStrategy(request) {
  try {
    // Try cache first
    const cache = await caches.open(CACHE_VERSION);
    const cached = await cache.match(request);

    if (cached) {
      console.log('📦 Service Worker: Serving from cache:', request.url);
      return cached;
    }

    // Fall back to network
    const response = await fetch(request);

    // Cache successful responses
    if (response.ok) {
      const cache = await caches.open(CACHE_VERSION);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.error('❌ Service Worker: Cache first failed:', error);
    return new Response('Network error', { status: 503 });
  }
}

async function networkFirstStrategy(request) {
  try {
    // Try network first
    const response = await fetch(request);

    // Cache successful API responses
    if (response.ok && request.method === 'GET') {
      const cache = await caches.open(CACHE_VERSION);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.log('🔴 Service Worker: Network failed, trying cache:', request.url);

    // Fall back to cache
    const cache = await caches.open(CACHE_VERSION);
    const cached = await cache.match(request);

    if (cached) {
      return cached;
    }

    // Return offline page if nothing cached
    return new Response('You are offline', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: new Headers({ 'Content-Type': 'text/plain' })
    });
  }
}

// =============================================
// Background Sync
// =============================================

self.addEventListener('sync', (event) => {
  console.log('🔄 Service Worker: Background sync event:', event.tag);

  if (event.tag === 'sync-queue') {
    event.waitUntil(syncPendingQueue());
  }
});

async function syncPendingQueue() {
  try {
    const response = await fetch('/api/sync/queue', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });

    if (response.ok) {
      const data = await response.json();
      console.log(`🔄 Service Worker: Syncing ${data.count} pending items`);

      // Notify client of sync status
      self.clients.matchAll().then((clients) => {
        clients.forEach((client) => {
          client.postMessage({
            type: 'SYNC_COMPLETE',
            pending: data.queue_stats?.pending || 0
          });
        });
      });
    }
  } catch (error) {
    console.error('❌ Service Worker: Background sync failed:', error);
    throw error; // Retry sync
  }
}

// =============================================
// Push Notifications
// =============================================

self.addEventListener('push', (event) => {
  console.log('📨 Service Worker: Push notification received');

  const data = event.data?.json() || {};
  const options = {
    body: data.body || 'New notification',
    icon: '/icon-192x192.png',
    badge: '/badge-72x72.png',
    tag: data.tag || 'notification',
    requireInteraction: data.requireInteraction || false,
    data: data.data || {}
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'GOTG-RIS', options)
  );
});

// =============================================
// Notification Click
// =============================================

self.addEventListener('notificationclick', (event) => {
  console.log('👆 Service Worker: Notification clicked');

  event.notification.close();

  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      // Focus existing window if open
      for (const client of clientList) {
        if (client.url === '/' && 'focus' in client) {
          return client.focus();
        }
      }
      // Open new window if not found
      if (clients.openWindow) {
        return clients.openWindow(event.notification.data.url || '/');
      }
    })
  );
});

// =============================================
// Message Event (Communication with client)
// =============================================

self.addEventListener('message', (event) => {
  const { type, payload } = event.data;

  console.log('💬 Service Worker: Message received:', type);

  if (type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (type === 'CACHE_URLS') {
    event.waitUntil(
      caches.open(CACHE_VERSION).then((cache) => {
        return cache.addAll(payload.urls);
      })
    );
  }

  if (type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.delete(CACHE_VERSION).then(() => {
        event.ports[0].postMessage({ success: true });
      })
    );
  }

  if (type === 'GET_CACHE_SIZE') {
    // Estimate cache size
    estimateCacheSize().then((size) => {
      event.ports[0].postMessage({ size });
    });
  }
});

async function estimateCacheSize() {
  if (!navigator.storage?.estimate) {
    return 0;
  }

  const estimate = await navigator.storage.estimate();
  return estimate.usage || 0;
}

// =============================================
// Update Check
// =============================================

setInterval(() => {
  console.log('🔄 Service Worker: Checking for updates');
  self.registration.update();
}, 60000); // Every minute

console.log('✅ Service Worker: Initialized and ready');
