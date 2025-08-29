/**
 * Service Worker for South African Medical Imaging PWA
 * Provides offline functionality and background sync
 */

const CACHE_NAME = 'sa-medical-imaging-v1.0.0';
const STATIC_CACHE = 'static-v1.0.0';
const DYNAMIC_CACHE = 'dynamic-v1.0.0';
const IMAGE_CACHE = 'images-v1.0.0';

// Files to cache immediately
const STATIC_FILES = [
    '/',
    '/index.html',
    '/static/css/main.css',
    '/static/js/main.js',
    '/static/js/mobile-framework.js',
    '/manifest.json',
    '/offline.html',
    // South African specific assets
    '/assets/flags/za.svg',
    '/assets/languages/en-za.json',
    '/assets/languages/af.json',
    '/assets/languages/zu.json'
];

// Critical medical imaging files
const CRITICAL_FILES = [
    '/api/auth/verify',
    '/api/user/profile',
    '/api/studies/recent',
    '/static/fonts/medical-icons.woff2'
];

// Install event - cache static files
self.addEventListener('install', (event) => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        Promise.all([
            caches.open(STATIC_CACHE).then(cache => {
                console.log('Service Worker: Caching static files');
                return cache.addAll(STATIC_FILES);
            }),
            caches.open(DYNAMIC_CACHE).then(cache => {
                console.log('Service Worker: Caching critical files');
                return cache.addAll(CRITICAL_FILES);
            })
        ]).then(() => {
            console.log('Service Worker: Installation complete');
            return self.skipWaiting();
        }).catch(error => {
            console.error('Service Worker: Installation failed', error);
        })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== STATIC_CACHE && 
                        cacheName !== DYNAMIC_CACHE && 
                        cacheName !== IMAGE_CACHE) {
                        console.log('Service Worker: Deleting old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            console.log('Service Worker: Activation complete');
            return self.clients.claim();
        })
    );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Handle different types of requests
    if (request.method === 'GET') {
        if (isStaticFile(url.pathname)) {
            event.respondWith(handleStaticFile(request));
        } else if (isAPIRequest(url.pathname)) {
            event.respondWith(handleAPIRequest(request));
        } else if (isDICOMImage(url.pathname)) {
            event.respondWith(handleDICOMImage(request));
        } else {
            event.respondWith(handleDynamicContent(request));
        }
    } else if (request.method === 'POST') {
        event.respondWith(handlePOSTRequest(request));
    }
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
    console.log('Service Worker: Background sync triggered', event.tag);
    
    if (event.tag === 'sync-offline-actions') {
        event.waitUntil(syncOfflineActions());
    } else if (event.tag === 'sync-measurements') {
        event.waitUntil(syncMeasurements());
    } else if (event.tag === 'sync-annotations') {
        event.waitUntil(syncAnnotations());
    }
});

// Push notifications for critical alerts
self.addEventListener('push', (event) => {
    console.log('Service Worker: Push notification received');
    
    const options = {
        body: 'New critical imaging study available',
        icon: '/assets/icons/icon-192x192.png',
        badge: '/assets/icons/badge-72x72.png',
        vibrate: [200, 100, 200],
        data: {
            url: '/studies/critical'
        },
        actions: [
            {
                action: 'view',
                title: 'View Study',
                icon: '/assets/icons/view-icon.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss',
                icon: '/assets/icons/dismiss-icon.png'
            }
        ]
    };
    
    if (event.data) {
        const data = event.data.json();
        options.body = data.message || options.body;
        options.data = { ...options.data, ...data };
    }
    
    event.waitUntil(
        self.registration.showNotification('SA Medical Imaging', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
    console.log('Service Worker: Notification clicked', event.action);
    
    event.notification.close();
    
    if (event.action === 'view') {
        event.waitUntil(
            clients.openWindow(event.notification.data.url || '/')
        );
    }
});

// Utility functions
function isStaticFile(pathname) {
    return pathname.startsWith('/static/') || 
           pathname.endsWith('.css') || 
           pathname.endsWith('.js') || 
           pathname.endsWith('.woff2') ||
           pathname === '/' ||
           pathname === '/manifest.json';
}

function isAPIRequest(pathname) {
    return pathname.startsWith('/api/');
}

function isDICOMImage(pathname) {
    return pathname.includes('/dicom/') || 
           pathname.includes('/images/') ||
           pathname.endsWith('.dcm');
}

async function handleStaticFile(request) {
    try {
        // Try cache first
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Fetch from network and cache
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.error('Service Worker: Static file error', error);
        
        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
            return caches.match('/offline.html');
        }
        
        throw error;
    }
}

async function handleAPIRequest(request) {
    try {
        // Try network first for API requests
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Cache successful responses
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('Service Worker: API request failed, trying cache', request.url);
        
        // Try cache if network fails
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline response for critical endpoints
        if (isCriticalEndpoint(request.url)) {
            return new Response(JSON.stringify({
                error: 'Offline',
                message: 'This feature is not available offline',
                offline: true
            }), {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            });
        }
        
        throw error;
    }
}

async function handleDICOMImage(request) {
    try {
        // Check cache first for images
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Fetch from network
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Cache DICOM images with size limit
            const cache = await caches.open(IMAGE_CACHE);
            
            // Only cache if image is not too large (< 10MB)
            const contentLength = networkResponse.headers.get('content-length');
            if (!contentLength || parseInt(contentLength) < 10 * 1024 * 1024) {
                cache.put(request, networkResponse.clone());
            }
        }
        
        return networkResponse;
    } catch (error) {
        console.error('Service Worker: DICOM image error', error);
        
        // Return placeholder image for offline
        return new Response(
            '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">' +
            '<rect width="400" height="300" fill="#f0f0f0"/>' +
            '<text x="200" y="150" text-anchor="middle" fill="#666">Image unavailable offline</text>' +
            '</svg>',
            { headers: { 'Content-Type': 'image/svg+xml' } }
        );
    }
}

