/**
 * 🇿🇦 South African Medical Imaging System - DICOM Viewer App
 * 
 * Main application component for the advanced DICOM viewer
 * Tailored for South African healthcare workflows
 */

import React, { useState, useEffect } from 'react';
import { DicomViewerLayout } from './components/layout/DicomViewerLayout';
import { StudyBrowser } from './components/browser/StudyBrowser';
import { ToolPanel } from './components/tools/ToolPanel';
import { ViewportGrid } from './components/viewport/ViewportGrid';
import { StatusBar } from './components/ui/StatusBar';
import { ReportingIntegration } from './components/ReportingIntegration';
import { DicomStudy, LoadingState, LayoutConfig } from './types/dicom';
import { useDicomLoader } from './hooks/useDicomLoader';
import { useSALocalization } from './hooks/useSALocalization';
import { useMeasurements } from './hooks/useMeasurements';
import './App.css';
import './components/components.css';

const App: React.FC = () => {
  // State management
  const [selectedStudy, setSelectedStudy] = useState<DicomStudy | null>(null);
  const [showReporting, setShowReporting] = useState(false);
  const [reportingStudy, setReportingStudy] = useState<DicomStudy | null>(null);
  const [layoutConfig, setLayoutConfig] = useState<LayoutConfig>({
    rows: 1,
    columns: 1,
    viewports: [{}]
  });
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [toolPanelOpen, setToolPanelOpen] = useState(true);
  const [loadingState, setLoadingState] = useState<LoadingState>({
    isLoading: false
  });

  // Custom hooks
  const { studies, loadingState: dicomLoadingState, loadStudies, loadStudy, loadImage } = useDicomLoader();
  const { t, currentLanguage, setLanguage } = useSALocalization();
  const { measurements, addMeasurement, updateMeasurement, removeMeasurement, exportMeasurements } = useMeasurements();

  // Load demo studies on mount
  useEffect(() => {
    loadDemoStudies();
  }, []);

  const loadDemoStudies = async () => {
    setLoadingState({ isLoading: true, message: t('loading.studies') });
    
    try {
      // In a real implementation, this would load from Orthanc or NAS
      // For now, we'll create demo data
      const demoStudies = createDemoStudies();
      
      setTimeout(() => {
        setLoadingState({ isLoading: false });
      }, 1000);
      
    } catch (error) {
      setLoadingState({
        isLoading: false,
        error: {
          code: 'LOAD_ERROR',
          message: t('error.loadStudies'),
          timestamp: new Date().toISOString()
        }
      });
    }
  };

  const createDemoStudies = (): DicomStudy[] => {
    // Demo studies representing common SA medical cases
    return [
      {
        studyInstanceUID: '1.2.3.4.5.6.7.8.9.1',
        studyDate: '2024-01-15',
        studyDescription: 'Chest X-Ray - TB Screening',
        accessionNumber: 'ACC001',
        patientInfo: {
          patientID: 'SA001',
          patientName: 'Patient, Demo',
          patientBirthDate: '1985-03-15',
          patientSex: 'M',
          saIdNumber: '8503155555555',
          medicalAidNumber: 'DH123456789',
          preferredLanguage: 'en'
        },
        series: [
          {
            seriesInstanceUID: '1.2.3.4.5.6.7.8.9.1.1',
            seriesNumber: 1,
            seriesDescription: 'PA View',
            modality: 'CR',
            bodyPartExamined: 'CHEST',
            images: [],
            numberOfImages: 1
          }
        ],
        numberOfSeries: 1,
        medicalAidScheme: 'Discovery Health',
        referringPhysician: 'Dr. Smith',
        institution: 'Johannesburg General Hospital',
        saHealthcareProvider: 'Netcare'
      }
    ];
  };

  const handleStudySelect = (study: DicomStudy) => {
    setSelectedStudy(study);
    setLoadingState({ isLoading: true, message: t('loading.images') });
    
    // Load study images
    loadStudy(study.studyInstanceUID).then(() => {
      setLoadingState({ isLoading: false });
    });
  };

  const handleStartReport = (study: DicomStudy) => {
    console.log('Starting report for study:', study.studyInstanceUID);
    
    // Set the study for reporting and show the integration modal
    setReportingStudy(study);
    setShowReporting(true);
    
    // Also select the study in the viewer
    setSelectedStudy(study);
  };

  const handleLayoutChange = (rows: number, columns: number) => {
    const viewports = Array(rows * columns).fill({});
    setLayoutConfig({ rows, columns, viewports });
  };

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const toggleToolPanel = () => {
    setToolPanelOpen(!toolPanelOpen);
  };

  return (
    <div className="sa-dicom-viewer">
      {/* SA Flag Accent */}
      <div className="sa-accent" />
      
      <DicomViewerLayout
        sidebarOpen={sidebarOpen}
        toolPanelOpen={toolPanelOpen}
        onToggleSidebar={toggleSidebar}
        onToggleToolPanel={toggleToolPanel}
        currentLanguage={currentLanguage}
        onLanguageChange={setLanguage}
      >
        {/* Left Sidebar - Study Browser */}
        {sidebarOpen && (
          <div className="sidebar">
            <StudyBrowser
              studies={studies}
              selectedStudy={selectedStudy}
              onStudySelect={handleStudySelect}
              onStartReport={handleStartReport}
              loadingState={loadingState}
            />
          </div>
        )}

        {/* Main Viewport Area */}
        <div className="main-content">
          <ViewportGrid
            layoutConfig={layoutConfig}
            selectedStudy={selectedStudy}
            onLayoutChange={handleLayoutChange}
          />
        </div>

        {/* Right Tool Panel */}
        {toolPanelOpen && (
          <div className="tool-panel">
            <ToolPanel
              selectedStudy={selectedStudy}
              onMeasurement={addMeasurement}
              onAnnotation={(annotation: any) => console.log('Annotation:', annotation)}
            />
          </div>
        )}
      </DicomViewerLayout>

      {/* Status Bar */}
      <StatusBar
        loadingState={loadingState}
        selectedStudy={selectedStudy}
        layoutConfig={layoutConfig}
      />

      {/* Reporting Integration Modal */}
      {showReporting && reportingStudy && (
        <div className="modal-overlay">
          <div className="modal-content">
            <ReportingIntegration
              study={reportingStudy}
              selectedSeries={reportingStudy.series}
              measurements={measurements}
              onExportMeasurements={exportMeasurements}
              onClose={() => {
                setShowReporting(false);
                setReportingStudy(null);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default App;