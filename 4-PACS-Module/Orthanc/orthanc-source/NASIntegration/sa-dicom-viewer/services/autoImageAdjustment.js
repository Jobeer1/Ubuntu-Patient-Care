/**
 * 🇿🇦 Automatic Image Adjustment for OHIF
 * 
 * Intelligent window/level adjustment for DICOM images
 * Uses histogram analysis and modality-specific rules
 * Dramatically improves image quality with no doctor interaction
 * 
 * Location: sa-dicom-viewer/services/autoImageAdjustment.js
 */

import { MODALITY_WINDOW_LEVEL_PRESETS } from '../config/desktop-radiologist-config.js';

/**
 * Main Auto-Adjustment Service
 */
class AutoImageAdjustmentService {
  constructor() {
    this.enabled = true;
    this.method = 'smart';                    // 'histogram', 'standard', 'smart'
    this.cache = new Map();
    this.stats = {
      applicationsCount: 0,
      averageTime: 0,
      successRate: 0
    };
  }

  /**
   * Main entry point - Apply optimal window/level to image
   * 
   * @param {Object} image - CornerstoneJS image object
   * @param {Object} metadata - DICOM metadata
   * @returns {Object} { window, level } settings
   */
  async optimizeImage(image, metadata) {
    if (!this.enabled) return null;

    try {
      const startTime = performance.now();

      // Try to use modality-specific settings first
      const modalityPreset = this.getModalityPreset(metadata);
      if (modalityPreset) {
        return this.applyPreset(image, modalityPreset);
      }

      // Fall back to method-based adjustment
      let result;
      switch (this.method) {
        case 'histogram':
          result = this.histogramBased(image, metadata);
          break;
        case 'standard':
          result = this.standardDICOM(image, metadata);
          break;
        case 'smart':
          result = this.smartAdjustment(image, metadata);
          break;
        default:
          result = this.histogramBased(image, metadata);
      }

      // Record metrics
      const duration = performance.now() - startTime;
      this.recordMetric(duration);

      // Cache result
      if (metadata.SOPInstanceUID) {
        this.cache.set(metadata.SOPInstanceUID, result);
      }

      return result;
    } catch (error) {
      console.error('Auto-adjustment failed:', error);
      return null;
    }
  }

  /**
   * Get modality-specific preset from metadata
   */
  getModalityPreset(metadata) {
    if (!metadata) return null;

    const modality = metadata.Modality || metadata.SeriesDescription?.substring(0, 2);
    const seriesDescription = metadata.SeriesDescription || '';
    const bodyPart = metadata.BodyPartExamined || '';

    // Try exact match
    if (MODALITY_WINDOW_LEVEL_PRESETS[modality]) {
      const presets = MODALITY_WINDOW_LEVEL_PRESETS[modality];
      
      // Look for matching description
      for (const [key, preset] of Object.entries(presets)) {
        if (seriesDescription.includes(key.split(' - ')[0]) ||
            bodyPart.includes(key.split(' - ')[0])) {
          return preset;
        }
      }

      // Return first preset as default for modality
      return Object.values(presets)[0];
    }

    return null;
  }

  /**
   * Histogram-based automatic window/level adjustment
   * 
   * Analyzes pixel intensity distribution to find optimal display parameters
   * Best for general-purpose use
   */
  histogramBased(image, metadata) {
    const pixelData = image.getPixelData();
    const histogram = this.buildHistogram(pixelData);
    
    // Remove outliers (typically noise)
    const lowerPercentile = this.findPercentile(histogram, 2);    // Darkest 2%
    const upperPercentile = this.findPercentile(histogram, 98);   // Brightest 2%

    // Calculate window and level
    const window = upperPercentile - lowerPercentile;
    const level = (upperPercentile + lowerPercentile) / 2;

    // Apply enhancement if image appears poor contrast
    const contrastQuality = this.assessContrastQuality(histogram, window, level);
    if (contrastQuality < 0.5) {
      // Boost window if poor contrast
      return {
        window: window * 1.2,
        level: level,
        enhanced: true,
        quality: contrastQuality
      };
    }

    return { window, level, enhanced: false, quality: contrastQuality };
  }

