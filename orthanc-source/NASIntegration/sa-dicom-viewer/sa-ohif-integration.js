/**
 * 🇿🇦 SA OHIF Integration Configuration
 * 
 * Main configuration file integrating all SA-specific plugins and settings
 */

import saCompliancePlugin from './plugins/sa-compliance-plugin.js';
import saMobilePlugin from './plugins/sa-mobile-plugin.js';
import saLanguagePlugin from './plugins/sa-language-plugin.js';
import saMedicalTheme from './themes/sa-medical-theme.js';

const SA_OHIF_CONFIG = {
  /**
   * OHIF Viewer Configuration for South African Healthcare
   */
  routerBasename: '/',
  
  /**
   * Extensions - SA Custom Plugins
   */
  extensions: [
    saCompliancePlugin,
    saMobilePlugin,
    saLanguagePlugin
  ],

  /**
   * Modes - Viewing modes for different use cases
   */
  modes: [
    {
      id: 'sa-general-viewing',
      displayName: 'General Medical Viewing',
      routes: [
        {
          path: 'sa-viewer',
          layoutTemplate: ({ location, servicesManager }) => {
            return {
              id: 'sa-medical-layout',
              props: {
                leftPanels: ['sa-patient-info', 'sa-study-browser'],
                rightPanels: ['sa-measurements', 'sa-annotations'],
                viewports: [
                  {
                    namespace: '@ohif/extension-cornerstone.sopClassHandlerModule.cornerstone',
                    displaySetsToDisplay: ['@ohif/extension-default.sopClassHandlerModule.stack']
                  }
                ]
              }
            };
          }
        }
      ]
    },
    {
      id: 'sa-mobile-viewing',
      displayName: 'Mobile Optimized Viewing',
      routes: [
        {
          path: 'sa-mobile',
          layoutTemplate: ({ location, servicesManager }) => {
            return {
              id: 'sa-mobile-layout',
              props: {
                leftPanels: [], // No left panels on mobile
                rightPanels: [], // No right panels on mobile
                viewports: [
                  {
                    namespace: '@ohif/extension-cornerstone.sopClassHandlerModule.cornerstone',
                    displaySetsToDisplay: ['@ohif/extension-default.sopClassHandlerModule.stack']
                  }
                ]
              }
            };
          }
        }
      ]
    }
  ],

  /**
   * Data Sources - Integration with Orthanc and secure links
   */
  dataSources: [
    {
      namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
      sourceName: 'orthanc',
      configuration: {
        friendlyName: 'SA Orthanc PACS',
        name: 'orthanc',
        wadoUriRoot: '/orthanc/wado',
        qidoRoot: '/orthanc/dicom-web',
        wadoRoot: '/orthanc/dicom-web',
        qidoSupportsIncludeField: false,
        imageRendering: 'wadors',
        thumbnailRendering: 'wadors',
        enableStudyLazyLoad: true,
        supportsFuzzyMatching: false,
        supportsWildcard: true,
        staticWado: true,
        singlepart: 'bulkdata,video',
        // SA-specific optimizations
        requestOptions: {
          headers: {
            'X-SA-Healthcare': 'true',
            'X-HPCSA-Compliant': 'true'
          }
        },
        // Network optimization for SA conditions
        requestInterceptors: [
          {
            // Add authentication tokens
            request: (config) => {
              const token = sessionStorage.getItem('sa-auth-token');
              if (token) {
                config.headers['Authorization'] = `Bearer ${token}`;
              }
              return config;
            }
          },
          {
            // Add HPCSA audit logging
            response: (response) => {
              if (window.saCompliance && response.config.url.includes('studies')) {
                window.saCompliance.hpcsa.userVerification.logUserAccess(
                  { hpcsaNumber: sessionStorage.getItem('hpcsa-number') },
                  { studyInstanceUID: response.config.url.match(/studies\/([^\/]+)/)?.[1] }
                );
              }
              return response;
            }
          }
        ]
      }
    },
    {
      namespace: '@ohif/extension-default.dataSourcesModule.dicomlocal',
      sourceName: 'dicomlocal',
      configuration: {
        friendlyName: 'SA Local Files',
        name: 'dicomlocal'
      }
    }
  ],

  /**
   * Default Data Source
   */
  defaultDataSourceName: 'orthanc',

  /**
   * Hot Keys - Medical imaging shortcuts
   */
  hotkeys: [
    // Basic navigation
    { commandName: 'incrementActiveViewport', label: 'Next Viewport', keys: ['right'] },
    { commandName: 'decrementActiveViewport', label: 'Previous Viewport', keys: ['left'] },
    
    // Tools
    { commandName: 'setToolActive', commandOptions: { toolName: 'Zoom' }, label: 'Zoom', keys: ['z'] },
    { commandName: 'setToolActive', commandOptions: { toolName: 'Wwwc' }, label: 'Window/Level', keys: ['w'] },
    { commandName: 'setToolActive', commandOptions: { toolName: 'Pan' }, label: 'Pan', keys: ['p'] },
    { commandName: 'setToolActive', commandOptions: { toolName: 'Length' }, label: 'Measure', keys: ['m'] },
    { commandName: 'setToolActive', commandOptions: { toolName: 'ArrowAnnotate' }, label: 'Annotate', keys: ['a'] },
    
    // View manipulation
    { commandName: 'resetViewport', label: 'Reset View', keys: ['space'] },
    { commandName: 'rotateViewportCW', label: 'Rotate Right', keys: ['r'] },
    { commandName: 'rotateViewportCCW', label: 'Rotate Left', keys: ['l'] },
    { commandName: 'flipViewportHorizontal', label: 'Flip Horizontal', keys: ['h'] },
    { commandName: 'flipViewportVertical', label: 'Flip Vertical', keys: ['v'] },
    
    // Series navigation
    { commandName: 'previousImageViewportScroll', label: 'Previous Image', keys: ['up'] },
    { commandName: 'nextImageViewportScroll', label: 'Next Image', keys: ['down'] },
    
    // Window presets
    { commandName: 'windowLevelPreset1', label: 'Preset 1', keys: ['1'] },
    { commandName: 'windowLevelPreset2', label: 'Preset 2', keys: ['2'] },
    { commandName: 'windowLevelPreset3', label: 'Preset 3', keys: ['3'] },
    { commandName: 'windowLevelPreset4', label: 'Preset 4', keys: ['4'] },
    { commandName: 'windowLevelPreset5', label: 'Preset 5', keys: ['5'] },
    
    // SA-specific shortcuts
    { commandName: 'toggleHPCSAInfo', label: 'Toggle HPCSA Info', keys: ['ctrl', 'h'] },
    { commandName: 'toggleLanguage', label: 'Toggle Language', keys: ['ctrl', 'l'] },
    { commandName: 'toggleQuality', label: 'Toggle Quality', keys: ['ctrl', 'q'] }
  ],

  /**
   * Cornerstone Configuration - Image rendering settings
   */
  cornerstoneExtensionConfig: {
    tools: {
      // Enable all standard tools
      Zoom: { invert: false },
      Pan: {},
      Wwwc: { orientation: 0 },
      Length: { 
        configuration: {
          shadow: true,
          drawHandles: true,
          drawRuler: true,
          color: '#FFFF00'
        }
      },
      ArrowAnnotate: {
        configuration: {
          arrowFirst: true,
          color: '#FFFF00'
        }
      },
      Bidirectional: {
        configuration: {
          shadow: true,
          color: '#FFFF00'
        }
      },
      EllipticalRoi: {
        configuration: {
          shadow: true,
          color: '#FFFF00'
        }
      },
      CircleRoi: {
        configuration: {
          shadow: true,
          color: '#FFFF00'
        }
      }
    },
    
    // SA-specific rendering optimizations
    rendering: {
      // Progressive loading for mobile networks
      preferSizeOverAccuracy: true,
      useNorm16Texture: false,
      strictZSpacing: true,
      
      // Mobile optimizations
      touchEnabled: true,
      gestureEnabled: true,
      
      // Network optimization
      requestPoolSize: 4, // Limit concurrent requests for SA networks
      maxImagesToPrefetch: 5 // Reduce prefetching for mobile
    }
  },

  /**
   * User Management Integration
   */
  userManagement: {
    enabled: true,
    authenticationService: {
      authenticate: async (credentials) => {
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(credentials),
          credentials: 'include'
        });
        
        if (response.ok) {
          const data = await response.json();
          
          // Store session info
          sessionStorage.setItem('sa-auth-token', data.token);
          sessionStorage.setItem('user-role', data.role);
          sessionStorage.setItem('hpcsa-number', data.hpcsaNumber);
          sessionStorage.setItem('sa-session-id', data.sessionId);
          
          return {
            success: true,
            user: data.user
          };
        }
        
        return { success: false, error: 'Authentication failed' };
      },
      
      getUserInfo: () => {
        const token = sessionStorage.getItem('sa-auth-token');
        const role = sessionStorage.getItem('user-role');
        const hpcsaNumber = sessionStorage.getItem('hpcsa-number');
        
        if (token && role && hpcsaNumber) {
          return {
            authenticated: true,
            role,
            hpcsaNumber,
            permissions: this.getRolePermissions(role)
          };
        }
        
        return { authenticated: false };
      },
      
      logout: async () => {
        await fetch('/api/auth/logout', {
          method: 'POST',
          credentials: 'include'
        });
        
        sessionStorage.clear();
        localStorage.clear();
        window.location.href = '/login';
      }
    },
    
    getRolePermissions: (role) => {
      const permissions = {
        admin: ['view', 'edit', 'delete', 'export', 'share', 'audit'],
        radiologist: ['view', 'edit', 'export', 'share'],
        referring_doctor: ['view', 'share'],
        technician: ['view'],
        viewer: ['view']
      };
      
      return permissions[role] || ['view'];
    }
  },

  /**
   * Secure Link Sharing
   */
  linkSharing: {
    enabled: true,
    
    generateSecureLink: async (studyInstanceUID, options = {}) => {
      try {
        const response = await fetch('/api/secure-links', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            studyInstanceUID,
            expiryHours: options.expiryHours || 24,
            password: options.password,
            allowDownload: options.allowDownload || false,
            accessLevel: options.accessLevel || 'view'
          }),
          credentials: 'include'
        });
        
        const data = await response.json();
        return {
          success: response.ok,
          link: data.link,
          password: data.password,
          expiryDate: data.expiryDate
        };
      } catch (error) {
        return { success: false, error: error.message };
      }
    }
  },

  /**
   * POPIA Compliance Settings
   */
  privacySettings: {
    dataMinimization: true,
    anonymizePatientData: true,
    auditAllAccess: true,
    consentRequired: true,
    
    // Data retention policies
    retentionPeriod: '7 years', // SA medical record requirements
    automaticDeletion: false,
    
    // Access controls
    requireReasonForAccess: true,
    logAllActions: true
  },

  /**
   * Mobile Optimization Settings
   */
  mobileSettings: {
    touchGestures: true,
    adaptiveQuality: true,
    offlineSupport: true,
    
    // Network optimization
    preferredQuality: 'auto', // auto, low, medium, high
    maxImageSize: 2048,
    compressionLevel: 0.8,
    
    // UI adaptations
    hideSidebarsOnMobile: true,
    showMobileToolPanel: true,
    enableFullscreenMode: true
  },

  /**
   * Internationalization Settings
   */
  i18n: {
    defaultLanguage: 'en',
    availableLanguages: ['en', 'af', 'zu'],
    autoDetect: true,
    
    // Date/time formatting for SA
    dateFormat: 'DD/MM/YYYY',
    timeFormat: '24hour',
    timezone: 'Africa/Johannesburg'
  },

  /**
   * Performance Settings for SA Networks
   */
  performance: {
    // Image loading
    imageLoadingConcurrency: 3, // Reduced for mobile networks
    imageCacheSize: 100, // MB
    enableImageCompression: true,
    
    // Prefetching
    prefetchNext: 2,
    prefetchPrevious: 1,
    
    // Rendering
    enableGPURendering: true,
    useWebWorkers: true,
    
    // Network timeouts
    requestTimeout: 30000, // 30 seconds for slow networks
    retryAttempts: 3,
    retryDelay: 2000 // 2 seconds
  },

  /**
   * Development and Debug Settings
   */
  development: {
    enableLogging: true,
    logLevel: 'info', // error, warn, info, debug
    showPerformanceMetrics: false,
    enableHotReload: false
  }
};

// Export configuration
export default SA_OHIF_CONFIG;

// Global registration for use in HTML
window.SA_OHIF_CONFIG = SA_OHIF_CONFIG;
