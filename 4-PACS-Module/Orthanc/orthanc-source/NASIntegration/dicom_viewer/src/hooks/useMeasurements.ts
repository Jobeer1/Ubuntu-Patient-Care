/**
 * 🇿🇦 South African Medical Imaging System - Measurements Hook
 * 
 * Custom hook for managing DICOM measurements with SA medical standards
 * Handles measurement creation, export, and formatting for reporting
 */

import { useState, useCallback, useEffect } from 'react';
import { Measurement } from '../types/dicom';

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
    
    // Format based on SA medical standards
    let formattedValue = value.toFixed(2);
    
    // Use SA medical terminology if available
    const displayLabel = saTerminology || label || type;
    
    // Format units in metric system (SA standard)
    let displayUnit = unit;
    switch (unit) {
      case 'mm':
        displayUnit = 'mm';
        break;
      case 'cm':
        displayUnit = 'cm';
        break;
      case 'cm²':
        displayUnit = 'cm²';
        break;
      case 'cm³':
        displayUnit = 'cm³';
        break;
      case '°':
        displayUnit = '°';
        break;
      case 'HU':
        displayUnit = 'HU';
        break;
      default:
        displayUnit = unit;
    }

    return `${displayLabel}: ${formattedValue} ${displayUnit}`;
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
        language: 'en', // TODO: Get from user preferences
        medicalContext: 'diagnostic_imaging'
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

// Helper functions for SA medical standards
export const saMedicalUnits = {
  length: ['mm', 'cm', 'm'],
  area: ['mm²', 'cm²', 'm²'],
  volume: ['mm³', 'cm³', 'l', 'ml'],
  angle: ['°', 'rad'],
  density: ['HU', 'g/cm³']
};

export const saAnatomicalTerms = {
  // Common SA anatomical terms in multiple languages
  chest: {
    en: 'chest',
    af: 'bors',
    zu: 'isifuba'
  },
  heart: {
    en: 'heart',
    af: 'hart',
    zu: 'inhliziyo'
  },
  lung: {
    en: 'lung',
    af: 'long',
    zu: 'amaphaphu'
  },
  bone: {
    en: 'bone',
    af: 'been',
    zu: 'ithambo'
  }
};

export const saCommonMeasurements = [
  {
    type: 'length' as const,
    name: 'Cardiothoracic Ratio',
    saTerminology: 'Heart-to-chest ratio',
    normalRange: { min: 0.4, max: 0.5 },
    unit: 'ratio'
  },
  {
    type: 'length' as const,
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