async function handleDynamicContent(request) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
            return caches.match('/offline.html');
        }
        
        throw error;
    }
}

async function handlePOSTRequest(request) {
    try {
        // Try network first
        return await fetch(request);
    } catch (error) {
        console.log('Service Worker: POST request failed, queuing for sync');
        
        // Queue for background sync
        const requestData = {
            url: request.url,
            method: request.method,
            headers: Object.fromEntries(request.headers.entries()),
            body: await request.text(),
            timestamp: Date.now()
        };
        
        // Store in IndexedDB for background sync
        await storeOfflineAction(requestData);
        
        // Register background sync
        await self.registration.sync.register('sync-offline-actions');
        
        return new Response(JSON.stringify({
            success: true,
            message: 'Action queued for sync when online',
            queued: true
        }), {
            status: 202,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

function isCriticalEndpoint(url) {
    const criticalPaths = [
        '/api/auth/',
        '/api/user/',
        '/api/studies/recent',
        '/api/emergency/'
    ];
    
    return criticalPaths.some(path => url.includes(path));
}

// IndexedDB operations for offline storage
async function storeOfflineAction(actionData) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('SAMedicalImaging', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['offlineActions'], 'readwrite');
            const store = transaction.objectStore('offlineActions');
            
            store.add(actionData);
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        };
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('offlineActions')) {
                const store = db.createObjectStore('offlineActions', { keyPath: 'timestamp' });
                store.createIndex('url', 'url', { unique: false });
            }
        };
    });
}

async function syncOfflineActions() {
    console.log('Service Worker: Syncing offline actions');
    
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('SAMedicalImaging', 1);
        
        request.onsuccess = async () => {
            const db = request.result;
            const transaction = db.transaction(['offlineActions'], 'readonly');
            const store = transaction.objectStore('offlineActions');
            const getAllRequest = store.getAll();
            
            getAllRequest.onsuccess = async () => {
                const actions = getAllRequest.result;
                
                for (const action of actions) {
                    try {
                        const response = await fetch(action.url, {
                            method: action.method,
                            headers: action.headers,
                            body: action.body
                        });
                        
                        if (response.ok) {
                            // Remove successful action from storage
                            const deleteTransaction = db.transaction(['offlineActions'], 'readwrite');
                            const deleteStore = deleteTransaction.objectStore('offlineActions');
                            deleteStore.delete(action.timestamp);
                        }
                    } catch (error) {
                        console.error('Service Worker: Failed to sync action', error);
                    }
                }
                
                resolve();
            };
        };
        
        request.onerror = () => reject(request.error);
    });
}

async function syncMeasurements() {
    console.log('Service Worker: Syncing measurements');
    // Implementation for syncing offline measurements
}

async function syncAnnotations() {
    console.log('Service Worker: Syncing annotations');
    // Implementation for syncing offline annotations
}

// Periodic cache cleanup
setInterval(async () => {
    const cache = await caches.open(IMAGE_CACHE);
    const requests = await cache.keys();
    
    // Remove old cached images (older than 7 days)
    const oneWeekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
    
    for (const request of requests) {
        const response = await cache.match(request);
        const dateHeader = response.headers.get('date');
        
        if (dateHeader && new Date(dateHeader).getTime() < oneWeekAgo) {
            await cache.delete(request);
        }
    }
}, 24 * 60 * 60 * 1000); // Run daily