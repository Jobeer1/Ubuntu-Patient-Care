/**
 * 🇿🇦 Enhanced Image Display Controls for OHIF
 * 
 * Doctor-friendly image adjustment UI component
 * Provides quick access to window/level presets, adjustment tools, and image stats
 * 
 * Location: sa-dicom-viewer/components/EnhancedImageControls.jsx
 */

import React, { useState, useEffect, useCallback } from 'react';
import { MODALITY_WINDOW_LEVEL_PRESETS } from '../config/desktop-radiologist-config.js';
import { getAutoAdjustmentService } from '../services/autoImageAdjustment.js';

/**
 * Image Control Panel Component
 */
export function EnhancedImageControlPanel({
  viewportId,
  metadata,
  cornerstoneViewportService,
  commandsManager
}) {
  const [windowLevel, setWindowLevel] = useState({ window: 400, level: 40 });
  const [imageStats, setImageStats] = useState(null);
  const [showStats, setShowStats] = useState(false);
  const [brightness, setBrightness] = useState(0);
  const [contrast, setContrast] = useState(100);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [modality, setModality] = useState(null);
  const [presets, setPresets] = useState([]);
  const [autoOptimizing, setAutoOptimizing] = useState(false);

  // Determine modality and available presets
  useEffect(() => {
    if (metadata) {
      const mod = metadata.Modality || 'CT';
      setModality(mod);
      
      if (MODALITY_WINDOW_LEVEL_PRESETS[mod]) {
        setPresets(Object.entries(MODALITY_WINDOW_LEVEL_PRESETS[mod]));
      }
    }
  }, [metadata]);

  /**
   * Apply window/level adjustment
   */
  const applyWindowLevel = useCallback((window, level) => {
    setWindowLevel({ window, level });
    const viewport = cornerstoneViewportService.getCornerstoneViewport(viewportId);
    if (viewport) {
      viewport.setWindowLevel(level, window);
    }
  }, [viewportId, cornerstoneViewportService]);

  /**
   * Apply preset
   */
  const applyPreset = useCallback((presetName) => {
    if (!modality || !MODALITY_WINDOW_LEVEL_PRESETS[modality]) return;
    
    const preset = MODALITY_WINDOW_LEVEL_PRESETS[modality][presetName];
    if (preset) {
      if (preset.auto) {
        // Trigger auto-adjustment
        triggerAutoAdjustment();
      } else {
        applyWindowLevel(preset.window, preset.level);
      }
      setSelectedPreset(presetName);
    }
  }, [modality, applyWindowLevel]);

  /**
   * Trigger automatic image adjustment
   */
  const triggerAutoAdjustment = useCallback(async () => {
    setAutoOptimizing(true);
    try {
      const viewport = cornerstoneViewportService.getCornerstoneViewport(viewportId);
      if (viewport && viewport.image) {
        const adjService = getAutoAdjustmentService();
        const result = await adjService.optimizeImage(viewport.image, metadata);
        
        if (result) {
          applyWindowLevel(result.window, result.level);
        }
      }
    } finally {
      setAutoOptimizing(false);
    }
  }, [viewportId, cornerstoneViewportService, metadata, applyWindowLevel]);

  /**
   * Update brightness
   */
  const handleBrightnessChange = useCallback((value) => {
    setBrightness(value);
    applyWindowLevel(
      windowLevel.window,
      windowLevel.level + value
    );
  }, [windowLevel, applyWindowLevel]);

  /**
   * Update contrast
   */
  const handleContrastChange = useCallback((value) => {
    setContrast(value);
    const factor = value / 100;
    applyWindowLevel(
      windowLevel.window * factor,
      windowLevel.level
    );
  }, [windowLevel, applyWindowLevel]);

  /**
   * Calculate image statistics
   */
  const calculateStats = useCallback(() => {
    const viewport = cornerstoneViewportService.getCornerstoneViewport(viewportId);
    if (viewport && viewport.image) {
      const pixelData = viewport.image.getPixelData();
      let min = pixelData[0];
      let max = pixelData[0];
      let sum = 0;

      for (let i = 0; i < pixelData.length; i++) {
        const val = pixelData[i];
        if (val < min) min = val;
        if (val > max) max = val;
        sum += val;
      }

      setImageStats({
        min: Math.round(min),
        max: Math.round(max),
        mean: Math.round(sum / pixelData.length),
        range: Math.round(max - min)
      });
    }
  }, [viewportId, cornerstoneViewportService]);

  /**
   * Toggle stats display
   */
  const toggleStats = useCallback(() => {
    if (!showStats) {
      calculateStats();
    }
    setShowStats(!showStats);
  }, [showStats, calculateStats]);

  return (
    <div className="enhanced-image-controls">
      {/* Header */}
      <div className="controls-header">
        <h3>Image Display Controls</h3>
        <div className="quality-indicator">
          <span className="quality-badge">🎬 Diagnostic Quality</span>
        </div>
      </div>

      {/* Quick Presets */}
      <div className="presets-section">
        <h4>Quick Presets</h4>
        <div className="preset-buttons">
          {presets.length > 0 ? (
            presets.slice(0, 6).map(([name, preset]) => (
              <button
                key={name}
                className={`preset-btn ${selectedPreset === name ? 'active' : ''}`}
                onClick={() => applyPreset(name)}
                title={`Apply preset: ${name}`}
              >
                {name.split(' - ')[0]}
              </button>
            ))
          ) : (
            <p className="text-muted">No presets for this modality</p>
          )}
          <button
            className={`preset-btn auto-btn ${autoOptimizing ? 'loading' : ''}`}
            onClick={triggerAutoAdjustment}
            disabled={autoOptimizing}
            title="Automatically optimize image display"
          >
            {autoOptimizing ? '🔄 Optimizing...' : '⚡ Auto'}
          </button>
        </div>
      </div>

      {/* Window/Level Display */}
      <div className="window-level-display">
        <div className="value-pair">
          <div className="value-item">
            <label>Window</label>
            <span className="value">{windowLevel.window.toFixed(0)}</span>
          </div>
          <div className="value-item">
            <label>Level</label>
            <span className="value">{windowLevel.level.toFixed(0)}</span>
          </div>
        </div>
      </div>

      {/* Sliders */}
      <div className="adjustment-sliders">
        {/* Brightness */}
        <div className="slider-group">
          <label htmlFor="brightness-slider">
            ☀️ Brightness
            <span className="slider-value">{brightness > 0 ? '+' : ''}{brightness}</span>
          </label>
          <input
            id="brightness-slider"
            type="range"
            min="-100"
            max="100"
            step="5"
            value={brightness}
            onChange={(e) => handleBrightnessChange(parseInt(e.target.value))}
            className="slider"
          />
        </div>

        {/* Contrast */}
        <div className="slider-group">
          <label htmlFor="contrast-slider">
            🎚️ Contrast
            <span className="slider-value">{contrast}%</span>
          </label>
          <input
            id="contrast-slider"
            type="range"
            min="50"
            max="150"
            step="5"
            value={contrast}
            onChange={(e) => handleContrastChange(parseInt(e.target.value))}
            className="slider"
          />
        </div>
      </div>

      {/* Image Statistics */}
      <div className="statistics-section">
        <button
          className="stats-toggle-btn"
          onClick={toggleStats}
          title="Show/hide image statistics"
        >
          {showStats ? '▼' : '▶'} Image Statistics
        </button>
        
        {showStats && imageStats && (
          <div className="stats-display">
            <div className="stat-item">
              <span className="stat-label">Min:</span>
              <span className="stat-value">{imageStats.min}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Max:</span>
              <span className="stat-value">{imageStats.max}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Mean:</span>
              <span className="stat-value">{imageStats.mean}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Range:</span>
              <span className="stat-value">{imageStats.range}</span>
            </div>
          </div>
        )}
      </div>

      {/* Reset Button */}
      <button
        className="reset-btn"
        onClick={() => {
          applyWindowLevel(400, 40);
          setBrightness(0);
          setContrast(100);
          setSelectedPreset(null);
        }}
        title="Reset to default settings"
      >
        ↻ Reset
      </button>
    </div>
  );
}

