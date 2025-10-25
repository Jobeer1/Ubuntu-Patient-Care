/**
 * Multi-Planar Reconstruction (MPR) Viewer
 * Advanced 2D slice viewing with 3D navigation for CT, MRI, and Ultrasound
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { useMobileOptimization } from '../../mobile/hooks/useMobileOptimization.js';
import { useTouchGestures } from '../../mobile/hooks/useTouchGestures.js';

const MPRViewer = ({
    volumeData,
    onSliceChange,
    onMeasurement,
    className = ''
}) => {
    const axialCanvasRef = useRef(null);
    const sagittalCanvasRef = useRef(null);
    const coronalCanvasRef = useRef(null);
    const oblique3DCanvasRef = useRef(null);

    const [currentSlices, setCurrentSlices] = useState({
        axial: 0,
        sagittal: 0,
        coronal: 0
    });

    const [viewportStates, setViewportStates] = useState({
        axial: { zoom: 1, pan: { x: 0, y: 0 }, windowLevel: { window: 400, level: 40 } },
        sagittal: { zoom: 1, pan: { x: 0, y: 0 }, windowLevel: { window: 400, level: 40 } },
        coronal: { zoom: 1, pan: { x: 0, y: 0 }, windowLevel: { window: 400, level: 40 } },
        oblique3D: { zoom: 1, pan: { x: 0, y: 0 }, rotation: { x: 0, y: 0, z: 0 } }
    });

    const [activeViewport, setActiveViewport] = useState('axial');
    const [syncViewports, setSyncViewports] = useState(true);
    const [showCrosshairs, setShowCrosshairs] = useState(true);
    const [mprMode, setMprMode] = useState('standard'); // 'standard', 'thick-slab', 'curved'
    const [slabThickness, setSlabThickness] = useState(1);
    const [measurements, setMeasurements] = useState([]);

    // Mobile optimization
    const { isMobile, isTablet, isLowBandwidth } = useMobileOptimization();

    // Touch gestures for mobile
    const axialGestures = useTouchGestures({
        onPinch: (scale) => handleZoom('axial', scale),
        onPan: (deltaX, deltaY) => handlePan('axial', deltaX, deltaY),
        onTap: (x, y) => handleTap('axial', x, y),
        onSwipe: (direction) => handleSwipe('axial', direction)
    });

    const sagittalGestures = useTouchGestures({
        onPinch: (scale) => handleZoom('sagittal', scale),
        onPan: (deltaX, deltaY) => handlePan('sagittal', deltaX, deltaY),
        onTap: (x, y) => handleTap('sagittal', x, y),
        onSwipe: (direction) => handleSwipe('sagittal', direction)
    });

    const coronalGestures = useTouchGestures({
        onPinch: (scale) => handleZoom('coronal', scale),
        onPan: (deltaX, deltaY) => handlePan('coronal', deltaX, deltaY),
        onTap: (x, y) => handleTap('coronal', x, y),
        onSwipe: (direction) => handleSwipe('coronal', direction)
    });

    // Initialize MPR renderer
    useEffect(() => {
        if (!volumeData) return;

        const initMPRRenderer = async () => {
            try {
                // Initialize canvases and rendering contexts
                await Promise.all([
                    initViewport('axial', axialCanvasRef.current),
                    initViewport('sagittal', sagittalCanvasRef.current),
                    initViewport('coronal', coronalCanvasRef.current),
                    initViewport('oblique3D', oblique3DCanvasRef.current)
                ]);

                // Set initial slice positions
                setCurrentSlices({
                    axial: Math.floor(volumeData.dimensions.z / 2),
                    sagittal: Math.floor(volumeData.dimensions.x / 2),
                    coronal: Math.floor(volumeData.dimensions.y / 2)
                });

                renderAllViewports();
            } catch (error) {
                console.error('MPR initialization failed:', error);
            }
        };

        initMPRRenderer();
    }, [volumeData]);

    // Handle viewport interactions
    const handleZoom = useCallback((viewport, scale) => {
        setViewportStates(prev => ({
            ...prev,
            [viewport]: {
                ...prev[viewport],
                zoom: Math.max(0.1, Math.min(10, prev[viewport].zoom * scale))
            }
        }));
        renderViewport(viewport);
    }, []);

    const handlePan = useCallback((viewport, deltaX, deltaY) => {
        setViewportStates(prev => ({
            ...prev,
            [viewport]: {
                ...prev[viewport],
                pan: {
                    x: prev[viewport].pan.x + deltaX,
                    y: prev[viewport].pan.y + deltaY
                }
            }
        }));
        renderViewport(viewport);
    }, []);

    const handleTap = useCallback((viewport, x, y) => {
        if (activeViewport !== viewport) {
            setActiveViewport(viewport);
        }

        // Convert screen coordinates to volume coordinates
        const volumeCoords = screenToVolumeCoords(viewport, x, y);

        if (syncViewports) {
            updateCrosshairPosition(volumeCoords);
        }
    }, [activeViewport, syncViewports]);

    const handleSwipe = useCallback((viewport, direction) => {
        const increment = direction === 'up' || direction === 'right' ? 1 : -1;

        setCurrentSlices(prev => {
            const newSlices = { ...prev };
            const maxSlice = getMaxSliceForViewport(viewport);

            newSlices[viewport] = Math.max(0, Math.min(maxSlice - 1, prev[viewport] + increment));

            if (onSliceChange) {
                onSliceChange(viewport, newSlices[viewport]);
            }

            return newSlices;
        });

        renderViewport(viewport);
    }, [onSliceChange]);

    // Initialize viewport rendering
    const initViewport = async (viewportName, canvas) => {
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error(`Failed to get 2D context for ${viewportName}`);

        // Set canvas size
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * window.devicePixelRatio;
        canvas.height = rect.height * window.devicePixelRatio;
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

        // Store context for later use
        canvas._renderingContext = ctx;
        canvas._viewportName = viewportName;
    };

    // Render specific viewport
    const renderViewport = useCallback((viewportName) => {
        if (!volumeData) return;

        const canvas = getCanvasForViewport(viewportName);
        if (!canvas || !canvas._renderingContext) return;

        const ctx = canvas._renderingContext;
        const state = viewportStates[viewportName];
        const sliceIndex = currentSlices[viewportName];

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width / window.devicePixelRatio, canvas.height / window.devicePixelRatio);

        // Extract slice data based on viewport orientation
        const sliceData = extractSliceData(viewportName, sliceIndex);

        // Apply window/level
        const processedData = applyWindowLevel(sliceData, state.windowLevel);

        // Create image data
        const imageData = createImageData(ctx, processedData, volumeData.dimensions);

        // Apply transformations
        ctx.save();
        ctx.translate(canvas.width / (2 * window.devicePixelRatio), canvas.height / (2 * window.devicePixelRatio));
        ctx.scale(state.zoom, state.zoom);
        ctx.translate(state.pan.x, state.pan.y);

        // Draw image
        ctx.putImageData(imageData, -imageData.width / 2, -imageData.height / 2);

        // Draw crosshairs if enabled
        if (showCrosshairs) {
            drawCrosshairs(ctx, viewportName);
        }

        // Draw measurements
        drawMeasurements(ctx, viewportName);

        ctx.restore();
    }, [volumeData, viewportStates, currentSlices, showCrosshairs]);

    // Render all viewports
    const renderAllViewports = useCallback(() => {
        ['axial', 'sagittal', 'coronal', 'oblique3D'].forEach(viewport => {
            renderViewport(viewport);
        });
    }, [renderViewport]);

    // Extract slice data for specific orientation
    const extractSliceData = (viewportName, sliceIndex) => {
        if (!volumeData) return null;

        const { buffer, dimensions } = volumeData;
        const { x: width, y: height, z: depth } = dimensions;

        switch (viewportName) {
            case 'axial':
                // Extract axial slice (XY plane)
                const axialSlice = new volumeData.constructor(width * height);
                const axialOffset = sliceIndex * width * height;
                axialSlice.set(buffer.subarray(axialOffset, axialOffset + width * height));
                return { data: axialSlice, width, height };

            case 'sagittal':
                // Extract sagittal slice (YZ plane)
                const sagittalSlice = new volumeData.constructor(height * depth);
                for (let z = 0; z < depth; z++) {
                    for (let y = 0; y < height; y++) {
                        const volumeIndex = z * width * height + y * width + sliceIndex;
                        const sliceIndex2D = z * height + y;
                        sagittalSlice[sliceIndex2D] = buffer[volumeIndex];
                    }
                }
                return { data: sagittalSlice, width: height, height: depth };

            case 'coronal':
                // Extract coronal slice (XZ plane)
                const coronalSlice = new volumeData.constructor(width * depth);
                for (let z = 0; z < depth; z++) {
                    for (let x = 0; x < width; x++) {
                        const volumeIndex = z * width * height + sliceIndex * width + x;
                        const sliceIndex2D = z * width + x;
                        coronalSlice[sliceIndex2D] = buffer[volumeIndex];
                    }
                }
                return { data: coronalSlice, width, height: depth };

            default:
                return null;
        }
    };

    // Apply window/level to slice data
    const applyWindowLevel = (sliceData, windowLevel) => {
        if (!sliceData) return null;

        const { window, level } = windowLevel;
        const minValue = level - window / 2;
        const maxValue = level + window / 2;
        const range = maxValue - minValue;

        const processedData = new Uint8ClampedArray(sliceData.data.length);

        for (let i = 0; i < sliceData.data.length; i++) {
            const value = sliceData.data[i];
            const normalized = Math.max(0, Math.min(1, (value - minValue) / range));
            processedData[i] = Math.floor(normalized * 255);
        }

        return { ...sliceData, data: processedData };
    };

    // Create ImageData for canvas rendering
    const createImageData = (ctx, processedData, dimensions) => {
        if (!processedData) return null;

        const { width, height } = processedData;
        const imageData = ctx.createImageData(width, height);
        const data = imageData.data;

        for (let i = 0; i < processedData.data.length; i++) {
            const pixelIndex = i * 4;
            const value = processedData.data[i];

            data[pixelIndex] = value;     // R
            data[pixelIndex + 1] = value; // G
            data[pixelIndex + 2] = value; // B
            data[pixelIndex + 3] = 255;   // A
        }

        return imageData;
    };

    // Draw crosshairs
    const drawCrosshairs = (ctx, viewportName) => {
        const canvas = getCanvasForViewport(viewportName);
        if (!canvas) return;

        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 1;
        ctx.setLineDash([5, 5]);

        const centerX = 0;
        const centerY = 0;
        const size = 50;

        ctx.beginPath();
        ctx.moveTo(centerX - size, centerY);
        ctx.lineTo(centerX + size, centerY);
        ctx.moveTo(centerX, centerY - size);
        ctx.lineTo(centerX, centerY + size);
        ctx.stroke();

        ctx.setLineDash([]);
    };

    // Draw measurements
    const drawMeasurements = (ctx, viewportName) => {
        const viewportMeasurements = measurements.filter(m => m.viewport === viewportName);

        ctx.strokeStyle = '#ffff00';
        ctx.fillStyle = '#ffff00';
        ctx.lineWidth = 2;
        ctx.font = '12px Arial';

        viewportMeasurements.forEach(measurement => {
            if (measurement.type === 'distance' && measurement.points.length === 2) {
                const [p1, p2] = measurement.points;

                // Draw line
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.stroke();

                // Draw measurement text
                const midX = (p1.x + p2.x) / 2;
                const midY = (p1.y + p2.y) / 2;
                ctx.fillText(`${measurement.value.toFixed(1)} mm`, midX + 5, midY - 5);
            }
        });
    };

    // Utility functions
    const getCanvasForViewport = (viewportName) => {
        switch (viewportName) {
            case 'axial': return axialCanvasRef.current;
            case 'sagittal': return sagittalCanvasRef.current;
            case 'coronal': return coronalCanvasRef.current;
            case 'oblique3D': return oblique3DCanvasRef.current;
            default: return null;
        }
    };

    const getMaxSliceForViewport = (viewportName) => {
        if (!volumeData) return 1;

        switch (viewportName) {
            case 'axial': return volumeData.dimensions.z;
            case 'sagittal': return volumeData.dimensions.x;
            case 'coronal': return volumeData.dimensions.y;
            default: return 1;
        }
    };

    const screenToVolumeCoords = (viewport, screenX, screenY) => {
        // Convert screen coordinates to volume coordinates
        // This is a simplified implementation
        return { x: screenX, y: screenY, z: currentSlices[viewport] };
    };

    const updateCrosshairPosition = (volumeCoords) => {
        // Update crosshair positions across all viewports
        // Implementation would update slice positions based on 3D coordinates
    };

    // Handle preset changes
    const handlePresetChange = (presetName) => {
        if (!volumeData?.windowLevel?.presets?.[presetName]) return;

        const preset = volumeData.windowLevel.presets[presetName];
        setViewportStates(prev => ({
            ...prev,
            [activeViewport]: {
                ...prev[activeViewport],
                windowLevel: preset
            }
        }));

        renderViewport(activeViewport);
    };

    return (
        <div className={`mpr-viewer ${className}`}>
            {/* MPR Controls */}
            <div className="mpr-controls">
                <div className="control-group">
                    <label>Mode:</label>
                    <select
                        value={mprMode}
                        onChange={(e) => setMprMode(e.target.value)}
                        className="control-select"
                    >
                        <option value="standard">Standard MPR</option>
                        <option value="thick-slab">Thick Slab</option>
                        <option value="curved">Curved MPR</option>
                    </select>
                </div>

                {mprMode === 'thick-slab' && (
                    <div className="control-group">
                        <label>Thickness:</label>
                        <input
                            type="range"
                            min="1"
                            max="20"
                            value={slabThickness}
                            onChange={(e) => setSlabThickness(parseInt(e.target.value))}
                            className="control-slider"
                        />
                        <span>{slabThickness}mm</span>
                    </div>
                )}

                <div className="control-group">
                    <button
                        className={`control-btn ${syncViewports ? 'active' : ''}`}
                        onClick={() => setSyncViewports(!syncViewports)}
                    >
                        Sync Viewports
                    </button>
                    <button
                        className={`control-btn ${showCrosshairs ? 'active' : ''}`}
                        onClick={() => setShowCrosshairs(!showCrosshairs)}
                    >
                        Crosshairs
                    </button>
                </div>

                {/* Window/Level presets */}
                {volumeData?.windowLevel?.presets && (
                    <div className="control-group">
                        <label>Presets:</label>
                        <div className="preset-buttons">
                            {Object.keys(volumeData.windowLevel.presets).map(presetName => (
                                <button
                                    key={presetName}
                                    className="preset-btn"
                                    onClick={() => handlePresetChange(presetName)}
                                >
                                    {presetName}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* MPR Viewports */}
            <div className={`mpr-viewports ${isMobile ? 'mobile-layout' : 'desktop-layout'}`}>
                {/* Axial Viewport */}
                <div className={`viewport axial ${activeViewport === 'axial' ? 'active' : ''}`}>
                    <div className="viewport-header">
                        <span>Axial - Slice {currentSlices.axial + 1}/{volumeData?.dimensions?.z || 0}</span>
                        <span>W/L: {viewportStates.axial.windowLevel.window}/{viewportStates.axial.windowLevel.level}</span>
                    </div>
                    <canvas
                        ref={axialCanvasRef}
                        className="mpr-canvas"
                        {...axialGestures}
                        onClick={() => setActiveViewport('axial')}
                    />
                </div>

                {/* Sagittal Viewport */}
                <div className={`viewport sagittal ${activeViewport === 'sagittal' ? 'active' : ''}`}>
                    <div className="viewport-header">
                        <span>Sagittal - Slice {currentSlices.sagittal + 1}/{volumeData?.dimensions?.x || 0}</span>
                        <span>W/L: {viewportStates.sagittal.windowLevel.window}/{viewportStates.sagittal.windowLevel.level}</span>
                    </div>
                    <canvas
                        ref={sagittalCanvasRef}
                        className="mpr-canvas"
                        {...sagittalGestures}
                        onClick={() => setActiveViewport('sagittal')}
                    />
                </div>

                {/* Coronal Viewport */}
                <div className={`viewport coronal ${activeViewport === 'coronal' ? 'active' : ''}`}>
                    <div className="viewport-header">
                        <span>Coronal - Slice {currentSlices.coronal + 1}/{volumeData?.dimensions?.y || 0}</span>
                        <span>W/L: {viewportStates.coronal.windowLevel.window}/{viewportStates.coronal.windowLevel.level}</span>
                    </div>
                    <canvas
                        ref={coronalCanvasRef}
                        className="mpr-canvas"
                        {...coronalGestures}
                        onClick={() => setActiveViewport('coronal')}
                    />
                </div>

                {/* 3D Oblique Viewport */}
                <div className={`viewport oblique3d ${activeViewport === 'oblique3D' ? 'active' : ''}`}>
                    <div className="viewport-header">
                        <span>3D Oblique</span>
                        <span>Interactive</span>
                    </div>
                    <canvas
                        ref={oblique3DCanvasRef}
                        className="mpr-canvas"
                        onClick={() => setActiveViewport('oblique3D')}
                    />
                </div>
            </div>

            {/* Mobile-specific controls */}
            {(isMobile || isTablet) && (
                <div className="mobile-mpr-controls">
                    <button className="mobile-control-btn">🔄</button>
                    <button className="mobile-control-btn">📏</button>
                    <button className="mobile-control-btn">🎯</button>
                    <button className="mobile-control-btn">⚙️</button>
                </div>
            )}

            {/* South African optimizations indicator */}
            {isLowBandwidth && (
                <div className="sa-optimization-indicator">
                    📶 Optimized for SA Networks
                </div>
            )}
        </div>
    );
};

export default MPRViewer;