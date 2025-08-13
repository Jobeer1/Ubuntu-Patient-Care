/**
 * 🇿🇦 South African Medical Imaging System - App (Phase 1 Integration)
 * 
 * Main application component with Phase 1 reporting integration
 * Shows how measurements hook and ReportingIntegration work together
 */

import React, { useState, useEffect } from 'react';
import { StudyBrowser } from './components/StudyBrowser';
import { ReportingIntegration } from './components/ReportingIntegration';
import { useMeasurements } from './hooks/useMeasurements';

// Simplified interfaces
interface DicomStudy {
  studyInstanceUID: string;
  studyDescription: string;
  studyDate: string;
  patientInfo: {
    patientID: string;
    patientName: string;
    preferredLanguage?: string;
  };
  series: Array<{
    seriesInstanceUID: string;
    seriesDescription: string;
    modality: string;
    numberOfImages: number;
  }>;
}

interface LoadingState {
  isLoading: boolean;
  message?: string;
  error?: { message: string };
}

// Mock data for demonstration
const mockStudies: DicomStudy[] = [
  {
    studyInstanceUID: "1.2.3.4.5.6.7.8.9.0",
    studyDescription: "Chest X-Ray",
    studyDate: "20240115",
    patientInfo: {
      patientID: "SA001234",
      patientName: "John Doe",
      preferredLanguage: "en-ZA"
    },
    series: [
      {
        seriesInstanceUID: "1.2.3.4.5.6.7.8.9.0.1",
        seriesDescription: "PA View",
        modality: "CR",
        numberOfImages: 1
      }
    ]
  }
];

export const App: React.FC = () => {
  // State management
  const [studies] = useState<DicomStudy[]>(mockStudies);
  const [selectedStudy, setSelectedStudy] = useState<DicomStudy | null>(null);
  const [showReporting, setShowReporting] = useState(false);
  const [reportingStudy, setReportingStudy] = useState<DicomStudy | null>(null);
  const [loadingState] = useState<LoadingState>({ isLoading: false });

  // Phase 1: Measurements hook integration
  const { 
    measurements, 
    addMeasurement, 
    updateMeasurement, 
    removeMeasurement, 
    exportMeasurements 
  } = useMeasurements(
    selectedStudy?.studyInstanceUID,
    selectedStudy?.patientInfo.patientID,
    'current_user'
  );

  // Phase 1: Handle study selection
  const handleStudySelect = (study: DicomStudy): void => {
    setSelectedStudy(study);
    console.log('📁 Study selected:', study.studyDescription);
  };

  // Phase 1: Handle report start - KEY INTEGRATION POINT
  const handleStartReport = (study: DicomStudy): void => {
    console.log('📝 Starting report for study:', study.studyDescription);
    setReportingStudy(study);
    setShowReporting(true);
  };

  // Phase 1: Handle measurement addition (would come from DICOM viewer tools)
  const handleMeasurementAdd = (measurementData: any): void => {
    addMeasurement({
      type: measurementData.type || 'distance',
      value: measurementData.value || 0,
      unit: measurementData.unit || 'mm',
      label: measurementData.label,
      imageId: measurementData.imageId,
      coordinates: measurementData.coordinates,
      createdBy: 'current_user'
    });
  };

  // Demo: Add sample measurements on mount
  useEffect(() => {
    if (selectedStudy && measurements.length === 0) {
      // Add some sample measurements to demonstrate
      setTimeout(() => {
        handleMeasurementAdd({
          type: 'distance',
          value: 45.7,
          unit: 'mm',
          label: 'Heart width',
          imageId: 'image_001'
        });
        
        handleMeasurementAdd({
          type: 'area',
          value: 125.3,
          unit: 'cm²',
          label: 'Lesion area',
          imageId: 'image_001'
        });
      }, 1000);
    }
  }, [selectedStudy]);

  return React.createElement('div', { className: 'sa-dicom-viewer' },
    // SA Flag Accent
    React.createElement('div', { className: 'sa-accent' }),
    
    // Main Layout
    React.createElement('div', { className: 'main-layout' },
      // Sidebar with Study Browser
      React.createElement('div', { className: 'sidebar' },
        React.createElement(StudyBrowser, {
          studies,
          selectedStudy,
          onStudySelect: handleStudySelect,
          onStartReport: handleStartReport, // Phase 1: Report integration
          loadingState
        })
      ),

      // Main Content Area
      React.createElement('div', { className: 'main-content' },
        selectedStudy 
          ? React.createElement('div', { className: 'study-viewer' },
              React.createElement('h2', {}, 
                `📋 ${selectedStudy.studyDescription}`
              ),
              React.createElement('div', { className: 'patient-info' },
                `Patient: ${selectedStudy.patientInfo.patientName} (ID: ${selectedStudy.patientInfo.patientID})`
              ),
              React.createElement('div', { className: 'measurements-summary' },
                React.createElement('h3', {}, '📊 Measurements'),
                React.createElement('div', { className: 'measurement-count' },
                  `${measurements.length} measurements recorded`
                ),
                measurements.map((measurement, index) =>
                  React.createElement('div', { 
                    key: measurement.id, 
                    className: 'measurement-item' 
                  },
                    `${index + 1}. ${measurement.label || measurement.type}: ${measurement.value} ${measurement.unit}`
                  )
                )
              ),
              React.createElement('div', { className: 'demo-actions' },
                React.createElement('button', {
                  className: 'btn btn-secondary',
                  onClick: () => handleMeasurementAdd({
                    type: 'distance',
                    value: Math.round(Math.random() * 100 * 10) / 10,
                    unit: 'mm',
                    label: 'Demo measurement',
                    imageId: 'image_001'
                  })
                }, '📏 Add Demo Measurement'),
                React.createElement('button', {
                  className: 'btn btn-primary',
                  onClick: () => handleStartReport(selectedStudy),
                  disabled: measurements.length === 0
                }, '📝 Start Report')
              )
            )
          : React.createElement('div', { className: 'no-study-selected' },
              React.createElement('div', { className: 'empty-message' },
                '📁 Select a study from the sidebar to begin'
              )
            )
      )
    ),

    // Phase 1: Reporting Integration Modal
    showReporting && reportingStudy && React.createElement('div', { className: 'modal-overlay' },
      React.createElement('div', { className: 'modal-content' },
        React.createElement(ReportingIntegration, {
          study: reportingStudy,
          selectedSeries: reportingStudy.series,
          measurements, // Phase 1: Pass actual measurements
          onExportMeasurements: exportMeasurements, // Phase 1: Pass export function
          onClose: () => {
            setShowReporting(false);
            setReportingStudy(null);
          }
        })
      )
    )
  );
};
