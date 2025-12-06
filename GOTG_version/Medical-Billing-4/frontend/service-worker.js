// Medical Billing Service Worker - Offline-First Operation
const CACHE_VERSION = 'mb-v1';
const CACHE_NAME = `medical-billing-${CACHE_VERSION}`;

const CACHED_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './package.json'
];

const API_ENDPOINTS = [
  '/api/insurance/',
  '/api/claims/',
  '/api/revenue/',
  '/api/sync/',
  '/api/admin/'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Caching static assets');
      return cache.addAll(CACHED_ASSETS).catch(err => {
        console.warn('Some assets failed to cache:', err);
        // Continue even if some assets fail
        return Promise.resolve();
      });
    }).then(() => {
      console.log('Service Worker installation complete');
      return self.skipWaiting();
    })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('Service Worker activation complete');
      return self.clients.claim();
    })
  );
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // For API requests - network first with offline fallback
  if (API_ENDPOINTS.some(endpoint => url.pathname.includes(endpoint))) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Clone and cache successful responses
          if (response.status === 200) {
            const clonedResponse = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, clonedResponse);
            });
          }
          return response;
        })
        .catch(err => {
          // Network failed, try cache
          return caches.match(request)
            .then(response => {
              if (response) {
                console.log('Using cached response for:', request.url);
                return response;
              }
              
              // Return offline response
              return new Response(
                JSON.stringify({
                  error: 'Offline - Request queued for sync',
                  request_url: request.url,
                  timestamp: new Date().toISOString()
                }),
                {
                  status: 503,
                  statusText: 'Service Unavailable',
                  headers: { 'Content-Type': 'application/json' }
                }
              );
            });
        })
    );
    return;
  }

  // For static assets - cache first
  event.respondWith(
    caches.match(request)
      .then(response => {
        if (response) {
          return response;
        }
        
        return fetch(request)
          .then(response => {
            // Cache successful responses
            if (response.status === 200) {
              const clonedResponse = response.clone();
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(request, clonedResponse);
              });
            }
            return response;
          })
          .catch(err => {
            // Return offline page
            return new Response(
              '<h1>Offline</h1><p>This page is not available offline</p>',
              {
                status: 503,
                statusText: 'Service Unavailable',
                headers: { 'Content-Type': 'text/html' }
              }
            );
          });
      })
  );
});

// Handle messages from clients
self.addEventListener('message', (event) => {
  const { type, data } = event.data;

  if (type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (type === 'CLEAR_CACHE') {
    caches.delete(CACHE_NAME).then(() => {
      event.ports[0].postMessage({ success: true });
    });
  }

  if (type === 'GET_CACHE_SIZE') {
    caches.open(CACHE_NAME).then((cache) => {
      cache.keys().then((keys) => {
        event.ports[0].postMessage({ cache_count: keys.length });
      });
    });
  }

  if (type === 'QUEUE_REQUEST') {
    // Queue API request for later sync
    console.log('Queuing request for later sync:', data);
    
    // Store in IndexedDB for persistent queue
    const dbRequest = indexedDB.open('medical-billing-sync');
    
    dbRequest.onsuccess = () => {
      const db = dbRequest.result;
      const transaction = db.transaction(['requests'], 'readwrite');
      const store = transaction.objectStore('requests');
      
      store.add({
        url: data.url,
        method: data.method,
        body: data.body,
        timestamp: Date.now(),
        status: 'pending'
      });
    };
  }
});

// Background sync for queued requests
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-requests') {
    event.waitUntil(syncQueuedRequests());
  }
});

async function syncQueuedRequests() {
  const dbRequest = indexedDB.open('medical-billing-sync');
  
  return new Promise((resolve) => {
    dbRequest.onsuccess = () => {
      const db = dbRequest.result;
      const transaction = db.transaction(['requests'], 'readwrite');
      const store = transaction.objectStore('requests');
      const query = store.getAll();

      query.onsuccess = async () => {
        const requests = query.result;
        
        for (const req of requests) {
          if (req.status === 'pending') {
            try {
              const response = await fetch(req.url, {
                method: req.method,
                body: req.body,
                headers: { 'Content-Type': 'application/json' }
              });

              if (response.ok) {
                // Mark as synced
                const updateTransaction = db.transaction(['requests'], 'readwrite');
                const updateStore = updateTransaction.objectStore('requests');
                req.status = 'synced';
                updateStore.put(req);
              }
            } catch (err) {
              console.error('Failed to sync request:', err);
            }
          }
        }
        
        resolve();
      };
    };
  });
}

// Initialize IndexedDB for request queue
const dbRequest = indexedDB.open('medical-billing-sync', 1);

dbRequest.onupgradeneeded = (event) => {
  const db = event.target.result;
  
  if (!db.objectStoreNames.contains('requests')) {
    db.createObjectStore('requests', { keyPath: 'id', autoIncrement: true });
  }
};

console.log('Medical Billing Service Worker loaded');
