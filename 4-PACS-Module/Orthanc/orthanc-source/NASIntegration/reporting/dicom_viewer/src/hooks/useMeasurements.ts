/**
 * 🇿🇦 South African Medical Imaging System - Measurements Hook
 * 
 * Custom hook for managing DICOM measurements with SA medical standards
 * Handles measurement creation, export, and formatting for reporting
 */

import { useState, useCallback, useEffect } from 'react';

// South African Medical Standards
export const SA_MEDICAL_STANDARDS = {
  units: {
    length: ['mm', 'cm', 'm'] as const,
    area: ['mm²', 'cm²', 'm²'] as const,
    volume: ['mm³', 'cm³', 'l', 'ml'] as const,
    angle: ['°', 'rad'] as const,
    density: ['HU', 'g/cm³'] as const
  },
  precision: {
    length: 1,
    area: 2,
    volume: 2,
    angle: 1,
    density: 0
  },
  language: {
    en: 'English',
    af: 'Afrikaans', 
    zu: 'isiZulu'
  }
};

export interface Measurement {
  id: string;
  type: 'distance' | 'area' | 'angle' | 'point' | 'rectangle' | 'ellipse';
  value: number;
  unit: string;
  label?: string;
  imageId?: string;
  coordinates?: {
    x: number;
    y: number;
  }[];
  saTerminology?: string;
  createdDate: string;
  createdBy: string;
  metadata?: {
    anatomicalLocation?: string;
    clinicalContext?: string;
    saReference?: string;
  };
}

export interface MeasurementExport {
  studyInstanceUID: string;
  patientID: string;
  measurements: Measurement[];
  exportedAt: string;
  exportedBy: string;
  saStandards: {
    units: 'metric';
    language: 'en' | 'af' | 'zu';
    medicalContext: string;
    standardsVersion: string;
  };
}

export interface UseMeasurementsReturn {
  measurements: Measurement[];
  addMeasurement: (measurement: Omit<Measurement, 'id' | 'createdDate'>) => void;
  removeMeasurement: (id: string) => void;
  updateMeasurement: (id: string, updates: Partial<Measurement>) => void;
  clearMeasurements: () => void;
  exportMeasurements: () => MeasurementExport;
  getMeasurementsByType: (type: Measurement['type']) => Measurement[];
  getMeasurementsByImage: (imageId: string) => Measurement[];
  formatMeasurementForSA: (measurement: Measurement) => string;
}

export const useMeasurements = (
  studyInstanceUID?: string,
  patientID?: string,
  currentUser: string = 'unknown'
): UseMeasurementsReturn => {
  const [measurements, setMeasurements] = useState<Measurement[]>([]);

  // Load measurements from localStorage on mount
  useEffect(() => {
    if (studyInstanceUID) {
      const storageKey = `measurements_${studyInstanceUID}`;
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        try {
          const parsedMeasurements = JSON.parse(stored);
          setMeasurements(parsedMeasurements);
        } catch (error) {
          console.warn('Failed to load stored measurements:', error);
        }
      }
    }
  }, [studyInstanceUID]);

  // Save measurements to localStorage when they change
  useEffect(() => {
    if (studyInstanceUID && measurements.length > 0) {
      const storageKey = `measurements_${studyInstanceUID}`;
      localStorage.setItem(storageKey, JSON.stringify(measurements));
    }
  }, [measurements, studyInstanceUID]);

  const addMeasurement = useCallback((measurementData: Omit<Measurement, 'id' | 'createdDate'>) => {
    const newMeasurement: Measurement = {
      ...measurementData,
      id: `measurement_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      createdDate: new Date().toISOString(),
      createdBy: currentUser
    };

    setMeasurements(prev => [...prev, newMeasurement]);
    
    console.log('🏥 SA Measurement added:', {
      type: newMeasurement.type,
      value: newMeasurement.value,
      unit: newMeasurement.unit,
      saTerminology: newMeasurement.saTerminology
    });
  }, [currentUser]);

  const removeMeasurement = useCallback((id: string) => {
    setMeasurements(prev => prev.filter(m => m.id !== id));
  }, []);

  const updateMeasurement = useCallback((id: string, updates: Partial<Measurement>) => {
    setMeasurements(prev => 
      prev.map(m => m.id === id ? { ...m, ...updates } : m)
    );
  }, []);

  const clearMeasurements = useCallback(() => {
    setMeasurements([]);
    if (studyInstanceUID) {
      const storageKey = `measurements_${studyInstanceUID}`;
      localStorage.removeItem(storageKey);
    }
  }, [studyInstanceUID]);

  const getMeasurementsByType = useCallback((type: Measurement['type']) => {
    return measurements.filter(m => m.type === type);
  }, [measurements]);

  const getMeasurementsByImage = useCallback((imageId: string) => {
    return measurements.filter(m => m.imageId === imageId);
  }, [measurements]);

  const formatMeasurementForSA = useCallback((measurement: Measurement): string => {
    const { type, value, unit, label, saTerminology } = measurement;
    
    // Get precision based on type
    let precision = 1;
    if (type === 'area') precision = 2;
    if (type === 'angle') precision = 1;
    
    const formattedValue = value.toFixed(precision);
    const displayLabel = saTerminology || label || type;
    
    return `${displayLabel}: ${formattedValue} ${unit}`;
  }, []);

  const exportMeasurements = useCallback((): MeasurementExport => {
    const exportData: MeasurementExport = {
      studyInstanceUID: studyInstanceUID || '',
      patientID: patientID || '',
      measurements,
      exportedAt: new Date().toISOString(),
      exportedBy: currentUser,
      saStandards: {
        units: 'metric',
        language: 'en',
        medicalContext: 'diagnostic_imaging',
        standardsVersion: 'SA_MEDICAL_2024'
      }
    };

    console.log('📊 SA Measurements exported:', {
      count: measurements.length,
  types: Array.from(new Set(measurements.map(m => m.type))),
      export: exportData
    });

    return exportData;
  }, [measurements, studyInstanceUID, patientID, currentUser]);

  return {
    measurements,
    addMeasurement,
    removeMeasurement,
    updateMeasurement,
    clearMeasurements,
    exportMeasurements,
    getMeasurementsByType,
    getMeasurementsByImage,
    formatMeasurementForSA
  };
};

// SA Medical terminology translations
export const saAnatomicalTerms = {
  chest: { en: 'chest', af: 'bors', zu: 'isifuba' },
  heart: { en: 'heart', af: 'hart', zu: 'inhliziyo' },
  lung: { en: 'lung', af: 'long', zu: 'amaphaphu' },
  bone: { en: 'bone', af: 'been', zu: 'ithambo' }
};

// Common SA medical measurements
export const saCommonMeasurements = [
  {
    type: 'distance' as const,
    name: 'Cardiothoracic Ratio',
    saTerminology: 'Heart-to-chest ratio',
    normalRange: { min: 0.4, max: 0.5 },
    unit: 'ratio'
  },
  {
    type: 'distance' as const,
    name: 'Fracture Length',
    saTerminology: 'Fracture measurement',
    unit: 'mm'
  },
  {
    type: 'area' as const,
    name: 'Lesion Area',
    saTerminology: 'TB lesion area',
    unit: 'cm²'
  },
  {
    type: 'angle' as const,
    name: 'Cobb Angle',
    saTerminology: 'Spinal curvature',
    unit: '°'
  }
];
