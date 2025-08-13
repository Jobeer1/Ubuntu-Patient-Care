/**
 * 🇿🇦 South African DICOM Viewer Configuration
 * 
 * OHIF configuration optimized for South African healthcare environment
 * Includes network optimizations, mobile support, and compliance features
 */

const SA_OHIF_CONFIG = {
  // Basic OHIF configuration
  routerBasename: '/sa-viewer',
  disableServersCache: false,
  
  // SA-specific branding
  branding: {
    name: '🇿🇦 SA Medical Imaging Viewer',
    logo: '/assets/sa-logo.png',
    favicon: '/assets/sa-favicon.ico',
    primaryColor: '#0F7B0F', // SA Green
    accentColor: '#FFD700',  // SA Gold
  },

  // Multi-language support for SA
  i18n: {
    defaultLanguage: 'en',
    supportedLanguages: [
      { code: 'en', name: 'English' },
      { code: 'af', name: 'Afrikaans' },
      { code: 'zu', name: 'isiZulu' },
      { code: 'xh', name: 'isiXhosa' }
    ]
  },

  // Network optimizations for SA connectivity
  networkOptimization: {
    // Optimize for 3G/4G networks
    enableCompression: true,
    enableCaching: true,
    prefetchStrategy: 'adaptive', // Adjust based on connection speed
    maxConcurrentRequests: 2, // Limit for slower connections
    timeout: 30000, // 30 second timeout for SA networks
    
    // Progressive loading for poor connections
    progressiveLoading: {
      enabled: true,
      lowQualityFirst: true,
      adaptiveQuality: true
    }
  },

  // Mobile optimizations for SA market
  mobile: {
    enableTouchGestures: true,
    enablePinchZoom: true,
    optimizeForMobile: true,
    adaptiveUI: true,
    
    // SA-specific mobile optimizations
    dataUsageOptimization: true,
    offlineMode: true,
    reducedMotion: true // For older devices
  },

  // SA Healthcare compliance
  compliance: {
    hpcsa: {
      enabled: true,
      auditLogging: true,
      userVerification: true,
      sessionTracking: true
    },
    popia: {
      enabled: true,
      dataMinimization: true,
      consentManagement: true,
      anonymization: true
    }
  },

  // DICOM servers configuration
  servers: {
    dicomweb: [
      {
        name: 'SA Orthanc Primary',
        wadoUriRoot: '/orthanc/wado',
        qidoRoot: '/orthanc/dicom-web',
        wadoRoot: '/orthanc/dicom-web',
        qidoSupportsIncludeField: true,
        imageRendering: 'wadors',
        thumbnailRendering: 'wadors',
        
        // SA-specific server settings
        enableStudyLazyLoad: true,
        supportsFuzzyMatching: true,
        supportsWildcard: true
      }
    ]
  },

  // Viewport and display settings optimized for SA
  viewport: {
    // Default tools for SA healthcare workflow
    defaultTools: [
      'Zoom',
      'WindowLevel',
      'Pan',
      'Length',
      'Angle',
      'Rectangle',
      'Ellipse',
      'FreehandMouse',
      'Eraser'
    ],
    
    // SA-specific viewport settings
    enableAnnotations: true,
    enableMeasurements: true,
    enableCrossHairs: true,
    enableReferenceLines: true,
    
    // Optimized for SA display conditions
    windowLevelPresets: [
      { name: 'Soft Tissue', window: 400, level: 50 },
      { name: 'Lung', window: 1500, level: -600 },
      { name: 'Bone', window: 1800, level: 400 },
      { name: 'Brain', window: 100, level: 50 },
      { name: 'Abdomen', window: 350, level: 50 }
    ]
  },

  // Security settings for SA healthcare
  security: {
    enableCSP: true,
    enableCORS: true,
    sessionTimeout: 1800000, // 30 minutes
    maxSessions: 1, // Single session enforcement
    
    // SA healthcare specific security
    requireSecureConnection: true,
    enableAuditLog: true,
    enableUserTracking: true
  },

  // Extensions and plugins
  extensions: [
    '@ohif/extension-default',
    '@ohif/extension-cornerstone',
    '@ohif/extension-measurement-tracking',
    '@ohif/extension-cornerstone-dicom-sr',
    '@ohif/extension-dicom-pdf',
    
    // SA-specific extensions
    '@sa-medical/extension-hpcsa-compliance',
    '@sa-medical/extension-popia-compliance',
    '@sa-medical/extension-multilingual',
    '@sa-medical/extension-mobile-optimized',
    '@sa-medical/extension-referring-doctor-workflow'
  ],

  // SA Healthcare workflow modes
  modes: [
    '@ohif/mode-longitudinal',
    '@ohif/mode-segmentation',
    '@sa-medical/mode-referring-doctor',
    '@sa-medical/mode-mobile-viewing',
    '@sa-medical/mode-offline-sync'
  ],

  // Hotkeys optimized for SA workflow
  hotkeys: [
    { commandName: 'incrementActiveViewport', label: 'Next Viewport', keys: ['right'] },
    { commandName: 'decrementActiveViewport', label: 'Previous Viewport', keys: ['left'] },
    { commandName: 'rotateViewportCW', label: 'Rotate Right', keys: ['r'] },
    { commandName: 'rotateViewportCCW', label: 'Rotate Left', keys: ['l'] },
    { commandName: 'invertViewport', label: 'Invert', keys: ['i'] },
    { commandName: 'flipViewportVertical', label: 'Flip Vertical', keys: ['v'] },
    { commandName: 'flipViewportHorizontal', label: 'Flip Horizontal', keys: ['h'] },
    { commandName: 'scaleUpViewport', label: 'Zoom In', keys: ['+'] },
    { commandName: 'scaleDownViewport', label: 'Zoom Out', keys: ['-'] },
    { commandName: 'fitViewportToWindow', label: 'Zoom to Fit', keys: ['='] },
    { commandName: 'resetViewport', label: 'Reset', keys: ['space'] }
  ],

  // Performance settings for SA infrastructure
  performance: {
    // Memory management for resource-constrained environments
    maxMemoryUsage: '512MB',
    imageCache: {
      maxCacheSize: '256MB',
      timeToLive: 300000 // 5 minutes
    },
    
    // Rendering optimizations
    renderingEngine: 'cornerstone3D',
    useWebWorkers: true,
    maxWebWorkers: 2, // Conservative for older devices
    
    // Progressive enhancement
    enableProgressive: true,
    lowMemoryMode: false, // Can be enabled for older devices
    reducedAnimations: false
  }
};

export default SA_OHIF_CONFIG;
