/**
 * 🇿🇦 South African Medical Imaging System - DICOM Types
 * 
 * TypeScript definitions for DICOM data structures
 * Tailored for South African healthcare workflows
 */

// Basic DICOM image information
export interface DicomImage {
  imageId: string;
  instanceNumber: number;
  sopInstanceUID: string;
  rows: number;
  columns: number;
  pixelSpacing?: [number, number];
  windowCenter?: number;
  windowWidth?: number;
  rescaleSlope?: number;
  rescaleIntercept?: number;
  photometricInterpretation?: string;
  bitsAllocated?: number;
  bitsStored?: number;
  highBit?: number;
  pixelRepresentation?: number;
  samplesPerPixel?: number;
  planarConfiguration?: number;
}

// DICOM series information
export interface DicomSeries {
  seriesInstanceUID: string;
  seriesNumber: number;
  seriesDescription: string;
  modality: string;
  bodyPartExamined?: string;
  images: DicomImage[];
  numberOfImages: number;
}

// DICOM study information with SA-specific fields
export interface DicomStudy {
  studyInstanceUID: string;
  studyDate: string;
  studyTime?: string;
  studyDescription: string;
  accessionNumber?: string;
  patientInfo: PatientInfo;
  series: DicomSeries[];
  numberOfSeries: number;
  // SA-specific fields
  medicalAidScheme?: string;
  referringPhysician?: string;
  institution?: string;
  saHealthcareProvider?: string;
}

// Patient information with SA-specific fields
export interface PatientInfo {
  patientID: string;
  patientName: string;
  patientBirthDate?: string;
  patientSex?: 'M' | 'F' | 'O';
  patientAge?: string;
  patientWeight?: number;
  patientHeight?: number;
  // SA-specific fields
  saIdNumber?: string;
  medicalAidNumber?: string;
  preferredLanguage?: 'en' | 'af' | 'zu';
  emergencyContact?: string;
}

// Viewport configuration
export interface ViewportConfig {
  scale: number;
  translation: {
    x: number;
    y: number;
  };
  voi: {
    windowWidth: number;
    windowCenter: number;
  };
  invert: boolean;
  pixelReplication: boolean;
  rotation: number;
  hflip: boolean;
  vflip: boolean;
}

// Measurement data
export interface Measurement {
  id: string;
  type: 'length' | 'angle' | 'area' | 'volume' | 'hounsfield';
  value: number;
  unit: string;
  coordinates: number[][];
  imageId: string;
  label?: string;
  description?: string;
  createdBy: string;
  createdDate: string;
  // SA-specific fields
  medicalSignificance?: string;
  saTerminology?: string;
}

// Annotation data
export interface Annotation {
  id: string;
  type: 'arrow' | 'text' | 'freehand' | 'rectangle' | 'ellipse';
  coordinates: number[][];
  text?: string;
  imageId: string;
  style: {
    color: string;
    lineWidth: number;
    fontSize?: number;
  };
  createdBy: string;
  createdDate: string;
  // SA-specific fields
  language?: 'en' | 'af' | 'zu';
  medicalContext?: string;
}

// Tool state
export interface ToolState {
  activeTool: string;
  tools: {
    [toolName: string]: {
      active: boolean;
      configuration?: any;
    };
  };
}

// Layout configuration for multi-image viewing
export interface LayoutConfig {
  rows: number;
  columns: number;
  viewports: ViewportInfo[];
}

export interface ViewportInfo {
  studyInstanceUID?: string;
  seriesInstanceUID?: string;
  imageIndex?: number;
  displaySetInstanceUID?: string;
}

// SA-specific window presets
export interface WindowPreset {
  name: string;
  windowCenter: number;
  windowWidth: number;
  description?: string;
  saCondition?: string; // TB, fracture, etc.
}

// Export configuration for SA medical reports
export interface ExportConfig {
  format: 'pdf' | 'png' | 'jpg' | 'dicom';
  includeAnnotations: boolean;
  includeMeasurements: boolean;
  includePatientInfo: boolean;
  watermark?: string;
  // SA-specific export options
  language: 'en' | 'af' | 'zu';
  medicalAidFormat?: boolean;
  saComplianceMode?: boolean;
}

// AI diagnosis integration (for SA medical conditions)
export interface AIDiagnosis {
  id: string;
  imageId: string;
  condition: string;
  confidence: number;
  boundingBoxes?: number[][];
  description: string;
  recommendations: string[];
  // SA-specific AI fields
  saConditionCode?: string;
  prevalenceInSA?: number;
  urgencyLevel: 'low' | 'medium' | 'high' | 'critical';
}

// Voice dictation integration
export interface VoiceDictation {
  sessionId: string;
  imageId: string;
  audioUrl?: string;
  transcript: string;
  language: 'en' | 'af' | 'zu';
  confidence: number;
  timestamp: string;
  status: 'recording' | 'processing' | 'completed' | 'error';
}

// SA medical terminology
export interface SAMedicalTerm {
  english: string;
  afrikaans?: string;
  zulu?: string;
  code?: string;
  category: 'anatomy' | 'condition' | 'procedure' | 'measurement';
}

// Error types
export interface DicomError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}

// Loading state
export interface LoadingState {
  isLoading: boolean;
  progress?: number;
  message?: string;
  error?: DicomError;
}