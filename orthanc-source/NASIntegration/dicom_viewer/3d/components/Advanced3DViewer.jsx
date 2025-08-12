/**
 * Advanced 3D DICOM Viewer Component
 * Specialized for CT, MRI, and Ultrasound with South African healthcare optimizations
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import DicomVolumeProcessor from '../core/DicomVolumeProcessor.js';
import VolumeRenderer from '../rendering/VolumeRenderer.js';
import { useMobileOptimization } from '../../mobile/hooks/useMobileOptimization.js';

const Advanced3DViewer = ({ 
    studyData, 
    seriesData, 
    modality = 'CT',
    onMeasurement,
    onError,
    className = ''
}) => {
    const canvasRef = useRef(null);
    const rendererRef = useRef(null);
    const processorRef = useRef(null);
    
    const [isLoading, setIsLoading] = useState(false);
    const [loadingProgress, setLoadingProgress] = useState(0);
    const [renderingMode, setRenderingMode] = useState('volume');
    const [qualityLevel, setQualityLevel] = useState('high');
    const [volumeData, setVolumeData] = useState(null);
    const [error, setError] = useState(null);
    
    // 3D viewer state
    const [viewerState, setViewerState] = useState({
        camera: {
            position: [0, 0, 2],
            target: [0, 0, 0],
            up: [0, 1, 0],
            fov: 45
        },
        lighting: {
            direction: [0.5, 0.5, -1.0],
            color: [1.0, 1.0, 1.0],
            ambient: 0.3
        },
        windowLevel: {
            window: 400,
            level: 40
        },
        transferFunction: null,
        clipping: {
            enabled: false,
            planes: []
        }
    });

    // UI state
    const [activeTools, setActiveTools] = useState({
        rotate: true,
        zoom: false,
        pan: false,
        windowLevel: false,
        measurement: false
    });

    const [measurements, setMeasurements] = useState([]);
    const [showControls, setShowControls] = useState(true);

    // Mobile optimization
    const { 
        isMobile, 
        isTablet, 
        isLowBandwidth, 
        deviceInfo 
    } = useMobileOptimization();

    // Initialize 3D viewer
    useEffect(() => {
        if (!canvasRef.current) return;

        const initViewer = async () => {
            try {
                // Initialize volume processor
                processorRef.current = new DicomVolumeProcessor();
                
                // Initialize renderer with SA optimizations
                const rendererOptions = {
                    qualityLevel: isLowBandwidth ? 'low' : qualityLevel,
                    saOptimizations: {
                        lowBandwidth: isLowBandwidth,
                        mobileDevice: isMobile || isTablet,
                        powerSave: deviceInfo.batteryLevel < 0.2
                    }
                };
                
                rendererRef.current = new VolumeRenderer(canvasRef.current, rendererOptions);
                
                console.log('3D viewer initialized successfully');
                
            } catch (error) {
                console.error('Failed to initialize 3D viewer:', error);
                setError(`3D viewer initialization failed: ${error.message}`);
                onError?.(error);
            }
        };

        initViewer();

        return () => {
            if (rendererRef.current) {
                rendererRef.current.dispose();
            }
        };
    }, [qualityLevel, isLowBandwidth, isMobile, isTablet, deviceInfo.batteryLevel, onError]);

    // Process DICOM series when data changes
    useEffect(() => {
        if (!seriesData || !processorRef.current || !rendererRef.current) return;

        const processVolume = async () => {
            setIsLoading(true);
            setError(null);
            
            try {
                console.log(`Processing ${modality} volume with ${seriesData.length} slices`);
                
                const processingOptions = {
                    modality,
                    qualityLevel: isLowBandwidth ? 'medium' : qualityLevel,
                    progressCallback: (progress) => {
                        setLoadingProgress(Math.round(progress * 100));
                    }
                };

                // Process volume based on modality
                const processedVolume = await processorRef.current.processVolume(
                    seriesData, 
                    processingOptions
                );

                // Load into renderer
                rendererRef.current.loadVolumeData(processedVolume);
                
                // Update viewer state with volume-specific settings
                setViewerState(prev => ({
                    ...prev,
                    windowLevel: processedVolume.windowLevel.default,
                    transferFunction: processedVolume.transferFunction
                }));

                setVolumeData(processedVolume);
                
                // Initial render
                rendererRef.current.render();
                
                console.log(`${modality} volume processing completed`);
                
            } catch (error) {
                console.error('Volume processing failed:', error);
                setError(`Failed to process ${modality} volume: ${error.message}`);
                onError?.(error);
            } finally {
                setIsLoading(false);
                setLoadingProgress(0);
            }
        };

        processVolume();
    }, [seriesData, modality, qualityLevel, isLowBandwidth, onError]);

    // Handle rendering mode change
    const handleRenderingModeChange = useCallback((mode) => {
        setRenderingMode(mode);
        if (rendererRef.current) {
            rendererRef.current.setRenderingMode(mode);
        }
    }, []);

    // Handle quality level change
    const handleQualityChange = useCallback((level) => {
        setQualityLevel(level);
        if (rendererRef.current) {
            rendererRef.current.setQualityLevel(level);
        }
    }, []);

    // Handle window/level adjustment
    const handleWindowLevelChange = useCallback((window, level) => {
        setViewerState(prev => ({
            ...prev,
            windowLevel: { window, level }
        }));
        
        // Update renderer uniforms would go here
        if (rendererRef.current) {
            rendererRef.current.render();
        }
    }, []);

    // Handle camera movement
    const handleCameraChange = useCallback((cameraUpdate) => {
        setViewerState(prev => ({
            ...prev,
            camera: { ...prev.camera, ...cameraUpdate }
        }));
        
        if (rendererRef.current) {
            rendererRef.current.updateCamera(cameraUpdate);
        }
    }, []);

    // Handle tool selection
    const handleToolChange = useCallback((toolName) => {
        setActiveTools(prev => ({
            ...Object.keys(prev).reduce((acc, key) => ({ ...acc, [key]: false }), {}),
            [toolName]: true
        }));
    }, []);

    // Handle preset selection
    const handlePresetChange = useCallback((presetName) => {
        if (!volumeData?.windowLevel?.presets?.[presetName]) return;
        
        const preset = volumeData.windowLevel.presets[presetName];
        handleWindowLevelChange(preset.window, preset.level);
    }, [volumeData, handleWindowLevelChange]);

    // Get modality-specific presets
    const getModalityPresets = useCallback(() => {
        if (!volumeData?.windowLevel?.presets) return [];
        
        return Object.keys(volumeData.windowLevel.presets).map(name => ({
            name,
            ...volumeData.windowLevel.presets[name]
        }));
    }, [volumeData]);

    // Render loading overlay
    const renderLoadingOverlay = () => (
        <div className="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center z-10">
            <div className="text-center text-white">
                <div className="mb-4">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
                </div>
                <div className="text-lg font-semibold mb-2">
                    Processing {modality} Volume
                </div>
                <div className="text-sm text-gray-300 mb-4">
                    {seriesData?.length || 0} slices • {loadingProgress}% complete
                </div>
                <div className="w-64 bg-gray-700 rounded-full h-2">
                    <div 
                        className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${loadingProgress}%` }}
                    ></div>
                </div>
            </div>
        </div>
    );

    // Render error overlay
    const renderErrorOverlay = () => (
        <div className="absolute inset-0 bg-red-900 bg-opacity-75 flex items-center justify-center z-10">
            <div className="text-center text-white max-w-md">
                <div className="text-6xl mb-4">⚠️</div>
                <div className="text-lg font-semibold mb-2">3D Rendering Error</div>
                <div className="text-sm text-red-200 mb-4">{error}</div>
                <button 
                    className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded"
                    onClick={() => setError(null)}
                >
                    Dismiss
                </button>
            </div>
        </div>
    );

    // Render 3D controls
    const render3DControls = () => (
        <div className={`absolute top-4 left-4 bg-black bg-opacity-75 rounded-lg p-4 text-white ${isMobile ? 'text-sm' : ''}`}>
            {/* Rendering Mode */}
            <div className="mb-4">
                <label className="block text-xs font-semibold mb-2">Rendering Mode</label>
                <div className="flex flex-wrap gap-2">
                    {['volume', 'mip', 'surface', 'mpr'].map(mode => (
                        <button
                            key={mode}
                            className={`px-3 py-1 rounded text-xs ${
                                renderingMode === mode 
                                    ? 'bg-blue-600' 
                                    : 'bg-gray-600 hover:bg-gray-500'
                            }`}
                            onClick={() => handleRenderingModeChange(mode)}
                        >
                            {mode.toUpperCase()}
                        </button>
                    ))}
                </div>
            </div>

            {/* Quality Level */}
            <div className="mb-4">
                <label className="block text-xs font-semibold mb-2">Quality</label>
                <div className="flex gap-2">
                    {['low', 'medium', 'high'].map(level => (
                        <button
                            key={level}
                            className={`px-3 py-1 rounded text-xs ${
                                qualityLevel === level 
                                    ? 'bg-green-600' 
                                    : 'bg-gray-600 hover:bg-gray-500'
                            }`}
                            onClick={() => handleQualityChange(level)}
                            disabled={isLowBandwidth && level === 'high'}
                        >
                            {level}
                        </button>
                    ))}
                </div>
            </div>

            {/* Modality-specific presets */}
            {modality === 'CT' && (
                <div className="mb-4">
                    <label className="block text-xs font-semibold mb-2">CT Presets</label>
                    <div className="flex flex-wrap gap-1">
                        {getModalityPresets().map(preset => (
                            <button
                                key={preset.name}
                                className="px-2 py-1 rounded text-xs bg-gray-600 hover:bg-gray-500"
                                onClick={() => handlePresetChange(preset.name)}
                            >
                                {preset.name}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Window/Level */}
            <div className="mb-4">
                <label className="block text-xs font-semibold mb-2">
                    W/L: {viewerState.windowLevel.window}/{viewerState.windowLevel.level}
                </label>
                <div className="space-y-2">
                    <input
                        type="range"
                        min="1"
                        max="2000"
                        value={viewerState.windowLevel.window}
                        onChange={(e) => handleWindowLevelChange(
                            parseInt(e.target.value), 
                            viewerState.windowLevel.level
                        )}
                        className="w-full"
                    />
                    <input
                        type="range"
                        min="-1000"
                        max="1000"
                        value={viewerState.windowLevel.level}
                        onChange={(e) => handleWindowLevelChange(
                            viewerState.windowLevel.window, 
                            parseInt(e.target.value)
                        )}
                        className="w-full"
                    />
                </div>
            </div>

            {/* Tools */}
            <div className="mb-4">
                <label className="block text-xs font-semibold mb-2">Tools</label>
                <div className="flex flex-wrap gap-2">
                    {Object.keys(activeTools).map(tool => (
                        <button
                            key={tool}
                            className={`px-2 py-1 rounded text-xs ${
                                activeTools[tool] 
                                    ? 'bg-yellow-600' 
                                    : 'bg-gray-600 hover:bg-gray-500'
                            }`}
                            onClick={() => handleToolChange(tool)}
                        >
                            {tool}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );

    // Render volume info
    const renderVolumeInfo = () => (
        <div className="absolute bottom-4 left-4 bg-black bg-opacity-75 rounded-lg p-3 text-white text-xs">
            <div className="font-semibold mb-1">{modality} Volume Info</div>
            {volumeData && (
                <>
                    <div>Dimensions: {volumeData.dimensions.x}×{volumeData.dimensions.y}×{volumeData.dimensions.z}</div>
                    <div>Spacing: {volumeData.spacing.x.toFixed(2)}×{volumeData.spacing.y.toFixed(2)}×{volumeData.spacing.z.toFixed(2)} mm</div>
                    <div>Type: {volumeData.type}</div>
                    {volumeData.sequenceType && (
                        <div>Sequence: {volumeData.sequenceType}</div>
                    )}
                </>
            )}
        </div>
    );

    // Render SA optimization indicators
    const renderSAIndicators = () => (
        <div className="absolute top-4 right-4 space-y-2">
            {isLowBandwidth && (
                <div className="bg-yellow-600 text-white px-3 py-1 rounded text-xs">
                    📶 Low Bandwidth Mode
                </div>
            )}
            {deviceInfo.batteryLevel < 0.2 && (
                <div className="bg-red-600 text-white px-3 py-1 rounded text-xs">
                    🔋 Power Save Mode
                </div>
            )}
            {(isMobile || isTablet) && (
                <div className="bg-blue-600 text-white px-3 py-1 rounded text-xs">
                    📱 Mobile Optimized
                </div>
            )}
        </div>
    );

    return (
        <div className={`relative w-full h-full bg-black ${className}`}>
            {/* Main 3D Canvas */}
            <canvas
                ref={canvasRef}
                className="w-full h-full"
                style={{ touchAction: 'none' }}
            />

            {/* Loading Overlay */}
            {isLoading && renderLoadingOverlay()}

            {/* Error Overlay */}
            {error && renderErrorOverlay()}

            {/* 3D Controls */}
            {showControls && !isLoading && !error && render3DControls()}

            {/* Volume Info */}
            {volumeData && !isLoading && !error && renderVolumeInfo()}

            {/* SA Optimization Indicators */}
            {renderSAIndicators()}

            {/* Mobile Controls Toggle */}
            {(isMobile || isTablet) && (
                <button
                    className="absolute bottom-4 right-4 bg-blue-600 text-white p-3 rounded-full"
                    onClick={() => setShowControls(!showControls)}
                >
                    {showControls ? '🔧' : '⚙️'}
                </button>
            )}

            {/* Measurements Overlay */}
            {measurements.length > 0 && (
                <div className="absolute top-1/2 right-4 transform -translate-y-1/2 bg-black bg-opacity-75 rounded-lg p-3 text-white text-xs max-w-xs">
                    <div className="font-semibold mb-2">3D Measurements</div>
                    {measurements.map((measurement, index) => (
                        <div key={index} className="mb-1">
                            {measurement.type}: {measurement.value} {measurement.unit}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default Advanced3DViewer;