/**
 * Quick Preset Toolbar
 * Compact version for toolbar integration
 */
export function QuickPresetToolbar({
  viewportId,
  metadata,
  cornerstoneViewportService
}) {
  const [modality, setModality] = useState(null);
  const [presets, setPresets] = useState([]);

  useEffect(() => {
    if (metadata) {
      const mod = metadata.Modality || 'CT';
      setModality(mod);
      
      if (MODALITY_WINDOW_LEVEL_PRESETS[mod]) {
        const presetList = Object.entries(MODALITY_WINDOW_LEVEL_PRESETS[mod]);
        setPresets(presetList.slice(0, 4)); // Show top 4
      }
    }
  }, [metadata]);

  const applyPreset = (presetName) => {
    if (!modality) return;
    
    const preset = MODALITY_WINDOW_LEVEL_PRESETS[modality][presetName];
    if (preset && !preset.auto) {
      const viewport = cornerstoneViewportService.getCornerstoneViewport(viewportId);
      if (viewport) {
        viewport.setWindowLevel(preset.level, preset.window);
      }
    }
  };

  return (
    <div className="quick-preset-toolbar">
      {presets.map(([name]) => (
        <button
          key={name}
          className="quick-preset-btn"
          onClick={() => applyPreset(name)}
          title={name}
        >
          {name.split(' - ')[0]}
        </button>
      ))}
    </div>
  );
}

