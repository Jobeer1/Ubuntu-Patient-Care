/**
 * API Integration Module for 3D PACS Viewer
 * Handles all communication between frontend and backend REST APIs
 * 
 * Features:
 * - Study loading and caching
 * - Slice retrieval with streaming
 * - Metadata fetching
 * - MPR reconstruction
 * - Error handling and retry logic
 * - Request throttling and batching
 */

class ViewerAPIClient {
    constructor(baseURL = '/api/viewer', timeout = 30000) {
        this.baseURL = baseURL;
        this.timeout = timeout;
        this.requestQueue = [];
        this.isProcessing = false;
        this.cache = new Map();
        this.activeRequests = new Map();
        this.retryCount = 3;
        this.retryDelay = 1000; // ms
        
        // Add listeners for visibility changes to pause/resume requests
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseRequests();
            } else {
                this.resumeRequests();
            }
        });
    }

    /**
     * Load a complete DICOM study
     * @param {string} studyId - Study ID
     * @param {object} options - Load options
     * @returns {Promise<object>} Study metadata and initial thumbnail
     */
    async loadStudy(studyId, options = {}) {
        const {
            seriesId = null,
            windowCenter = 40,
            windowWidth = 400,
            useCache = true
        } = options;

        // Check cache first
        if (useCache && this.cache.has(`study_${studyId}`)) {
            console.log(`[APIClient] Returning cached study: ${studyId}`);
            return this.cache.get(`study_${studyId}`);
        }

        const requestData = {
            study_id: studyId,
            series_id: seriesId,
            window_center: windowCenter,
            window_width: windowWidth
        };

        try {
            console.log(`[APIClient] Loading study: ${studyId}`);
            const response = await this._post('/load-study', requestData);
            
            // Cache the result
            if (useCache) {
                this.cache.set(`study_${studyId}`, response);
            }
            
            console.log(`[APIClient] Study loaded successfully:`, response);
            return response;
        } catch (error) {
            console.error(`[APIClient] Error loading study ${studyId}:`, error);
            throw new Error(`Failed to load study: ${error.message}`);
        }
    }

    /**
     * Get a single slice from a loaded study
     * @param {string} studyId - Study ID
     * @param {number} sliceIndex - Slice index
     * @param {object} options - Additional options
     * @returns {Promise<object>} Slice data
     */
    async getSlice(studyId, sliceIndex, options = {}) {
        const {
            normalize = true,
            useCache = true
        } = options;

        // Check cache
        const cacheKey = `slice_${studyId}_${sliceIndex}`;
        if (useCache && this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }

        const params = new URLSearchParams({
            slice_index: sliceIndex,
            normalize: normalize
        });

        try {
            console.log(`[APIClient] Loading slice ${sliceIndex} from study ${studyId}`);
            const response = await this._get(`/get-slice/${studyId}?${params}`);
            
            // Cache if configured
            if (useCache) {
                this.cache.set(cacheKey, response);
            }
            
            return response;
        } catch (error) {
            console.error(`[APIClient] Error loading slice:`, error);
            throw error;
        }
    }

    /**
     * Get multiple slices in batch (more efficient than individual calls)
     * @param {string} studyId - Study ID
     * @param {number[]} sliceIndices - Array of slice indices
     * @param {object} options - Options
     * @returns {Promise<object[]>} Array of slice data
     */
    async getSlicesBatch(studyId, sliceIndices, options = {}) {
        console.log(`[APIClient] Loading ${sliceIndices.length} slices in batch`);
        
        // Batch requests by grouping them
        const batchSize = 5;
        const results = [];
        
        for (let i = 0; i < sliceIndices.length; i += batchSize) {
            const batch = sliceIndices.slice(i, i + batchSize);
            
            // Execute batch in parallel
            const batchPromises = batch.map(idx => 
                this.getSlice(studyId, idx, options)
            );
            
            const batchResults = await Promise.all(batchPromises);
            results.push(...batchResults);
        }
        
        return results;
    }

    /**
     * Get study metadata
     * @param {string} studyId - Study ID
     * @returns {Promise<object>} Metadata
     */
    async getMetadata(studyId) {
        // Check cache
        const cacheKey = `metadata_${studyId}`;
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }

        try {
            console.log(`[APIClient] Fetching metadata for study ${studyId}`);
            const response = await this._get(`/get-metadata/${studyId}`);
            
            // Cache metadata
            this.cache.set(cacheKey, response);
            console.log(`[APIClient] Metadata retrieved:`, response);
            
            return response;
        } catch (error) {
            console.error(`[APIClient] Error fetching metadata:`, error);
            throw error;
        }
    }

    /**
     * Get MPR (Multiplanar Reconstruction) slice
     * @param {string} studyId - Study ID
     * @param {string} plane - Plane ('axial', 'sagittal', 'coronal')
     * @param {number} position - Position (0.0-1.0)
     * @returns {Promise<object>} MPR slice data
     */
    async getMPRSlice(studyId, plane, position) {
        const requestData = {
            study_id: studyId,
            plane: plane,
            position: Math.max(0, Math.min(1, position)) // Clamp to 0-1
        };

        try {
            console.log(`[APIClient] Requesting ${plane} MPR at position ${position}`);
            const response = await this._post('/mpr-slice', requestData);
            return response;
        } catch (error) {
            console.error(`[APIClient] Error getting MPR slice:`, error);
            throw error;
        }
    }

    /**
     * Get thumbnail for a study
     * @param {string} studyId - Study ID
     * @returns {string} URL to thumbnail image
     */
    getThumbnailURL(studyId) {
        return `${this.baseURL}/thumbnail/${studyId}`;
    }

    /**
     * Get thumbnail as blob
     * @param {string} studyId - Study ID
     * @returns {Promise<Blob>} Thumbnail image blob
     */
    async getThumbnail(studyId) {
        try {
            const response = await fetch(`${this.baseURL}/thumbnail/${studyId}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.blob();
        } catch (error) {
            console.error(`[APIClient] Error fetching thumbnail:`, error);
            throw error;
        }
    }

    /**
     * Clear study cache on server
     * @param {string} studyId - Study ID (or null to clear all)
     * @returns {Promise<object>} Result
     */
    async clearStudyCache(studyId = null) {
        try {
            const url = studyId ? `/clear-cache/${studyId}` : '/clear-cache';
            const response = await this._delete(url);
            console.log(`[APIClient] Cache cleared for ${studyId || 'all studies'}`);
            
            // Also clear local cache
            if (studyId) {
                for (let [key] of this.cache) {
                    if (key.includes(studyId)) {
                        this.cache.delete(key);
                    }
                }
            } else {
                this.cache.clear();
            }
            
            return response;
        } catch (error) {
            console.error(`[APIClient] Error clearing cache:`, error);
            throw error;
        }
    }

    /**
     * Get cache status
     * @returns {Promise<object>} Cache statistics
     */
    async getCacheStatus() {
        try {
            const response = await this._get('/cache-status');
            console.log(`[APIClient] Cache status:`, response);
            return response;
        } catch (error) {
            console.error(`[APIClient] Error getting cache status:`, error);
            throw error;
        }
    }

    /**
     * Check health of viewer API
     * @returns {Promise<object>} Health status
     */
    async getHealthStatus() {
        try {
            const response = await this._get('/health');
            return response;
        } catch (error) {
            console.error(`[APIClient] Health check failed:`, error);
            throw error;
        }
    }

    /**
     * Clear local frontend cache
     */
    clearLocalCache() {
        this.cache.clear();
        console.log('[APIClient] Local cache cleared');
    }

    /**
     * Get cache size in MB
     * @returns {number} Approximate size in MB
     */
    getCacheSize() {
        let size = 0;
        for (let [key, value] of this.cache) {
            if (value && typeof value === 'object') {
                size += JSON.stringify(value).length;
            }
        }
        return size / (1024 * 1024); // Convert to MB
    }

    /**
     * Internal HTTP GET request
     * @private
     */
    async _get(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        return this._request('GET', url, null, options);
    }

    /**
     * Internal HTTP POST request
     * @private
     */
    async _post(endpoint, data, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        return this._request('POST', url, data, options);
    }

    /**
     * Internal HTTP DELETE request
     * @private
     */
    async _delete(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        return this._request('DELETE', url, null, options);
    }

    /**
     * Core request handler with retry logic
     * @private
     */
    async _request(method, url, data = null, options = {}) {
        const {
            retries = this.retryCount,
            timeout = this.timeout
        } = options;

        let lastError;

        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), timeout);

                const fetchOptions = {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    signal: controller.signal
                };

                if (data) {
                    fetchOptions.body = JSON.stringify(data);
                }

                const response = await fetch(url, fetchOptions);
                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();
                return result;

            } catch (error) {
                lastError = error;

                if (attempt < retries) {
                    const delay = this.retryDelay * Math.pow(2, attempt); // Exponential backoff
                    console.warn(`[APIClient] Attempt ${attempt + 1} failed: ${error.message}. Retrying in ${delay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                } else {
                    console.error(`[APIClient] All ${retries + 1} attempts failed:`, error);
                }
            }
        }

        throw lastError;
    }

    /**
     * Pause all active requests
     * @private
     */
    pauseRequests() {
        console.log('[APIClient] Pausing requests (page hidden)');
        this.isProcessing = false;
    }

    /**
     * Resume processing requests
     * @private
     */
    resumeRequests() {
        console.log('[APIClient] Resuming requests (page visible)');
        this.isProcessing = true;
    }

    /**
     * Clear cache if it exceeds size limit (in MB)
     * @param {number} maxSizeMB - Maximum cache size
     */
    limitCacheSize(maxSizeMB = 100) {
        const currentSize = this.getCacheSize();
        
        if (currentSize > maxSizeMB) {
            console.warn(`[APIClient] Cache size ${currentSize.toFixed(2)}MB exceeds limit ${maxSizeMB}MB. Clearing...`);
            this.clearLocalCache();
        }
    }
}

/**
 * Global viewer API client instance
 */
let viewerAPI = null;

/**
 * Initialize the viewer API client
 * @param {object} config - Configuration options
 * @returns {ViewerAPIClient} Client instance
 */
function initializeViewerAPI(config = {}) {
    const baseURL = config.baseURL || '/api/viewer';
    const timeout = config.timeout || 30000;
    
    viewerAPI = new ViewerAPIClient(baseURL, timeout);
    console.log('[APIClient] Viewer API client initialized');
    
    return viewerAPI;
}

/**
 * Get global viewer API client
 * @returns {ViewerAPIClient} Client instance
 */
function getViewerAPI() {
    if (!viewerAPI) {
        viewerAPI = new ViewerAPIClient();
    }
    return viewerAPI;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ViewerAPIClient, initializeViewerAPI, getViewerAPI };
}
