/**
 * 🇿🇦 SA Medical Service Worker
 * 
 * Provides offline capabilities and caching for the SA DICOM viewer
 */

const CACHE_NAME = 'sa-medical-viewer-v1.0.0';
const STATIC_CACHE_NAME = 'sa-medical-static-v1.0.0';
const DYNAMIC_CACHE_NAME = 'sa-medical-dynamic-v1.0.0';
const DICOM_CACHE_NAME = 'sa-medical-dicom-v1.0.0';

// Static assets to cache immediately
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/sa-ohif-integration.js',
    '/themes/sa-medical-theme.js',
    '/plugins/sa-compliance-plugin.js',
    '/plugins/sa-mobile-plugin.js',
    '/plugins/sa-language-plugin.js',
    // OHIF dependencies from CDN
    'https://unpkg.com/@ohif/core@latest/dist/index.umd.js',
    'https://unpkg.com/@ohif/ui@latest/dist/index.umd.js',
    'https://unpkg.com/@ohif/extension-cornerstone@latest/dist/index.umd.js',
    'https://unpkg.com/@ohif/extension-default@latest/dist/index.umd.js',
    'https://unpkg.com/cornerstone-core@latest/dist/cornerstone.min.js',
    'https://unpkg.com/cornerstone-math@latest/dist/cornerstoneMath.min.js',
    'https://unpkg.com/cornerstone-tools@latest/dist/cornerstoneTools.min.js',
    'https://unpkg.com/cornerstone-wado-image-loader@latest/dist/cornerstoneWADOImageLoader.bundle.min.js',
    'https://unpkg.com/cornerstone-web-image-loader@latest/dist/cornerstoneWebImageLoader.min.js',
    'https://unpkg.com/dicom-parser@latest/dist/dicomParser.min.js'
];

// Network timeouts for different types of requests
const TIMEOUTS = {
    static: 5000,    // 5 seconds for static assets
    api: 10000,      // 10 seconds for API calls
    dicom: 30000     // 30 seconds for DICOM images
};

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('🇿🇦 SA Medical SW: Installing');
    
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME)
            .then((cache) => {
                console.log('SA Medical SW: Caching static assets');
                return cache.addAll(STATIC_ASSETS.map(url => {
                    return new Request(url, { mode: 'cors' });
                }));
            })
            .then(() => {
                console.log('SA Medical SW: Static assets cached');
                self.skipWaiting();
            })
            .catch((error) => {
                console.error('SA Medical SW: Failed to cache static assets:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('🇿🇦 SA Medical SW: Activating');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== STATIC_CACHE_NAME && 
                            cacheName !== DYNAMIC_CACHE_NAME && 
                            cacheName !== DICOM_CACHE_NAME) {
                            console.log('SA Medical SW: Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('SA Medical SW: Cache cleanup complete');
                self.clients.claim();
            })
    );
});

// Fetch event - handle all network requests
self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip chrome-extension requests
    if (url.protocol === 'chrome-extension:') {
        return;
    }
    
    // Handle different types of requests
    if (isStaticAsset(url)) {
        event.respondWith(handleStaticAsset(request));
    } else if (isDicomRequest(url)) {
        event.respondWith(handleDicomRequest(request));
    } else if (isApiRequest(url)) {
        event.respondWith(handleApiRequest(request));
    } else {
        event.respondWith(handleDynamicRequest(request));
    }
});

// Check if request is for a static asset
function isStaticAsset(url) {
    return STATIC_ASSETS.some(asset => {
        if (asset.startsWith('http')) {
            return url.href === asset;
        }
        return url.pathname === asset || url.pathname.endsWith(asset);
    }) || 
    url.pathname.endsWith('.js') ||
    url.pathname.endsWith('.css') ||
    url.pathname.endsWith('.html') ||
    url.pathname.includes('/plugins/') ||
    url.pathname.includes('/themes/');
}

// Check if request is for DICOM data
function isDicomRequest(url) {
    return url.pathname.includes('/dicom-web/') ||
           url.pathname.includes('/wado') ||
           url.pathname.includes('/studies/') ||
           url.pathname.includes('/series/') ||
           url.pathname.includes('/instances/') ||
           url.searchParams.has('requestType') && 
           ['WADO', 'QIDO', 'STOW'].includes(url.searchParams.get('requestType'));
}

// Check if request is for API endpoints
function isApiRequest(url) {
    return url.pathname.startsWith('/api/');
}

// Handle static asset requests - cache first strategy
async function handleStaticAsset(request) {
    try {
        const cache = await caches.open(STATIC_CACHE_NAME);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse) {
            console.log('SA Medical SW: Serving from cache:', request.url);
            return cachedResponse;
        }
        
        console.log('SA Medical SW: Fetching static asset:', request.url);
        const networkResponse = await fetchWithTimeout(request, TIMEOUTS.static);
        
        // Cache the response
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.error('SA Medical SW: Static asset fetch failed:', error);
        
        // Return offline fallback if available
        if (request.url.includes('index.html') || request.url.endsWith('/')) {
            return createOfflinePage();
        }
        
        throw error;
    }
}

