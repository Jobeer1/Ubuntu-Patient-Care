/**
 * Touch-Optimized DICOM Viewer for Mobile Devices
 * Designed for South African healthcare professionals
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useTouchGestures } from '../hooks/useTouchGestures';
import { useMobileOptimization } from '../hooks/useMobileOptimization';

const TouchDicomViewer = ({ 
    studyId, 
    seriesId, 
    imageData, 
    onImageChange,
    onMeasurement,
    isOffline = false 
}) => {
    const viewportRef = useRef(null);
    const imageRef = useRef(null);
    const [currentImageIndex, setCurrentImageIndex] = useState(0);
    const [viewportState, setViewportState] = useState({
        zoom: 1,
        pan: { x: 0, y: 0 },
        windowLevel: { width: 400, center: 40 },
        rotation: 0,
        invert: false
    });
    const [activeTools, setActiveTools] = useState({
        pan: false,
        zoom: false,
        windowLevel: false,
        measurement: false
    });
    const [measurements, setMeasurements] = useState([]);
    const [isLoading, setIsLoading] = useState(true);

    // Mobile optimization hooks
    const { deviceInfo, isLowBandwidth } = useMobileOptimization();
    
    // Touch gesture handling
    const {
        onTouchStart,
        onTouchMove,
        onTouchEnd,
        gestureState
    } = useTouchGestures({
        onPinch: handlePinchZoom,
        onPan: handlePan,
        onTap: handleTap,
        onDoubleTap: handleDoubleTap,
        onLongPress: handleLongPress
    });

    // Load image data
    useEffect(() => {
        if (imageData && imageData.length > 0) {
            loadImage(imageData[currentImageIndex]);
        }
    }, [imageData, currentImageIndex]);

    const loadImage = async (imageInfo) => {
        setIsLoading(true);
        try {
            // Optimize image loading for mobile
            const imageUrl = isLowBandwidth 
                ? imageInfo.thumbnailUrl || imageInfo.url
                : imageInfo.url;
            
            const img = new Image();
            img.onload = () => {
                setIsLoading(false);
                // Auto-fit image to viewport
                if (viewportRef.current && img.naturalWidth && img.naturalHeight) {
                    const viewport = viewportRef.current.getBoundingClientRect();
                    const scaleX = viewport.width / img.naturalWidth;
                    const scaleY = viewport.height / img.naturalHeight;
                    const scale = Math.min(scaleX, scaleY, 1);
                    
                    setViewportState(prev => ({
                        ...prev,
                        zoom: scale,
                        pan: { x: 0, y: 0 }
                    }));
                }
            };
            img.onerror = () => {
                setIsLoading(false);
                console.error('Failed to load DICOM image');
            };
            img.src = imageUrl;
        } catch (error) {
            setIsLoading(false);
            console.error('Error loading image:', error);
        }
    };

    // Touch gesture handlers
    function handlePinchZoom(scale, center) {
        setViewportState(prev => ({
            ...prev,
            zoom: Math.max(0.1, Math.min(10, prev.zoom * scale))
        }));
    }

    function handlePan(deltaX, deltaY) {
        if (activeTools.pan || gestureState.isPanning) {
            setViewportState(prev => ({
                ...prev,
                pan: {
                    x: prev.pan.x + deltaX,
                    y: prev.pan.y + deltaY
                }
            }));
        } else if (activeTools.windowLevel) {
            // Window/Level adjustment with touch
            const windowDelta = deltaX * 2;
            const levelDelta = -deltaY * 2;
            
            setViewportState(prev => ({
                ...prev,
                windowLevel: {
                    width: Math.max(1, prev.windowLevel.width + windowDelta),
                    center: prev.windowLevel.center + levelDelta
                }
            }));
        }
    }

    function handleTap(x, y) {
        if (activeTools.measurement) {
            addMeasurementPoint(x, y);
        }
    }

    function handleDoubleTap(x, y) {
        // Reset zoom and pan
        setViewportState(prev => ({
            ...prev,
            zoom: 1,
            pan: { x: 0, y: 0 }
        }));
    }

    function handleLongPress(x, y) {
        // Show context menu
        showContextMenu(x, y);
    }

    // Navigation functions
    const navigateToImage = useCallback((direction) => {
        if (!imageData || imageData.length === 0) return;
        
        const newIndex = direction === 'next' 
            ? Math.min(currentImageIndex + 1, imageData.length - 1)
            : Math.max(currentImageIndex - 1, 0);
        
        if (newIndex !== currentImageIndex) {
            setCurrentImageIndex(newIndex);
            onImageChange?.(newIndex);
        }
    }, [currentImageIndex, imageData, onImageChange]);

    // Swipe navigation
    useEffect(() => {
        if (gestureState.swipeDirection) {
            if (gestureState.swipeDirection === 'left') {
                navigateToImage('next');
            } else if (gestureState.swipeDirection === 'right') {
                navigateToImage('previous');
            }
        }
    }, [gestureState.swipeDirection, navigateToImage]);

    // Tool functions
    const toggleTool = (toolName) => {
        setActiveTools(prev => ({
            ...Object.keys(prev).reduce((acc, key) => ({ ...acc, [key]: false }), {}),
            [toolName]: !prev[toolName]
        }));
    };

    const addMeasurementPoint = (x, y) => {
        const rect = viewportRef.current.getBoundingClientRect();
        const relativeX = (x - rect.left) / rect.width;
        const relativeY = (y - rect.top) / rect.height;
        
        const newMeasurement = {
            id: Date.now(),
            type: 'point',
            x: relativeX,
            y: relativeY,
            timestamp: new Date().toISOString()
        };
        
        setMeasurements(prev => [...prev, newMeasurement]);
        onMeasurement?.(newMeasurement);
    };

    const showContextMenu = (x, y) => {
        // Implementation for context menu
        console.log('Context menu at:', x, y);
    };

    // Render image with transformations
    const imageStyle = {
        transform: `
            scale(${viewportState.zoom}) 
            translate(${viewportState.pan.x}px, ${viewportState.pan.y}px) 
            rotate(${viewportState.rotation}deg)
        `,
        filter: `
            brightness(${viewportState.windowLevel.center / 100}) 
            contrast(${viewportState.windowLevel.width / 100})
            ${viewportState.invert ? 'invert(1)' : ''}
        `,
        transformOrigin: 'center center',
        transition: gestureState.isGesturing ? 'none' : 'transform 0.2s ease-out'
    };

    return (
        <div className="touch-dicom-viewer">
            {/* Mobile Toolbar */}
            <div className="mobile-toolbar">
                <div className="toolbar-section">
                    <button 
                        className={`tool-btn ${activeTools.pan ? 'active' : ''}`}
                        onClick={() => toggleTool('pan')}
                        aria-label="Pan tool"
                    >
                        🤚
                    </button>
                    <button 
                        className={`tool-btn ${activeTools.zoom ? 'active' : ''}`}
                        onClick={() => toggleTool('zoom')}
                        aria-label="Zoom tool"
                    >
                        🔍
                    </button>
                    <button 
                        className={`tool-btn ${activeTools.windowLevel ? 'active' : ''}`}
                        onClick={() => toggleTool('windowLevel')}
                        aria-label="Window/Level tool"
                    >
                        🌓
                    </button>
                    <button 
                        className={`tool-btn ${activeTools.measurement ? 'active' : ''}`}
                        onClick={() => toggleTool('measurement')}
                        aria-label="Measurement tool"
                    >
                        📏
                    </button>
                </div>
                
                <div className="toolbar-section">
                    <button 
                        className="tool-btn"
                        onClick={() => setViewportState(prev => ({ ...prev, rotation: prev.rotation + 90 }))}
                        aria-label="Rotate"
                    >
                        🔄
                    </button>
                    <button 
                        className="tool-btn"
                        onClick={() => setViewportState(prev => ({ ...prev, invert: !prev.invert }))}
                        aria-label="Invert"
                    >
                        ⚫⚪
                    </button>
                </div>
            </div>

            {/* Viewport */}
            <div 
                ref={viewportRef}
                className="dicom-viewport gesture-area"
                onTouchStart={onTouchStart}
                onTouchMove={onTouchMove}
                onTouchEnd={onTouchEnd}
                style={{ touchAction: 'none' }}
            >
                {isLoading && (
                    <div className="loading-overlay">
                        <div className="loading-spinner"></div>
                        <div className="loading-text">Loading image...</div>
                    </div>
                )}
                
                {imageData && imageData[currentImageIndex] && (
                    <img
                        ref={imageRef}
                        src={imageData[currentImageIndex].url}
                        alt="DICOM Image"
                        className="dicom-image"
                        style={imageStyle}
                        draggable={false}
                    />
                )}

                {/* Measurements overlay */}
                <div className="measurements-overlay">
                    {measurements.map(measurement => (
                        <div
                            key={measurement.id}
                            className="measurement-point"
                            style={{
                                left: `${measurement.x * 100}%`,
                                top: `${measurement.y * 100}%`
                            }}
                        >
                            <div className="measurement-marker"></div>
                        </div>
                    ))}
                </div>

                {/* Offline indicator */}
                {isOffline && (
                    <div className="offline-badge">
                        📡 Offline
                    </div>
                )}
            </div>

            {/* Navigation Controls */}
            <div className="navigation-controls">
                <button 
                    className="nav-btn prev"
                    onClick={() => navigateToImage('previous')}
                    disabled={currentImageIndex === 0}
                    aria-label="Previous image"
                >
                    ◀
                </button>
                
                <div className="image-counter">
                    {currentImageIndex + 1} / {imageData?.length || 0}
                </div>
                
                <button 
                    className="nav-btn next"
                    onClick={() => navigateToImage('next')}
                    disabled={currentImageIndex === (imageData?.length || 1) - 1}
                    aria-label="Next image"
                >
                    ▶
                </button>
            </div>

            {/* Quick Actions FAB */}
            <div className="fab-menu">
                <button className="fab" aria-label="Quick actions">
                    ⚡
                </button>
                <div className="fab-items">
                    <button className="fab-item" aria-label="Reset view">🏠</button>
                    <button className="fab-item" aria-label="Fit to screen">📐</button>
                    <button className="fab-item" aria-label="Share">📤</button>
                </div>
            </div>

            {/* South African Context */}
            {deviceInfo.isLowBandwidth && (
                <div className="bandwidth-warning">
                    ⚠️ Low bandwidth detected - using optimized images
                </div>
            )}
        </div>
    );
};

export default TouchDicomViewer;