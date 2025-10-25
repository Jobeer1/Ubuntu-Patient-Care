/**
 * OHIF-Based Web Viewer for Referring Doctors
 * Optimized for South African healthcare networks and workflows
 */

import React, { useEffect, useState, useRef } from 'react';
import { OHIFViewer } from '@ohif/viewer';
import { useMobileOptimization } from '../../frontend/mobile/hooks/useMobileOptimization.js';

const ReferringDoctorViewer = ({
    studyInstanceUID,
    seriesInstanceUID,
    secureToken,
    referringDoctorInfo,
    reportData,
    onViewingComplete,
    className = ''
}) => {
    const viewerRef = useRef(null);
    const [isLoading, setIsLoading] = useState(true);
    const [viewerConfig, setViewerConfig] = useState(null);
    const [error, setError] = useState(null);
    const [viewingSession, setViewingSession] = useState(null);

    // Mobile optimization for SA networks
    const { 
        isMobile, 
        isTablet, 
        isLowBandwidth, 
        isOffline,
        formatSADate,
        formatSAPhoneNumber 
    } = useMobileOptimization();

    // Initialize OHIF viewer with SA optimizations
    useEffect(() => {
        const initializeViewer = async () => {
            try {
                setIsLoading(true);

                // Create SA-optimized OHIF configuration
                const config = createSAOptimizedConfig();
                
                // Set up data sources for secure access
                const dataSources = await setupSecureDataSources();
                
                // Configure viewer for referring doctor workflow
                const viewerConfiguration = {
                    ...config,
                    dataSources,
                    studyInstanceUIDs: [studyInstanceUID],
                    seriesInstanceUID,
                    // SA-specific settings
                    saOptimizations: {
                        lowBandwidth: isLowBandwidth,
                        mobileDevice: isMobile || isTablet,
                        offlineMode: isOffline,
                        referringDoctor: true
                    }
                };

                setViewerConfig(viewerConfiguration);
                
                // Track viewing session for audit
                const session = {
                    sessionId: `ref_${Date.now()}`,
                    doctorInfo: referringDoctorInfo,
                    studyUID: studyInstanceUID,
                    startTime: new Date().toISOString(),
                    ipAddress: await getUserIP(),
                    userAgent: navigator.userAgent
                };
                
                setViewingSession(session);
                await logViewingSession(session);

            } catch (error) {
                console.error('Failed to initialize referring doctor viewer:', error);
                setError(`Viewer initialization failed: ${error.message}`);
            } finally {
                setIsLoading(false);
            }
        };

        if (studyInstanceUID && secureToken) {
            initializeViewer();
        }
    }, [studyInstanceUID, secureToken, isLowBandwidth, isMobile, isTablet, isOffline]);

    // Create SA-optimized OHIF configuration
    const createSAOptimizedConfig = () => {
        return {
            routerBasename: '/referring-viewer',
            showStudyList: false, // Simplified for referring doctors
            maxNumberOfWebWorkers: isLowBandwidth ? 2 : 4,
            showWarningMessageForCrossOrigin: false,
            showCPUFallbackMessage: false,
            strictZSpacingForVolumeViewport: false,
            
            // SA Medical Standards
            defaultViewportOptions: {
                viewportType: 'stack',
                toolGroupId: 'referring-doctor-tools',
                initialImageOptions: {
                    preset: 'first'
                },
                // Optimized for SA networks
                imageRendering: isLowBandwidth ? 'pixelated' : 'auto',
                imageQuality: isLowBandwidth ? 'medium' : 'high'
            },

            // Simplified toolbar for referring doctors
            cornerstoneExtensionConfig: {
                tools: {
                    enabled: [
                        'WindowLevel',
                        'Pan',
                        'Zoom',
                        'StackScrollMouseWheel',
                        'Magnify',
                        'Length',
                        'Angle',
                        'Rectangle'
                    ],
                    disabled: [
                        'Crosshairs', // Too complex for referring doctors
                        'ReferenceLines',
                        'SegmentationDisplay'
                    ]
                }
            },

            // SA Language support
            i18n: {
                lng: 'en-ZA', // South African English
                fallbackLng: 'en',
                debug: false,
                resources: {
                    'en-ZA': {
                        translation: {
                            'Study Date': 'Study Date',
                            'Patient Name': 'Patient Name',
                            'Patient ID': 'Patient ID',
                            'Modality': 'Modality',
                            'Series Description': 'Series Description',
                            'Referring Physician': 'Referring Physician',
                            'Institution': 'Institution'
                        }
                    }
                }
            },

            // Mobile optimizations
            ...(isMobile || isTablet) && {
                viewport: {
                    // Touch-friendly settings
                    interactionType: 'touch',
                    gestureSettings: {
                        pinchToZoom: true,
                        panGesture: true,
                        doubleTapZoom: true
                    }
                }
            }
        };
    };

    // Setup secure data sources with token authentication
    const setupSecureDataSources = async () => {
        const baseURL = window.location.origin;
        
        return [
            {
                sourceName: 'sa-medical-dicomweb',
                type: 'dicomweb',
                wadoUriRoot: `${baseURL}/api/secure-dicom/wado`,
                qidoRoot: `${baseURL}/api/secure-dicom/qido`,
                wadoRoot: `${baseURL}/api/secure-dicom/wado`,
                
                // SA-specific authentication
                requestOptions: {
                    headers: {
                        'Authorization': `Bearer ${secureToken}`,
                        'X-SA-Referring-Doctor': 'true',
                        'X-SA-Session-ID': viewingSession?.sessionId,
                        'X-SA-Network-Type': isLowBandwidth ? 'low-bandwidth' : 'standard'
                    },
                    // Network optimizations for SA
                    timeout: isLowBandwidth ? 30000 : 15000,
                    retries: 3,
                    retryDelay: 2000
                },

                // Image loading optimizations
                imageRendering: {
                    thumbnailType: isLowBandwidth ? 'image/jpeg' : 'image/png',
                    preferSizeOverQuality: isLowBandwidth,
                    progressive: true
                }
            }
        ];
    };

    // Log viewing session for audit compliance
    const logViewingSession = async (session) => {
        try {
            await fetch('/api/audit/referring-doctor-access', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${secureToken}`
                },
                body: JSON.stringify({
                    ...session,
                    studyUID: studyInstanceUID,
                    accessType: 'referring-doctor-web-viewer',
                    saCompliance: true
                })
            });
        } catch (error) {
            console.warn('Failed to log viewing session:', error);
        }
    };

    // Get user IP for audit logging
    const getUserIP = async () => {
        try {
            const response = await fetch('/api/utils/client-ip');
            const data = await response.json();
            return data.ip;
        } catch (error) {
            return 'unknown';
        }
    };

    // Handle viewer events
    const handleViewerEvent = (event) => {
        switch (event.type) {
            case 'STUDY_LOADED':
                console.log('Study loaded for referring doctor');
                break;
            case 'MEASUREMENT_ADDED':
                // Log measurements made by referring doctor
                logReferringDoctorMeasurement(event.data);
                break;
            case 'VIEWPORT_CHANGED':
                // Track which images are being viewed
                logImageViewing(event.data);
                break;
        }
    };

    // Log measurements made by referring doctors
    const logReferringDoctorMeasurement = async (measurementData) => {
        try {
            await fetch('/api/audit/referring-doctor-measurement', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${secureToken}`
                },
                body: JSON.stringify({
                    sessionId: viewingSession?.sessionId,
                    doctorInfo: referringDoctorInfo,
                    measurement: measurementData,
                    timestamp: new Date().toISOString()
                })
            });
        } catch (error) {
            console.warn('Failed to log referring doctor measurement:', error);
        }
    };

    // Render loading state
    if (isLoading) {
        return (
            <div className="referring-doctor-viewer-loading">
                <div className="loading-content">
                    <div className="sa-medical-logo">🇿🇦 SA Medical Imaging</div>
                    <div className="loading-spinner"></div>
                    <div className="loading-text">
                        Loading study for referring doctor review...
                    </div>
                    {isLowBandwidth && (
                        <div className="network-notice">
                            📶 Optimizing for your network connection
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Render error state
    if (error) {
        return (
            <div className="referring-doctor-viewer-error">
                <div className="error-content">
                    <div className="error-icon">⚠️</div>
                    <div className="error-title">Unable to Load Study</div>
                    <div className="error-message">{error}</div>
                    <div className="error-actions">
                        <button 
                            className="retry-btn"
                            onClick={() => window.location.reload()}
                        >
                            Retry
                        </button>
                        <button 
                            className="contact-btn"
                            onClick={() => window.open('tel:+27-11-xxx-xxxx')}
                        >
                            Contact Support
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className={`referring-doctor-viewer ${className}`}>
            {/* SA Medical Header */}
            <div className="sa-medical-header">
                <div className="header-left">
                    <div className="sa-flag">🇿🇦</div>
                    <div className="system-title">SA Medical Imaging</div>
                    <div className="viewer-type">Referring Doctor Portal</div>
                </div>
                <div className="header-right">
                    <div className="doctor-info">
                        <div className="doctor-name">{referringDoctorInfo?.name}</div>
                        <div className="practice-info">{referringDoctorInfo?.practice}</div>
                    </div>
                    {isLowBandwidth && (
                        <div className="network-indicator">📶 Low Bandwidth</div>
                    )}
                </div>
            </div>

            {/* Patient Information Panel */}
            <div className="patient-info-panel">
                <div className="patient-details">
                    <div className="detail-item">
                        <span className="label">Patient:</span>
                        <span className="value">{reportData?.patientName || 'Loading...'}</span>
                    </div>
                    <div className="detail-item">
                        <span className="label">Study Date:</span>
                        <span className="value">
                            {reportData?.studyDate ? formatSADate(reportData.studyDate) : 'Loading...'}
                        </span>
                    </div>
                    <div className="detail-item">
                        <span className="label">Modality:</span>
                        <span className="value">{reportData?.modality || 'Loading...'}</span>
                    </div>
                </div>
                
                {/* Quick Actions for Referring Doctors */}
                <div className="quick-actions">
                    <button className="action-btn" title="Print Images">🖨️</button>
                    <button className="action-btn" title="Download Report">📄</button>
                    <button className="action-btn" title="Share with Patient">👤</button>
                    <button className="action-btn" title="Contact Radiologist">📞</button>
                </div>
            </div>

            {/* OHIF Viewer Container */}
            <div className="ohif-viewer-container">
                {viewerConfig && (
                    <OHIFViewer
                        ref={viewerRef}
                        config={viewerConfig}
                        onEvent={handleViewerEvent}
                        className="sa-optimized-ohif"
                    />
                )}
            </div>

            {/* Report Panel */}
            {reportData && (
                <div className="report-panel">
                    <div className="report-header">
                        <h3>Radiology Report</h3>
                        <div className="report-date">
                            {formatSADate(reportData.reportDate)}
                        </div>
                    </div>
                    <div className="report-content">
                        <div className="report-section">
                            <h4>Clinical History</h4>
                            <p>{reportData.clinicalHistory}</p>
                        </div>
                        <div className="report-section">
                            <h4>Findings</h4>
                            <p>{reportData.findings}</p>
                        </div>
                        <div className="report-section">
                            <h4>Impression</h4>
                            <p>{reportData.impression}</p>
                        </div>
                        <div className="report-footer">
                            <div className="radiologist-info">
                                <strong>Reported by:</strong> {reportData.radiologistName}<br/>
                                <strong>HPCSA Number:</strong> {reportData.hpcsaNumber}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* SA Compliance Footer */}
            <div className="sa-compliance-footer">
                <div className="compliance-text">
                    This system complies with POPIA and HPCSA regulations for medical imaging in South Africa
                </div>
                <div className="session-info">
                    Session: {viewingSession?.sessionId} | 
                    Started: {viewingSession?.startTime ? formatSADate(viewingSession.startTime) : ''}
                </div>
            </div>

            {/* Mobile-specific controls */}
            {(isMobile || isTablet) && (
                <div className="mobile-referring-controls">
                    <button className="mobile-control">🔍 Zoom</button>
                    <button className="mobile-control">📏 Measure</button>
                    <button className="mobile-control">📄 Report</button>
                    <button className="mobile-control">📞 Call</button>
                </div>
            )}
        </div>
    );
};

export default ReferringDoctorViewer;