  /**
   * Standard DICOM auto-adjustment
   * 
   * Uses min/max with optional gamma correction
   * More conservative, preserves original data range
   */
  standardDICOM(image, metadata) {
    const pixelData = image.getPixelData();
    const stats = this.calculatePixelStats(pixelData);

    const window = stats.max - stats.min;
    const level = (stats.max + stats.min) / 2;

    // Optional gamma correction for better perception
    let result = { window, level };
    
    if (window > 0) {
      // Apply subtle gamma correction for better visualization
      const gamma = 1.0 / 2.2;  // Standard display gamma
      result.gamma = gamma;
    }

    return result;
  }

  /**
   * Smart adjustment combining multiple techniques
   * 
   * Uses modality detection + histogram analysis + contrast assessment
   * Best quality, requires slightly more processing
   */
  smartAdjustment(image, metadata) {
    const histogram = this.buildHistogram(image.getPixelData());
    const modality = metadata.Modality;

    // Step 1: Base histogram adjustment
    const histResult = this.histogramBased(image, metadata);

    // Step 2: Modality-specific refinement
    let refinedWindow = histResult.window;
    let refinedLevel = histResult.level;

    // Apply modality-specific multipliers
    const modalityFactors = {
      'CT': 1.0,      // No adjustment needed
      'MR': 1.1,      // Slightly boost window
      'CR': 0.95,     // Slight reduction for radiography
      'DX': 0.95,
      'US': 1.2,      // Boost for ultrasound
      'PT': 1.3       // Boost for nuclear
    };

    const factor = modalityFactors[modality] || 1.0;
    refinedWindow = histResult.window * factor;

    // Step 3: Automatic contrast enhancement if needed
    const contrastQuality = this.assessContrastQuality(histogram, refinedWindow, refinedLevel);
    
    let enhancement = 1.0;
    if (contrastQuality < 0.4) {
      enhancement = 1.3;  // Aggressive boost
    } else if (contrastQuality < 0.6) {
      enhancement = 1.15; // Moderate boost
    }

    return {
      window: refinedWindow * enhancement,
      level: refinedLevel,
      confidence: Math.min(contrastQuality + (1 - contrastQuality) * enhancement, 1.0),
      method: 'smart',
      modality,
      enhanced: enhancement > 1.0
    };
  }

  /**
   * Build histogram from pixel data
   * Groups pixels by intensity value
   */
  buildHistogram(pixelData) {
    const histogram = new Map();
    
    // Sample data for performance (if very large)
    const sampleRate = pixelData.length > 1000000 ? 10 : 1;
    
    for (let i = 0; i < pixelData.length; i += sampleRate) {
      const value = Math.round(pixelData[i]);
      histogram.set(value, (histogram.get(value) || 0) + 1);
    }
    
    return histogram;
  }

  /**
   * Calculate pixel statistics
   */
  calculatePixelStats(pixelData) {
    let min = pixelData[0];
    let max = pixelData[0];
    let sum = 0;
    let count = 0;

    for (let i = 0; i < pixelData.length; i++) {
      const value = pixelData[i];
      if (value < min) min = value;
      if (value > max) max = value;
      sum += value;
      count++;
    }

    return {
      min,
      max,
      mean: sum / count,
      range: max - min
    };
  }

  /**
   * Find percentile in histogram
   */
  findPercentile(histogram, percentile) {
    const total = Array.from(histogram.values()).reduce((a, b) => a + b, 0);
    const target = (total * percentile) / 100;
    
    let cumulative = 0;
    const sortedEntries = Array.from(histogram.entries()).sort((a, b) => a[0] - b[0]);
    
    for (const [value, count] of sortedEntries) {
      cumulative += count;
      if (cumulative >= target) {
        return value;
      }
    }
    
    return Array.from(histogram.keys()).pop();
  }

