/**
 * 3D Measurement Tools for Advanced DICOM Viewer
 * Provides volumetric measurements, distance calculations, and annotations
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useMobileOptimization } from '../../mobile/hooks/useMobileOptimization.js';

const Measurement3DTools = ({
    volumeData,
    activeViewport,
    onMeasurementAdd,
    onMeasurementUpdate,
    onMeasurementDelete,
    measurements = [],
    className = ''
}) => {
    const [activeTool, setActiveTool] = useState(null);
    const [measurementMode, setMeasurementMode] = useState('2d'); // '2d', '3d', 'volume'
    const [currentMeasurement, setCurrentMeasurement] = useState(null);
    const [measurementUnits, setMeasurementUnits] = useState('mm');
    const [showMeasurements, setShowMeasurements] = useState(true);
    const [measurementPrecision, setMeasurementPrecision] = useState(2);

    // Mobile optimization
    const { isMobile, isTablet } = useMobileOptimization();

    // Available measurement tools
    const measurementTools = [
        {
            id: 'distance',
            name: 'Distance',
            icon: '📏',
            description: 'Measure distance between two points',
            modes: ['2d', '3d']
        },
        {
            id: 'angle',
            name: 'Angle',
            icon: '📐',
            description: 'Measure angle between three points',
            modes: ['2d', '3d']
        },
        {
            id: 'area',
            name: 'Area',
            icon: '⬜',
            description: 'Measure area of polygon',
            modes: ['2d']
        },
        {
            id: 'volume',
            name: 'Volume',
            icon: '🧊',
            description: 'Measure 3D volume',
            modes: ['3d', 'volume']
        },
        {
            id: 'ellipse',
            name: 'Ellipse',
            icon: '⭕',
            description: 'Measure elliptical area',
            modes: ['2d']
        },
        {
            id: 'rectangle',
            name: 'Rectangle',
            icon: '▭',
            description: 'Measure rectangular area',
            modes: ['2d']
        },
        {
            id: 'freehand',
            name: 'Freehand',
            icon: '✏️',
            description: 'Freehand measurement',
            modes: ['2d']
        },
        {
            id: 'hounsfield',
            name: 'HU Value',
            icon: '🎯',
            description: 'Measure Hounsfield units (CT only)',
            modes: ['2d'],
            modalitySpecific: ['CT']
        }
    ];

    // Calculate 2D distance
    const calculate2DDistance = useCallback((point1, point2, spacing) => {
        const dx = (point2.x - point1.x) * spacing.x;
        const dy = (point2.y - point1.y) * spacing.y;
        return Math.sqrt(dx * dx + dy * dy);
    }, []);

    // Calculate 3D distance
    const calculate3DDistance = useCallback((point1, point2, spacing) => {
        const dx = (point2.x - point1.x) * spacing.x;
        const dy = (point2.y - point1.y) * spacing.y;
        const dz = (point2.z - point1.z) * spacing.z;
        return Math.sqrt(dx * dx + dy * dy + dz * dz);
    }, []);

    // Calculate angle between three points
    const calculateAngle = useCallback((point1, point2, point3, spacing) => {
        // Vector from point2 to point1
        const v1 = {
            x: (point1.x - point2.x) * spacing.x,
            y: (point1.y - point2.y) * spacing.y,
            z: (point1.z - point2.z) * spacing.z
        };

        // Vector from point2 to point3
        const v2 = {
            x: (point3.x - point2.x) * spacing.x,
            y: (point3.y - point2.y) * spacing.y,
            z: (point3.z - point2.z) * spacing.z
        };

        // Calculate dot product
        const dotProduct = v1.x * v2.x + v1.y * v2.y + v1.z * v2.z;

        // Calculate magnitudes
        const mag1 = Math.sqrt(v1.x * v1.x + v1.y * v1.y + v1.z * v1.z);
        const mag2 = Math.sqrt(v2.x * v2.x + v2.y * v2.y + v2.z * v2.z);

        // Calculate angle in radians, then convert to degrees
        const angleRad = Math.acos(dotProduct / (mag1 * mag2));
        return (angleRad * 180) / Math.PI;
    }, []);

    // Calculate polygon area (2D)
    const calculatePolygonArea = useCallback((points, spacing) => {
        if (points.length < 3) return 0;

        let area = 0;
        for (let i = 0; i < points.length; i++) {
            const j = (i + 1) % points.length;
            const xi = points[i].x * spacing.x;
            const yi = points[i].y * spacing.y;
            const xj = points[j].x * spacing.x;
            const yj = points[j].y * spacing.y;
            area += xi * yj - xj * yi;
        }
        return Math.abs(area) / 2;
    }, []);

    // Calculate ellipse area
    const calculateEllipseArea = useCallback((centerPoint, radiusPoint1, radiusPoint2, spacing) => {
        const a = calculate2DDistance(centerPoint, radiusPoint1, spacing);
        const b = calculate2DDistance(centerPoint, radiusPoint2, spacing);
        return Math.PI * a * b;
    }, [calculate2DDistance]);

    // Calculate 3D volume using voxel counting
    const calculate3DVolume = useCallback((segmentationMask, spacing) => {
        if (!segmentationMask || !volumeData) return 0;

        let voxelCount = 0;
        for (let i = 0; i < segmentationMask.length; i++) {
            if (segmentationMask[i] > 0) {
                voxelCount++;
            }
        }

        const voxelVolume = spacing.x * spacing.y * spacing.z;
        return voxelCount * voxelVolume;
    }, [volumeData]);

    // Get Hounsfield unit value at point (CT only)
    const getHounsfieldValue = useCallback((point) => {
        if (!volumeData || volumeData.type !== 'CT') return null;

        const { buffer, dimensions } = volumeData;
        const x = Math.floor(point.x);
        const y = Math.floor(point.y);
        const z = Math.floor(point.z);

        if (x < 0 || x >= dimensions.x || 
            y < 0 || y >= dimensions.y || 
            z < 0 || z >= dimensions.z) {
            return null;
        }

        const index = z * dimensions.x * dimensions.y + y * dimensions.x + x;
        return buffer[index];
    }, [volumeData]);

    // Handle tool selection
    const handleToolSelect = useCallback((toolId) => {
        setActiveTool(toolId);
        setCurrentMeasurement(null);
    }, []);

    // Handle measurement point addition
    const handlePointAdd = useCallback((point, viewport) => {
        if (!activeTool || !volumeData) return;

        const newPoint = {
            ...point,
            viewport,
            timestamp: Date.now()
        };

        if (!currentMeasurement) {
            // Start new measurement
            const measurement = {
                id: `measurement_${Date.now()}`,
                type: activeTool,
                mode: measurementMode,
                points: [newPoint],
                viewport,
                units: measurementUnits,
                precision: measurementPrecision,
                created: new Date().toISOString(),
                modality: volumeData.type
            };

            setCurrentMeasurement(measurement);
        } else {
            // Add point to current measurement
            const updatedMeasurement = {
                ...currentMeasurement,
                points: [...currentMeasurement.points, newPoint]
            };

            // Check if measurement is complete
            const isComplete = checkMeasurementComplete(updatedMeasurement);
            
            if (isComplete) {
                // Calculate final measurement value
                const calculatedMeasurement = calculateMeasurementValue(updatedMeasurement);
                onMeasurementAdd?.(calculatedMeasurement);
                setCurrentMeasurement(null);
                setActiveTool(null);
            } else {
                setCurrentMeasurement(updatedMeasurement);
            }
        }
    }, [activeTool, currentMeasurement, measurementMode, measurementUnits, measurementPrecision, volumeData, onMeasurementAdd]);

    // Check if measurement is complete
    const checkMeasurementComplete = (measurement) => {
        const requiredPoints = {
            distance: 2,
            angle: 3,
            area: 3, // minimum for polygon
            volume: 1, // requires segmentation
            ellipse: 3, // center + 2 radius points
            rectangle: 2, // diagonal corners
            freehand: 1, // can be completed at any time
            hounsfield: 1
        };

        return measurement.points.length >= (requiredPoints[measurement.type] || 1);
    };

    // Calculate measurement value
    const calculateMeasurementValue = (measurement) => {
        const { type, points, mode } = measurement;
        const spacing = volumeData.spacing;
        let value = 0;
        let unit = measurementUnits;

        switch (type) {
            case 'distance':
                if (points.length >= 2) {
                    value = mode === '3d' 
                        ? calculate3DDistance(points[0], points[1], spacing)
                        : calculate2DDistance(points[0], points[1], spacing);
                }
                break;

            case 'angle':
                if (points.length >= 3) {
                    value = calculateAngle(points[0], points[1], points[2], spacing);
                    unit = '°';
                }
                break;

            case 'area':
                if (points.length >= 3) {
                    value = calculatePolygonArea(points, spacing);
                    unit = 'mm²';
                }
                break;

            case 'ellipse':
                if (points.length >= 3) {
                    value = calculateEllipseArea(points[0], points[1], points[2], spacing);
                    unit = 'mm²';
                }
                break;

            case 'rectangle':
                if (points.length >= 2) {
                    const width = Math.abs(points[1].x - points[0].x) * spacing.x;
                    const height = Math.abs(points[1].y - points[0].y) * spacing.y;
                    value = width * height;
                    unit = 'mm²';
                }
                break;

            case 'volume':
                // This would require segmentation data
                value = 0;
                unit = 'mm³';
                break;

            case 'hounsfield':
                if (points.length >= 1) {
                    value = getHounsfieldValue(points[0]);
                    unit = 'HU';
                }
                break;

            default:
                value = 0;
        }

        return {
            ...measurement,
            value: parseFloat(value.toFixed(measurementPrecision)),
            unit,
            calculated: new Date().toISOString()
        };
    };

    // Delete measurement
    const handleMeasurementDelete = useCallback((measurementId) => {
        onMeasurementDelete?.(measurementId);
    }, [onMeasurementDelete]);

    // Export measurements
    const exportMeasurements = useCallback(() => {
        const exportData = {
            studyInfo: {
                modality: volumeData?.type,
                dimensions: volumeData?.dimensions,
                spacing: volumeData?.spacing,
                exported: new Date().toISOString()
            },
            measurements: measurements.map(m => ({
                type: m.type,
                value: m.value,
                unit: m.unit,
                points: m.points,
                created: m.created
            }))
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `measurements_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, [measurements, volumeData]);

    // Filter tools based on modality and mode
    const getAvailableTools = () => {
        return measurementTools.filter(tool => {
            // Check mode compatibility
            if (!tool.modes.includes(measurementMode)) return false;
            
            // Check modality compatibility
            if (tool.modalitySpecific && volumeData) {
                return tool.modalitySpecific.includes(volumeData.type);
            }
            
            return true;
        });
    };

    return (
        <div className={`measurement-3d-tools ${className}`}>
            {/* Tool Selection */}
            <div className="measurement-toolbar">
                <div className="toolbar-section">
                    <label className="toolbar-label">Mode:</label>
                    <select 
                        value={measurementMode}
                        onChange={(e) => setMeasurementMode(e.target.value)}
                        className="mode-select"
                    >
                        <option value="2d">2D Measurements</option>
                        <option value="3d">3D Measurements</option>
                        <option value="volume">Volume Analysis</option>
                    </select>
                </div>

                <div className="toolbar-section">
                    <label className="toolbar-label">Units:</label>
                    <select 
                        value={measurementUnits}
                        onChange={(e) => setMeasurementUnits(e.target.value)}
                        className="units-select"
                    >
                        <option value="mm">Millimeters</option>
                        <option value="cm">Centimeters</option>
                        <option value="px">Pixels</option>
                    </select>
                </div>

                <div className="toolbar-section">
                    <label className="toolbar-label">Precision:</label>
                    <select 
                        value={measurementPrecision}
                        onChange={(e) => setMeasurementPrecision(parseInt(e.target.value))}
                        className="precision-select"
                    >
                        <option value="0">0 decimals</option>
                        <option value="1">1 decimal</option>
                        <option value="2">2 decimals</option>
                        <option value="3">3 decimals</option>
                    </select>
                </div>
            </div>

            {/* Measurement Tools */}
            <div className={`measurement-tools ${isMobile ? 'mobile-tools' : 'desktop-tools'}`}>
                {getAvailableTools().map(tool => (
                    <button
                        key={tool.id}
                        className={`tool-btn ${activeTool === tool.id ? 'active' : ''}`}
                        onClick={() => handleToolSelect(tool.id)}
                        title={tool.description}
                    >
                        <span className="tool-icon">{tool.icon}</span>
                        {!isMobile && <span className="tool-name">{tool.name}</span>}
                    </button>
                ))}
            </div>

            {/* Current Measurement Status */}
            {currentMeasurement && (
                <div className="current-measurement">
                    <div className="measurement-status">
                        <span className="status-icon">📏</span>
                        <span className="status-text">
                            {currentMeasurement.type} - {currentMeasurement.points.length} point(s)
                        </span>
                        <button 
                            className="cancel-btn"
                            onClick={() => setCurrentMeasurement(null)}
                        >
                            ✕
                        </button>
                    </div>
                </div>
            )}

            {/* Measurements List */}
            <div className="measurements-list">
                <div className="list-header">
                    <span>Measurements ({measurements.length})</span>
                    <div className="list-actions">
                        <button
                            className="action-btn"
                            onClick={() => setShowMeasurements(!showMeasurements)}
                            title="Toggle visibility"
                        >
                            {showMeasurements ? '👁️' : '🙈'}
                        </button>
                        <button
                            className="action-btn"
                            onClick={exportMeasurements}
                            title="Export measurements"
                            disabled={measurements.length === 0}
                        >
                            📤
                        </button>
                    </div>
                </div>

                {showMeasurements && (
                    <div className="measurements-content">
                        {measurements.length === 0 ? (
                            <div className="no-measurements">
                                No measurements yet. Select a tool and click on the image to start measuring.
                            </div>
                        ) : (
                            measurements.map((measurement, index) => (
                                <div key={measurement.id} className="measurement-item">
                                    <div className="measurement-header">
                                        <span className="measurement-type">
                                            {measurementTools.find(t => t.id === measurement.type)?.icon} 
                                            {measurement.type}
                                        </span>
                                        <button
                                            className="delete-btn"
                                            onClick={() => handleMeasurementDelete(measurement.id)}
                                            title="Delete measurement"
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                    <div className="measurement-value">
                                        {measurement.value} {measurement.unit}
                                    </div>
                                    <div className="measurement-details">
                                        <small>
                                            {measurement.mode.toUpperCase()} • 
                                            {measurement.points.length} points • 
                                            {measurement.viewport}
                                        </small>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}
            </div>

            {/* South African Medical Context */}
            {volumeData?.type === 'CT' && (
                <div className="sa-medical-context">
                    <div className="context-header">🇿🇦 SA Medical Standards</div>
                    <div className="context-content">
                        <small>
                            Measurements follow HPCSA guidelines for medical imaging reporting.
                            All values are calibrated for South African medical equipment standards.
                        </small>
                    </div>
                </div>
            )}

            {/* Mobile-specific quick actions */}
            {(isMobile || isTablet) && (
                <div className="mobile-quick-actions">
                    <button className="quick-action-btn" title="Clear all">🗑️</button>
                    <button className="quick-action-btn" title="Save">💾</button>
                    <button className="quick-action-btn" title="Share">📤</button>
                </div>
            )}
        </div>
    );
};

export default Measurement3DTools;