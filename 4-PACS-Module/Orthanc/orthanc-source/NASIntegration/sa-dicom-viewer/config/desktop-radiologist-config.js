/**
 * 🇿🇦 Desktop Radiologist Configuration for OHIF
 * 
 * Optimized image display settings for reporting stations
 * Prioritizes diagnostic accuracy and radiologist workflows
 * 
 * Use: Import and merge with base sa-ohif-integration.js for desktop environments
 */

export const DESKTOP_RADIOLOGIST_CONFIG = {
  /**
   * Cornerstone Rendering - Medical Imaging Focused
   * Critical for diagnostic quality
   */
  cornerstoneExtensionConfig: {
    rendering: {
      // === ACCURACY OVER SPEED ===
      preferSizeOverAccuracy: false,          // ✓ Diagnostic quality (NOT mobile)
      useNorm16Texture: true,                 // ✓ 16-bit texture precision
      strictZSpacing: true,                   // ✓ Maintain spacing accuracy
      
      // === PERFORMANCE FOR WORKFLOWS ===
      requestPoolSize: 16,                    // ✓ Parallel requests (from 4)
      maxImagesToPrefetch: 20,                // ✓ Smooth series browsing (from 5)
      requestTimeout: 60000,                  // ✓ 60 second timeout for large files
      
      // === MOBILE OPTIMIZATION DISABLED ===
      touchEnabled: true,                     // Keep for occasional touch inputs
      gestureEnabled: false,                  // Disable pinch/pan gestures
      
      // === NEW: GPU ACCELERATION ===
      enableClientSideRendering: true,        // Use GPU if available
      enableWebGL2: true,                     // Modern rendering
      enableImageProcessing: true,            // CPU/GPU image enhancement
      
      // === NEW: PROGRESSIVE ENHANCEMENT ===
      enableProgressiveLoading: false,        // Load full quality (no low-res first)
      enableStreamingGeometry: false,         // Wait for complete data
      
      // === ADVANCED FEATURES ===
      enableImageComparison: true,            // Side-by-side viewing
      enableMeasurementAnnotations: true,     // Measurement tools
      enableVideoPlayback: true               // For multi-frame images
    },

    /**
     * Window/Level Tools - Better Control
     */
    tools: {
      Zoom: {
        invert: false,
        configuration: {
          minScale: 0.1,                      // Allow very zoomed out
          maxScale: 10,                       // Allow very zoomed in
          currentScale: 1
        }
      },
      
      Pan: {
        configuration: {
          enabled: true
        }
      },
      
      Wwwc: {
        orientation: 0,
        configuration: {
          enabled: true,
          sensitivity: 100,                   // Higher = more responsive
          displayStats: true                  // NEW: Show W/L numbers
        }
      },
      
      Length: {
        configuration: {
          shadow: true,
          drawHandles: true,
          drawRuler: true,
          color: '#00FF00',                   // Green for measurements
          lineWidth: 2,
          fontSize: 12
        }
      },
      
      ArrowAnnotate: {
        configuration: {
          arrowFirst: true,
          color: '#FFFF00',                   // Yellow annotations
          lineWidth: 2,
          fontSize: 12
        }
      },
      
      Bidirectional: {
        configuration: {
          shadow: true,
          color: '#00FF00',
          lineWidth: 2
        }
      },
      
      EllipticalRoi: {
        configuration: {
          shadow: true,
          color: '#00FFFF',                   // Cyan for ROI
          lineWidth: 2
        }
      },
      
      CircleRoi: {
        configuration: {
          shadow: true,
          color: '#00FFFF',
          lineWidth: 2
        }
      },
      
      // NEW: Enhance/Optimize Tools
      ImageEnhancer: {
        configuration: {
          enabled: true,
          brightness: 0,                      // Range: -100 to +100
          contrast: 0,                        // Range: -100 to +100
          sharpness: 0,                       // Range: -100 to +100
          gamma: 1.0                          // Range: 0.5 to 2.0
        }
      }
    },

    /**
     * Maximum Resolution Settings
     */
    maxResolution: {
      viewport: 4096,                         // Full 4K resolution
      compression: 'lossless',                // No JPEG artifacts
      colorDepth: 16,                         // 16-bit greyscale for medical
      enableHighDPI: true                     // Support 2x/3x displays
    },

    /**
     * Caching Strategy
     */
    cache: {
      enableImageCache: true,
      enableMetadataCache: true,
      cacheSizeInMB: 512,                     // Allow larger cache
      compressionInCache: false               // No compression in RAM
    }
  },

  /**
   * Image Display Defaults
   */
  imageDisplay: {
    enableAutoAdjustment: true,               // NEW: Auto window/level
    autoAdjustmentMethod: 'histogram',        // Histogram-based (also 'standard')
    enableBrightnessNormalization: true,      // Normalize across series
    enableContrastEnhancement: true,          // Subtle enhancement
    defaultInterpolation: 'bicubic'           // Smoother rendering
  },

  /**
   * Performance Optimization
   */
  performance: {
    enableVirtualScrolling: false,            // Load all in viewport
    enableLazyLoading: false,                 // No lazy loading
    preloadSeriesCount: 3,                    // Load adjacent series
    renderTimeout: 30000,                     // 30 second render timeout
    enableGPUAcceleration: true
  },

  /**
   * UI Enhancements for Radiologists
   */
  ui: {
    showImageStatistics: true,                // NEW: Display min/max/mean
    showWindowLevelValues: true,              // Display W/L numbers
    showImageQualityIndicator: true,          // Quality badge
    showPerformanceMetrics: true,             // Load time, frame rate
    showMeasurementAnnotations: true,
    compactToolbar: false,                    // Full toolbar
    enableQuickPresets: true,                 // Quick access presets
    layoutMode: 'desktop'                     // Desktop-optimized layout
  }
};