/**
 * CSS Styles for Controls
 * 
 * Location: sa-dicom-viewer/styles/enhanced-controls.css
 */
export const ENHANCED_CONTROLS_CSS = `
.enhanced-image-controls {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 16px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  max-width: 350px;
}

.controls-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  border-bottom: 2px solid #ddd;
  padding-bottom: 8px;
}

.controls-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.quality-indicator {
  display: flex;
  gap: 8px;
}

.quality-badge {
  background: #51cf66;
  color: white;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 600;
}

/* Presets Section */
.presets-section {
  margin-bottom: 16px;
}

.presets-section h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.preset-buttons {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.preset-btn {
  padding: 8px 12px;
  border: 2px solid #ddd;
  background: white;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #333;
}

.preset-btn:hover {
  border-color: #2196F3;
  background: #e3f2fd;
}

.preset-btn.active {
  border-color: #2196F3;
  background: #2196F3;
  color: white;
}

.preset-btn.auto-btn {
  grid-column: span 3;
  background: #ff9800;
  border-color: #ff9800;
  color: white;
}

.preset-btn.auto-btn:hover {
  background: #f57c00;
  border-color: #f57c00;
}

.preset-btn.auto-btn.loading {
  opacity: 0.7;
  cursor: not-allowed;
}

/* Window/Level Display */
.window-level-display {
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 16px;
}

.value-pair {
  display: flex;
  gap: 16px;
}

.value-item {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.value-item label {
  font-size: 12px;
  color: #999;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.value-item .value {
  font-size: 18px;
  font-weight: 700;
  color: #2196F3;
  font-family: 'Monaco', monospace;
}

/* Sliders */
.adjustment-sliders {
  margin-bottom: 16px;
}

.slider-group {
  margin-bottom: 12px;
}

.slider-group label {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 6px;
}

.slider-value {
  font-family: monospace;
  background: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #ddd;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #2196F3;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #2196F3;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* Statistics Section */
.statistics-section {
  margin-bottom: 16px;
}

.stats-toggle-btn {
  width: 100%;
  padding: 10px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.stats-toggle-btn:hover {
  background: #f9f9f9;
  border-color: #bbb;
}

.stats-display {
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 10px;
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-label {
  font-size: 11px;
  color: #999;
  text-transform: uppercase;
}

.stat-value {
  font-size: 14px;
  font-weight: 700;
  color: #2196F3;
  font-family: monospace;
}

/* Reset Button */
.reset-btn {
  width: 100%;
  padding: 10px;
  background: #f44336;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.reset-btn:hover {
  background: #d32f2f;
}

/* Toolbar Version */
.quick-preset-toolbar {
  display: flex;
  gap: 8px;
  padding: 8px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.quick-preset-btn {
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.quick-preset-btn:hover {
  background: #e8e8e8;
  border-color: #2196F3;
}

.quick-preset-btn.active {
  background: #2196F3;
  color: white;
  border-color: #2196F3;
}

/* Responsive */
@media (max-width: 768px) {
  .enhanced-image-controls {
    max-width: 100%;
  }
  
  .preset-buttons {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .preset-btn.auto-btn {
    grid-column: span 2;
  }
}
`;

export default EnhancedImageControlPanel;
