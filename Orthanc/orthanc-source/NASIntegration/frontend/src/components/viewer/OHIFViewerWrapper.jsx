import React, { useState, useEffect, useCallback } from 'react';
import { Maximize2, Minimize2, RotateCw, ZoomIn, ZoomOut, Move, Square } from 'lucide-react';
import unifiedAPI from '../../utils/unifiedAPI';

/**
 * OHIF Viewer Integration for SA Healthcare
 * Developer B - Phase 2 OHIF Integration
 * 
 * Features:
 * - Embedded OHIF viewer
 * - SA-specific configurations
 * - Mobile optimization for SA networks
 * - Multi-language interface integration
 * - Voice dictation integration
 */

const OHIFViewerWrapper = ({ 
  studyInstanceUID, 
  seriesInstanceUID = null,
  className = "",
  onStudyLoad = null,
  saConfig = {} 
}) => {
  const [viewerLoaded, setViewerLoaded] = useState(false);
  const [studyData, setStudyData] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // SA-specific configuration
  const defaultSAConfig = {
    language: 'en', // Will be updated from user preferences
    enableVoiceDictation: true,
    mobileOptimized: true,
    loadSheddingMode: false,
    showSAMetadata: true,
    medicalAidDisplay: true,
    hpcsaValidation: true,
    ...saConfig
  };

  // Load study data with SA metadata
  const loadStudyData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await unifiedAPI.getStudyWithSAMetadata(studyInstanceUID);
      setStudyData(response.data);
      
      if (onStudyLoad) {
        onStudyLoad(response.data);
      }
      
    } catch (err) {
      console.error('Error loading study data:', err);
      setError('Failed to load study data');
    } finally {
      setLoading(false);
    }
  }, [studyInstanceUID, onStudyLoad]);

  // Initialize OHIF viewer
  useEffect(() => {
    loadStudyData();
  }, [loadStudyData]);

  // OHIF configuration for SA healthcare
  const getOHIFConfig = useCallback(() => {
    return {
      routerBasename: '/',
      whiteLabeling: {
        createLogoComponentFn: () => {
          return React.createElement('div', {
            style: { 
              display: 'flex', 
              alignItems: 'center', 
              fontSize: '18px', 
              fontWeight: 'bold',
              color: '#2563eb'
            }
          }, 'Orthanc SA PACS');
        },
      },
      extensions: [],
      modes: ['@ohif/mode-longitudinal'],
      customizationService: {
        // SA-specific customizations
        dicomUploadComponent: null,
        cornerstoneExtensionConfig: {
          tools: {
            // Enable touch tools for mobile SA devices
            PanTool: { configuration: { touchEnabled: true } },
            ZoomTool: { configuration: { touchEnabled: true } },
            WindowLevelTool: { configuration: { touchEnabled: true } }
          }
        }
      },
      defaultDataSourceName: 'orthancDICOMWeb',
      dataSources: [
        {
          namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
          sourceName: 'orthancDICOMWeb',
          configuration: {
            friendlyName: 'Orthanc SA DICOM Server',
            name: 'orthanc',
            wadoUriRoot: '/orthanc/wado',
            qidoRoot: '/orthanc/dicom-web',
            wadoRoot: '/orthanc/dicom-web',
            qidoSupportsIncludeField: false,
            supportsReject: true,
            imageRendering: 'wadors',
            thumbnailRendering: 'wadors',
            enableStudyLazyLoad: true,
            supportsFuzzyMatching: false,
            supportsWildcard: true,
            staticWado: true,
            singlepart: 'bulkdata,video,pdf',
            // SA-specific optimizations
            requestOptions: {
              requestTimeout: defaultSAConfig.loadSheddingMode ? 60000 : 30000,
              retryDelay: 1000,
              maxRetries: defaultSAConfig.loadSheddingMode ? 5 : 3
            }
          },
        },
      ],
      showStudyList: false,
      // SA language configuration
      i18n: {
        lng: defaultSAConfig.language,
        fallbackLng: 'en',
        debug: false,
        interpolation: {
          escapeValue: false
        }
      }
    };
  }, [defaultSAConfig]);

  // Handle fullscreen toggle
  const toggleFullscreen = useCallback(() => {
    if (!isFullscreen) {
      const element = document.getElementById('ohif-viewer-container');
      if (element.requestFullscreen) {
        element.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
    setIsFullscreen(!isFullscreen);
  }, [isFullscreen]);

  // Toolbar component for SA-specific tools
  const SAToolbar = () => (
    <div className="flex items-center gap-2 p-2 bg-gray-800 text-white">
      {/* Standard DICOM tools */}
      <button 
        className="p-2 hover:bg-gray-700 rounded"
        title="Pan Tool"
      >
        <Move className="w-4 h-4" />
      </button>
      
      <button 
        className="p-2 hover:bg-gray-700 rounded"
        title="Zoom In"
      >
        <ZoomIn className="w-4 h-4" />
      </button>
      
      <button 
        className="p-2 hover:bg-gray-700 rounded"
        title="Zoom Out"
      >
        <ZoomOut className="w-4 h-4" />
      </button>
      
      <button 
        className="p-2 hover:bg-gray-700 rounded"
        title="Rotate"
      >
        <RotateCw className="w-4 h-4" />
      </button>

      <div className="h-6 w-px bg-gray-600 mx-2" />

      {/* SA-specific tools */}
      {defaultSAConfig.enableVoiceDictation && (
        <button 
          className="p-2 hover:bg-gray-700 rounded text-green-400"
          title="Voice Dictation (SA)"
        >
          🎤
        </button>
      )}

      {defaultSAConfig.showSAMetadata && studyData?.saMetadata && (
        <div className="flex items-center gap-2 text-sm">
          {studyData.saMetadata.medical_aid && (
            <span className="bg-blue-600 px-2 py-1 rounded text-xs">
              {studyData.saMetadata.medical_aid}
            </span>
          )}
          {studyData.saMetadata.hpcsa_ref && (
            <span className="bg-green-600 px-2 py-1 rounded text-xs">
              HPCSA: {studyData.saMetadata.hpcsa_ref}
            </span>
          )}
        </div>
      )}

      <div className="flex-1" />

      {/* Fullscreen toggle */}
      <button 
        onClick={toggleFullscreen}
        className="p-2 hover:bg-gray-700 rounded"
        title={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
      >
        {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
      </button>
    </div>
  );

  // Loading state
  if (loading) {
    return (
      <div className={`flex items-center justify-center min-h-96 bg-black text-white ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p>Loading DICOM Study...</p>
          <p className="text-sm text-gray-400 mt-1">SA Healthcare Viewer</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`flex items-center justify-center min-h-96 bg-red-50 text-red-700 ${className}`}>
        <div className="text-center">
          <Square className="w-12 h-12 mx-auto mb-4 text-red-500" />
          <p className="font-semibold">Failed to Load Study</p>
          <p className="text-sm">{error}</p>
          <button 
            onClick={loadStudyData}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // OHIF Viewer placeholder (will be replaced with actual OHIF integration)
  return (
    <div 
      id="ohif-viewer-container" 
      className={`relative bg-black ${className}`}
      style={{ minHeight: '600px' }}
    >
      <SAToolbar />
      
      <div className="flex-1 bg-black text-white p-8">
        <div className="text-center">
          <h3 className="text-xl font-semibold mb-4">OHIF Viewer Integration</h3>
          <p className="text-gray-400 mb-6">
            Study: {studyInstanceUID}
          </p>
          
          {studyData && (
            <div className="bg-gray-800 rounded-lg p-6 max-w-md mx-auto">
              <h4 className="font-semibold mb-3">Study Information</h4>
              <div className="text-left space-y-2 text-sm">
                <div><span className="text-gray-400">Patient:</span> {studyData.PatientName || 'Unknown'}</div>
                <div><span className="text-gray-400">Study Date:</span> {studyData.StudyDate || 'Unknown'}</div>
                <div><span className="text-gray-400">Modality:</span> {studyData.ModalitiesInStudy || 'Unknown'}</div>
                
                {studyData.saMetadata && (
                  <>
                    <div className="border-t border-gray-600 pt-2 mt-3">
                      <span className="text-blue-400 font-semibold">SA Healthcare Metadata:</span>
                    </div>
                    {studyData.saMetadata.medical_aid && (
                      <div><span className="text-gray-400">Medical Aid:</span> {studyData.saMetadata.medical_aid}</div>
                    )}
                    {studyData.saMetadata.hpcsa_ref && (
                      <div><span className="text-gray-400">HPCSA Ref:</span> {studyData.saMetadata.hpcsa_ref}</div>
                    )}
                    {studyData.saMetadata.language && (
                      <div><span className="text-gray-400">Language:</span> {studyData.saMetadata.language}</div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
          
          <div className="mt-6 text-sm text-gray-500">
            <p>🚧 OHIF Integration In Development</p>
            <p>Phase 2 - Mobile-optimized SA DICOM viewer</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OHIFViewerWrapper;