/**
 * Modality-Specific Window/Level Presets
 * 
 * These are the optimal settings for different imaging types
 * Format: { window: W, level: L } or { auto: true, contrast: enhancement }
 * 
 * Radiologists can quickly switch between presets with keyboard shortcuts
 */
export const MODALITY_WINDOW_LEVEL_PRESETS = {
  /**
   * RADIOGRAPHY (X-Ray, CR, DX)
   */
  'CR': {
    'Chest - Standard': { window: 350, level: 40 },
    'Chest - Lung': { window: 1500, level: -600 },
    'Chest - Mediastinum': { window: 350, level: 40 },
    'Abdomen': { window: 400, level: 40 },
    'Spine - Cervical': { window: 300, level: 50 },
    'Spine - Thoracic': { window: 300, level: 50 },
    'Spine - Lumbar': { window: 300, level: 50 },
    'Pelvis': { window: 400, level: 40 },
    'Extremity': { window: 300, level: 50 }
  },

  'DX': {
    'Chest - Standard': { window: 350, level: 40 },
    'Chest - Lung': { window: 1500, level: -600 },
    'Abdomen': { window: 400, level: 40 }
  },

  /**
   * CT (Computed Tomography)
   */
  'CT': {
    'Brain - Gray Matter': { window: 80, level: 40 },
    'Brain - White Matter': { window: 80, level: 20 },
    'Brain - Bone': { window: 400, level: 40 },
    'Brain - Subdural': { window: 130, level: 50 },
    'Chest - Soft Tissue': { window: 350, level: 40 },
    'Chest - Lung': { window: 1500, level: -600 },
    'Chest - Bone': { window: 400, level: 40 },
    'Abdomen - Soft Tissue': { window: 400, level: 40 },
    'Abdomen - Liver': { window: 150, level: 30 },
    'Abdomen - Pancreas': { window: 150, level: 30 },
    'Abdomen - Bone': { window: 400, level: 40 },
    'Pelvis - Soft Tissue': { window: 400, level: 40 },
    'Spine - Bone': { window: 600, level: 100 },
    'Spine - Soft Tissue': { window: 100, level: 30 },
    'Extremity - Bone': { window: 400, level: 40 }
  },

  /**
   * MRI (Magnetic Resonance Imaging)
   * MRI doesn't have standard window/level - use auto with contrast
   */
  'MR': {
    'Brain T1': { auto: true, contrast: 1.0, brightness: 0 },
    'Brain T2': { auto: true, contrast: 1.2, brightness: 0 },
    'Brain FLAIR': { auto: true, contrast: 1.1, brightness: 0 },
    'Spine T1': { auto: true, contrast: 1.1, brightness: 0 },
    'Spine T2': { auto: true, contrast: 1.2, brightness: 0 },
    'Cardiac': { auto: true, contrast: 1.0, brightness: 0 },
    'Abdomen': { auto: true, contrast: 1.1, brightness: 0 }
  },

  /**
   * ULTRASOUND (US/Doppler)
   */
  'US': {
    'General': { auto: true, contrast: 0.9, brightness: -5 },
    'OB/GYN': { auto: true, contrast: 1.0, brightness: 0 },
    'Cardiac': { auto: true, contrast: 1.1, brightness: 0 },
    'Vascular': { auto: true, contrast: 1.1, brightness: 0 }
  },

  /**
   * NUCLEAR MEDICINE
   */
  'NM': {
    'Default': { auto: true, contrast: 1.3, brightness: 0 }
  },

  /**
   * PET (Positron Emission Tomography)
   */
  'PT': {
    'Default': { auto: true, contrast: 1.2, brightness: 0 }
  }
};

/**
 * Automatic Window/Level Adjustment Algorithm
 * 
 * Uses histogram analysis to determine optimal display parameters
 */