// Handle DICOM requests - cache with network fallback
async function handleDicomRequest(request) {
    try {
        const cache = await caches.open(DICOM_CACHE_NAME);
        
        // For SA networks, try cache first for better performance
        const cachedResponse = await cache.match(request);
        if (cachedResponse) {
            console.log('SA Medical SW: Serving DICOM from cache:', request.url);
            
            // Update cache in background for next time
            fetchWithTimeout(request, TIMEOUTS.dicom)
                .then(response => {
                    if (response.ok) {
                        cache.put(request, response.clone());
                    }
                })
                .catch(() => {}); // Silent fail for background update
                
            return cachedResponse;
        }
        
        console.log('SA Medical SW: Fetching DICOM from network:', request.url);
        const networkResponse = await fetchWithTimeout(request, TIMEOUTS.dicom);
        
        // Cache successful DICOM responses
        if (networkResponse.ok) {
            // Only cache smaller DICOM responses to avoid storage issues
            const contentLength = networkResponse.headers.get('content-length');
            if (!contentLength || parseInt(contentLength) < 10 * 1024 * 1024) { // 10MB limit
                cache.put(request, networkResponse.clone());
            }
        }
        
        return networkResponse;
        
    } catch (error) {
        console.error('SA Medical SW: DICOM fetch failed:', error);
        
        // Try to return cached version
        const cache = await caches.open(DICOM_CACHE_NAME);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse) {
            console.log('SA Medical SW: Returning stale DICOM cache:', request.url);
            return cachedResponse;
        }
        
        // Return error response
        return new Response(
            JSON.stringify({
                error: 'DICOM data unavailable offline',
                url: request.url,
                timestamp: new Date().toISOString()
            }),
            {
                status: 503,
                statusText: 'Service Unavailable',
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Handle API requests - network first with cache fallback
async function handleApiRequest(request) {
    try {
        console.log('SA Medical SW: Fetching API:', request.url);
        const networkResponse = await fetchWithTimeout(request, TIMEOUTS.api);
        
        // Cache successful API responses (except auth endpoints)
        if (networkResponse.ok && !request.url.includes('/auth/')) {
            const cache = await caches.open(DYNAMIC_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.error('SA Medical SW: API fetch failed:', error);
        
        // Try cache for non-critical API calls
        if (!request.url.includes('/auth/')) {
            const cache = await caches.open(DYNAMIC_CACHE_NAME);
            const cachedResponse = await cache.match(request);
            
            if (cachedResponse) {
                console.log('SA Medical SW: Returning cached API response:', request.url);
                return cachedResponse;
            }
        }
        
        // Return error response
        return new Response(
            JSON.stringify({
                error: 'API unavailable offline',
                url: request.url,
                timestamp: new Date().toISOString()
            }),
            {
                status: 503,
                statusText: 'Service Unavailable',
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Handle dynamic requests - network with cache fallback
async function handleDynamicRequest(request) {
    try {
        const networkResponse = await fetchWithTimeout(request, TIMEOUTS.static);
        
        // Cache non-sensitive dynamic content
        if (networkResponse.ok && !request.url.includes('secure')) {
            const cache = await caches.open(DYNAMIC_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.error('SA Medical SW: Dynamic fetch failed:', error);
        
        // Try cache
        const cache = await caches.open(DYNAMIC_CACHE_NAME);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        throw error;
    }
}

// Fetch with timeout for SA network conditions
function fetchWithTimeout(request, timeout) {
    return Promise.race([
        fetch(request),
        new Promise((_, reject) => {
            setTimeout(() => {
                reject(new Error(`Network timeout after ${timeout}ms`));
            }, timeout);
        })
    ]);
}

// Create offline fallback page
function createOfflinePage() {
    const offlineHTML = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>SA Medical Viewer - Offline</title>
            <style>
                body {
                    font-family: 'Roboto', sans-serif;
                    background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
                    color: white;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    text-align: center;
                }
                .offline-icon {
                    font-size: 64px;
                    margin-bottom: 20px;
                }
                .offline-title {
                    font-size: 28px;
                    font-weight: 600;
                    margin-bottom: 10px;
                }
                .offline-message {
                    font-size: 16px;
                    margin-bottom: 30px;
                    max-width: 400px;
                    line-height: 1.5;
                }
                .offline-actions {
                    display: flex;
                    gap: 15px;
                    flex-wrap: wrap;
                    justify-content: center;
                }
                .offline-btn {
                    background: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    color: white;
                    padding: 12px 24px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                    text-decoration: none;
                    transition: background 0.2s;
                }
                .offline-btn:hover {
                    background: rgba(255, 255, 255, 0.3);
                }
                .sa-flag-accent {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: linear-gradient(
                        to right,
                        #007749 0%, #007749 16.66%,
                        #ffffff 16.66%, #ffffff 33.33%,
                        #de3831 33.33%, #de3831 50%,
                        #ffffff 50%, #ffffff 66.66%,
                        #001489 66.66%, #001489 83.33%,
                        #ffb81c 83.33%, #ffb81c 100%
                    );
                }
            </style>
        </head>
        <body>
            <div class="sa-flag-accent"></div>
            
            <div class="offline-icon">📡</div>
            <div class="offline-title">SA Medical Viewer - Offline Mode</div>
            <div class="offline-message">
                You're currently offline. The SA Medical DICOM Viewer will work with limited 
                functionality using cached data. Some features may not be available until 
                you're back online.
            </div>
            
            <div class="offline-actions">
                <button class="offline-btn" onclick="location.reload()">
                    Try Again
                </button>
                <button class="offline-btn" onclick="window.history.back()">
                    Go Back
                </button>
            </div>
            
            <script>
                // Auto-reload when back online
                window.addEventListener('online', () => {
                    setTimeout(() => {
                        location.reload();
                    }, 1000);
                });
                
                // Check connection periodically
                setInterval(() => {
                    if (navigator.onLine) {
                        location.reload();
                    }
                }, 30000); // Check every 30 seconds
            </script>
        </body>
        </html>
    `;
    
    return new Response(offlineHTML, {
        headers: { 'Content-Type': 'text/html' }
    });
}

// Background sync for when connection is restored
self.addEventListener('sync', (event) => {
    if (event.tag === 'sa-medical-sync') {
        console.log('SA Medical SW: Background sync triggered');
        event.waitUntil(performBackgroundSync());
    }
});

// Perform background sync operations
async function performBackgroundSync() {
    try {
        // Clear old DICOM cache entries
        const dicomCache = await caches.open(DICOM_CACHE_NAME);
        const dicomKeys = await dicomCache.keys();
        
        // Remove entries older than 24 hours
        const oneDayAgo = Date.now() - (24 * 60 * 60 * 1000);
        
        for (const request of dicomKeys) {
            const response = await dicomCache.match(request);
            if (response) {
                const dateHeader = response.headers.get('date');
                if (dateHeader && new Date(dateHeader).getTime() < oneDayAgo) {
                    await dicomCache.delete(request);
                }
            }
        }
        
        console.log('SA Medical SW: Background sync completed');
        
    } catch (error) {
        console.error('SA Medical SW: Background sync failed:', error);
    }
}

// Handle messages from the main thread
self.addEventListener('message', (event) => {
    const { type, payload } = event.data;
    
    switch (type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;
            
        case 'CACHE_STUDY':
            if (payload && payload.studyData) {
                cacheStudyData(payload.studyData);
            }
            break;
            
        case 'CLEAR_CACHE':
            clearAllCaches();
            break;
            
        case 'GET_CACHE_SIZE':
            getCacheSize().then(size => {
                event.ports[0].postMessage({ type: 'CACHE_SIZE', size });
            });
            break;
    }
});

// Cache study data for offline access
async function cacheStudyData(studyData) {
    try {
        const cache = await caches.open(DICOM_CACHE_NAME);
        
        // Cache study metadata
        const studyRequest = new Request(`/studies/${studyData.studyInstanceUID}`);
        const studyResponse = new Response(JSON.stringify(studyData), {
            headers: { 'Content-Type': 'application/json' }
        });
        
        await cache.put(studyRequest, studyResponse);
        
        console.log('SA Medical SW: Study cached for offline access:', studyData.studyInstanceUID);
        
    } catch (error) {
        console.error('SA Medical SW: Failed to cache study:', error);
    }
}

// Clear all caches
async function clearAllCaches() {
    try {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map(name => caches.delete(name)));
        console.log('SA Medical SW: All caches cleared');
    } catch (error) {
        console.error('SA Medical SW: Failed to clear caches:', error);
    }
}

// Get total cache size
async function getCacheSize() {
    try {
        let totalSize = 0;
        const cacheNames = await caches.keys();
        
        for (const cacheName of cacheNames) {
            const cache = await caches.open(cacheName);
            const keys = await cache.keys();
            
            for (const request of keys) {
                const response = await cache.match(request);
                if (response) {
                    const blob = await response.blob();
                    totalSize += blob.size;
                }
            }
        }
        
        return {
            bytes: totalSize,
            mb: (totalSize / (1024 * 1024)).toFixed(2)
        };
        
    } catch (error) {
        console.error('SA Medical SW: Failed to calculate cache size:', error);
        return { bytes: 0, mb: '0.00' };
    }
}