  /**
   * Assess contrast quality of image (0-1 scale)
   * 
   * 0 = poor contrast (all pixels similar)
   * 1 = excellent contrast (good range)
   */
  assessContrastQuality(histogram, window, level) {
    if (window === 0) return 0;

    // Count pixels in window range
    const rangeStart = level - (window / 2);
    const rangeEnd = level + (window / 2);
    
    let pixelsInRange = 0;
    let totalPixels = 0;

    for (const [value, count] of histogram.entries()) {
      totalPixels += count;
      if (value >= rangeStart && value <= rangeEnd) {
        pixelsInRange += count;
      }
    }

    // Ideal distribution: 80-95% of pixels in display range
    const distribution = pixelsInRange / totalPixels;
    
    if (distribution >= 0.8 && distribution <= 0.95) {
      return 1.0;  // Perfect
    } else if (distribution >= 0.7 && distribution <= 0.98) {
      return 0.85; // Good
    } else if (distribution >= 0.6 && distribution <= 0.99) {
      return 0.7;  // Acceptable
    } else {
      return 0.4;  // Poor
    }
  }

  /**
   * Apply preset to image
   */
  applyPreset(image, preset) {
    if (preset.auto) {
      // Auto-adjust with contrast modification
      const baseResult = this.histogramBased(image, {});
      return {
        ...baseResult,
        contrastEnhancement: preset.contrast || 1.0,
        brightnessAdjustment: preset.brightness || 0,
        method: 'preset'
      };
    } else if (preset.window && preset.level) {
      // Fixed preset
      return {
        window: preset.window,
        level: preset.level,
        method: 'preset'
      };
    }

    return null;
  }

  /**
   * Record performance metrics
   */
  recordMetric(duration) {
    this.stats.applicationsCount++;
    const oldAvg = this.stats.averageTime;
    this.stats.averageTime =
      (oldAvg * (this.stats.applicationsCount - 1) + duration) /
      this.stats.applicationsCount;
  }

  /**
   * Get statistics
   */
  getStats() {
    return {
      ...this.stats,
      cacheSize: this.cache.size
    };
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.cache.clear();
  }

  /**
   * Set adjustment method
   */
  setMethod(method) {
    if (['histogram', 'standard', 'smart'].includes(method)) {
      this.method = method;
    }
  }

  /**
   * Enable/disable auto-adjustment
   */
  setEnabled(enabled) {
    this.enabled = enabled;
  }
}

/**
 * Singleton instance
 */
let instance = null;

export function getAutoAdjustmentService() {
  if (!instance) {
    instance = new AutoImageAdjustmentService();
  }
  return instance;
}

/**
 * Integration hook for OHIF
 * 
 * Usage in OHIF initialization:
 * 
 * import { getAutoAdjustmentService } from './services/autoImageAdjustment.js';
 * 
 * // In viewport rendering hook:
 * const adjService = getAutoAdjustmentService();
 * const result = await adjService.optimizeImage(image, metadata);
 * 
 * if (result) {
 *   viewport.setWindowLevel(result.window, result.level);
 * }
 */

export class OHIFAutoAdjustmentPlugin {
  static id = '@sa-medical/auto-adjustment-plugin';
  
  static init(servicesManager, commandsManager, extensionManager) {
    const adjService = getAutoAdjustmentService();
    
    // Register command for manual trigger
    commandsManager.registerCommand('autoAdjustImage', 'Auto-adjust image display', ({
      viewportId,
      metadata
    }) => {
      const cornerstoneViewportService = servicesManager.services.cornerstoneViewportService;
      const viewport = cornerstoneViewportService.getCornerstoneViewport(viewportId);
      
      if (viewport) {
        adjService.optimizeImage(viewport.image, metadata).then(result => {
          if (result) {
            viewport.setWindowLevel(result.window, result.level);
          }
        });
      }
    });
    
    // Auto-apply when new image loaded
    cornerstoneViewportService.subscribe('VIEWPORT_NEW_IMAGE', async (evt) => {
      const result = await adjService.optimizeImage(
        evt.image,
        evt.metadata
      );
      
      if (result) {
        evt.viewport.setWindowLevel(result.window, result.level);
      }
    });
  }
}

export default getAutoAdjustmentService();