export const AUTO_ADJUSTMENT_CONFIG = {
  method: 'histogram',                        // 'histogram', 'standard', 'smart'
  
  /**
   * Histogram-based automatic adjustment
   * Analyzes pixel intensity distribution
   */
  histogram: {
    enablePercentileBased: true,              // Use percentiles
    lowerPercentile: 2,                       // Ignore darkest 2%
    upperPercentile: 98,                      // Ignore brightest 2%
    windowWidth: 'auto',                      // Computed from histogram
    levelPosition: 'center'                   // Center of data range
  },
  
  /**
   * Standard DICOM auto-adjust
   * Uses min/max pixel values
   */
  standard: {
    enableFullRange: true,
    enableGammaCorrection: true,
    gammaValue: 1.0
  },
  
  /**
   * Smart adjustment using modality detection
   * Combines histogram analysis with modality-specific rules
   */
  smart: {
    detectModality: true,                     // Auto-detect from DICOM tags
    useModalityDefaults: true,                // Use presets as baseline
    refineWithHistogram: true,                // Fine-tune with actual data
    enableAdaptiveContrast: true              // Boost contrast if needed
  }
};

/**
 * Keyboard Shortcuts for Radiologists
 * 
 * Quick access to common functions
 */
export const RADIOLOGIST_HOTKEYS = [
  // Window/Level Presets by Number (1-9)
  { keys: ['1'], action: 'applyPreset', preset: 0, label: 'Preset 1' },
  { keys: ['2'], action: 'applyPreset', preset: 1, label: 'Preset 2' },
  { keys: ['3'], action: 'applyPreset', preset: 2, label: 'Preset 3' },
  { keys: ['4'], action: 'applyPreset', preset: 3, label: 'Preset 4' },
  { keys: ['5'], action: 'applyPreset', preset: 4, label: 'Preset 5' },
  { keys: ['6'], action: 'applyPreset', preset: 5, label: 'Preset 6' },
  { keys: ['7'], action: 'applyPreset', preset: 6, label: 'Preset 7' },
  { keys: ['8'], action: 'applyPreset', preset: 7, label: 'Preset 8' },
  { keys: ['9'], action: 'applyPreset', preset: 8, label: 'Preset 9' },

  // Image Adjustment (Ctrl + arrows)
  { keys: ['ctrl', 'up'], action: 'increaseBrightness', delta: 10, label: 'Brightness +' },
  { keys: ['ctrl', 'down'], action: 'decreaseBrightness', delta: -10, label: 'Brightness -' },
  { keys: ['ctrl', 'right'], action: 'increaseContrast', delta: 10, label: 'Contrast +' },
  { keys: ['ctrl', 'left'], action: 'decreaseContrast', delta: -10, label: 'Contrast -' },

  // Series Navigation (Quick)
  { keys: ['left'], action: 'previousImage', label: 'Previous Image' },
  { keys: ['right'], action: 'nextImage', label: 'Next Image' },
  { keys: ['up'], action: 'previousSeries', label: 'Previous Series' },
  { keys: ['down'], action: 'nextSeries', label: 'Next Series' },

  // Tools (Alt + key)
  { keys: ['alt', 'z'], action: 'setTool', tool: 'Zoom', label: 'Zoom Tool' },
  { keys: ['alt', 'w'], action: 'setTool', tool: 'Wwwc', label: 'Window/Level' },
  { keys: ['alt', 'p'], action: 'setTool', tool: 'Pan', label: 'Pan Tool' },
  { keys: ['alt', 'm'], action: 'setTool', tool: 'Length', label: 'Measure' },
  { keys: ['alt', 'a'], action: 'setTool', tool: 'ArrowAnnotate', label: 'Annotate' },

  // Display
  { keys: ['f'], action: 'toggleFullscreen', label: 'Fullscreen' },
  { keys: ['r'], action: 'resetView', label: 'Reset View' },
  { keys: ['h'], action: 'toggleHistogram', label: 'Show Histogram' },
  { keys: ['i'], action: 'toggleImageStats', label: 'Image Statistics' },

  // Comparison
  { keys: ['c'], action: 'toggleComparison', label: 'Comparison Mode' },
  { keys: ['d'], action: 'toggleDifference', label: 'Difference View' }
];

/**
 * Image Quality Profile
 * Used to maintain consistent quality across display
 */
export const IMAGE_QUALITY_PROFILE = {
  name: 'Diagnostic Radiology',
  description: 'Optimized for diagnostic-grade medical imaging',
  
  // Display quality
  targetResolution: 4096,                     // Full 4K
  colorDepth: 16,                             // 16-bit greyscale
  dithering: false,                           // No dithering
  gammaCorrection: true,
  gammaValue: 2.2,                            // Standard gamma
  
  // Processing
  enableNoiseReduction: false,                // Don't modify raw data
  enableSharpening: true,                     // Subtle enhancement
  sharpnessAmount: 0.3,                       // Mild (0.0-1.0)
  enableColorCorrection: false,               // Grayscale only
  
  // Compression
  compression: 'lossless',                    // No loss of data
  jpegQuality: 100,                           // If JPEG necessary
  
  // Metadata
  preserveDICOMMetadata: true,                // Keep all tags
  displayDICOMTags: true,                     // Show info panel
  enableAuditLogging: true                    // HPCSA compliance
};

export default DESKTOP_RADIOLOGIST_CONFIG;
