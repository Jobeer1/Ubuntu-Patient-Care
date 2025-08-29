import axios from 'axios';
import toast from 'react-hot-toast';

/**
 * Unified API Client for Orthanc SA Integration
 * Supports both current Flask APIs and future Orthanc plugin APIs
 * Developer B - Phase 2 Migration Implementation
 */

class UnifiedAPIClient {
  constructor() {
    // Current Flask API client (for migration phase)
    this.flaskAPI = axios.create({
      baseURL: '/api',
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Future Orthanc Plugin API client (for unified system)
    this.orthancAPI = axios.create({
      baseURL: '/orthanc',
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Migration mode - allows gradual transition
    this.migrationMode = true;
    this.pluginEndpoints = new Set([
      // Add plugin endpoints as they become available
      // Example: '/auth/sa/login', '/sa/localization/languages'
    ]);

    this.setupInterceptors();
  }

  setupInterceptors() {
    // Flask API interceptors (current system)
    this.flaskAPI.interceptors.response.use(
      (response) => response,
      (error) => this.handleError(error, 'flask')
    );

    // Orthanc Plugin API interceptors (future system)
    this.orthancAPI.interceptors.response.use(
      (response) => response,
      (error) => this.handleError(error, 'orthanc')
    );
  }

  handleError(error, apiType) {
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 401:
          // Unauthorized - redirect to login
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
          break;
          
        case 403:
          // Forbidden - check if 2FA is required
          if (data.requires_2fa) {
            window.location.href = '/2fa/verify';
          } else if (data.requires_2fa_setup) {
            window.location.href = '/2fa/setup';
          } else {
            toast.error(data.error || 'Access denied');
          }
          break;
          
        case 404:
          if (apiType === 'orthanc' && this.migrationMode) {
            // Plugin endpoint not available yet, don't show error
            console.warn(`Plugin endpoint not available: ${error.config.url}`);
          } else {
            toast.error(data.error || 'Resource not found');
          }
          break;
          
        case 500:
          toast.error(data.error || 'Server error occurred');
          break;
          
        default:
          toast.error(data.error || `HTTP ${status} error`);
      }
    } else if (error.request) {
      toast.error('Network error - please check your connection');
    } else {
      toast.error('An unexpected error occurred');
    }
    
    return Promise.reject(error);
  }

  /**
   * Smart routing: Use plugin API if available, fallback to Flask API
   */
  async request(method, endpoint, data = null, config = {}) {
    const isPluginEndpoint = this.pluginEndpoints.has(endpoint);
    
    if (this.migrationMode && isPluginEndpoint) {
      try {
        // Try plugin API first
        return await this.orthancAPI.request({
          method,
          url: endpoint,
          data,
          ...config
        });
      } catch (error) {
        if (error.response?.status === 404) {
          // Plugin not available, fallback to Flask
          console.warn(`Plugin fallback for: ${endpoint}`);
          return await this.flaskAPI.request({
            method,
            url: endpoint.replace('/sa/', '/api/sa/').replace('/auth/sa/', '/api/auth/'),
            data,
            ...config
          });
        }
        throw error;
      }
    } else {
      // Use Flask API for non-migrated endpoints
      return await this.flaskAPI.request({
        method,
        url: endpoint,
        data,
        ...config
      });
    }
  }

  // Convenience methods
  async get(endpoint, config = {}) {
    return this.request('GET', endpoint, null, config);
  }

  async post(endpoint, data = null, config = {}) {
    return this.request('POST', endpoint, data, config);
  }

  async put(endpoint, data = null, config = {}) {
    return this.request('PUT', endpoint, data, config);
  }

  async delete(endpoint, config = {}) {
    return this.request('DELETE', endpoint, null, config);
  }

  // SA-specific API methods with smart routing

  // Authentication APIs
  async login(credentials) {
    return this.post('/auth/login', credentials);
  }

  async logout() {
    return this.post('/auth/logout');
  }

  async setup2FA() {
    return this.post('/auth/2fa/setup');
  }

  async verify2FA(token) {
    return this.post('/auth/2fa/verify', { token });
  }

  async getCurrentUser() {
    return this.get('/auth/user');
  }

  // SA Localization APIs
  async getSupportedLanguages() {
    return this.get('/sa/localization/languages');
  }

  async setLanguage(language) {
    return this.post('/sa/localization/set-language', { language });
  }

  // SA Voice Dictation APIs
  async startDictation(config = {}) {
    return this.get('/sa/voice/dictate', config);
  }

  async transcribeAudio(audioData) {
    return this.post('/sa/voice/transcribe', audioData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  }

  // SA Medical Templates APIs
  async getMedicalTemplates(type = null) {
    const endpoint = type ? `/sa/templates/${type}` : '/sa/templates';
    return this.get(endpoint);
  }

  async saveMedicalTemplate(templateData) {
    return this.post('/sa/templates', templateData);
  }

  // SA Healthcare Validation APIs
  async validateMedicalAid(memberNumber, scheme) {
    return this.post('/sa/medical-aid/validate', { memberNumber, scheme });
  }

  async validateHPCSA(number) {
    return this.get(`/sa/hpcsa/validate/${number}`);
  }

  // Enhanced DICOM APIs (with SA metadata)
  async getStudyWithSAMetadata(studyId) {
    if (this.pluginEndpoints.has('/dicom-web/studies')) {
      // Unified response from plugin
      return this.get(`/dicom-web/studies/${studyId}`);
    } else {
      // Separate calls during migration
      const [dicomResponse, saResponse] = await Promise.all([
        this.orthancAPI.get(`/studies/${studyId}`),
        this.get(`/images/${studyId}/sa-metadata`)
      ]);
      
      return {
        data: {
          ...dicomResponse.data,
          saMetadata: saResponse.data
        }
      };
    }
  }

  async getSeriesWithSAMetadata(seriesId) {
    if (this.pluginEndpoints.has('/dicom-web/series')) {
      return this.get(`/dicom-web/series/${seriesId}`);
    } else {
      const [dicomResponse, saResponse] = await Promise.all([
        this.orthancAPI.get(`/series/${seriesId}`),
        this.get(`/images/${seriesId}/sa-metadata`)
      ]);
      
      return {
        data: {
          ...dicomResponse.data,
          saMetadata: saResponse.data
        }
      };
    }
  }

  // Migration control methods
  enablePluginEndpoint(endpoint) {
    this.pluginEndpoints.add(endpoint);
    console.log(`Plugin endpoint enabled: ${endpoint}`);
  }

  disablePluginEndpoint(endpoint) {
    this.pluginEndpoints.delete(endpoint);
    console.log(`Plugin endpoint disabled: ${endpoint}`);
  }

  setMigrationMode(enabled) {
    this.migrationMode = enabled;
    console.log(`Migration mode: ${enabled ? 'enabled' : 'disabled'}`);
  }

  getPluginStatus() {
    return {
      migrationMode: this.migrationMode,
      enabledPluginEndpoints: Array.from(this.pluginEndpoints),
      totalEndpoints: this.pluginEndpoints.size
    };
  }
}

// Create singleton instance
const unifiedAPI = new UnifiedAPIClient();

// Export both the instance and the class for testing
export default unifiedAPI;
export { UnifiedAPIClient };

// Legacy export for backward compatibility during migration
export const api = unifiedAPI;
