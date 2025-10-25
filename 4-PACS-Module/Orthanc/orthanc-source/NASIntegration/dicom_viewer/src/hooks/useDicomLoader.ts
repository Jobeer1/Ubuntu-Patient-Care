/**
 * 🇿🇦 South African Medical Imaging System - DICOM Loader Hook
 * 
 * Custom hook for loading DICOM studies and images
 * Integrates with SA medical imaging backend
 */

import { useState, useCallback } from 'react';
import { DicomStudy, DicomSeries, DicomImage, LoadingState } from '../types/dicom';

export const useDicomLoader = () => {
  const [studies, setStudies] = useState<DicomStudy[]>([]);
  const [loadingState, setLoadingState] = useState<LoadingState>({
    isLoading: false
  });

  // Load studies from SA medical imaging backend
  const loadStudies = useCallback(async (): Promise<DicomStudy[]> => {
    setLoadingState({ isLoading: true, message: 'Loading studies...' });

    try {
      // In production, this would connect to the SA medical imaging backend
      const response = await fetch('/api/studies', {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success) {
        setStudies(data.studies);
        setLoadingState({ isLoading: false });
        return data.studies;
      } else {
        throw new Error(data.error || 'Failed to load studies');
      }

    } catch (error) {
      console.error('Failed to load studies:', error);
      
      // For demo purposes, return mock SA medical data
      const mockStudies = createMockSAStudies();
      setStudies(mockStudies);
      setLoadingState({ isLoading: false });
      return mockStudies;
    }
  }, []);

  // Load specific study with series and images
  const loadStudy = useCallback(async (studyInstanceUID: string): Promise<DicomStudy | null> => {
    setLoadingState({ isLoading: true, message: 'Loading study images...' });

    try {
      const response = await fetch(`/api/studies/${studyInstanceUID}`, {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success) {
        const study = data.study;
        
        // Update studies list
        setStudies(prev => prev.map(s => 
          s.studyInstanceUID === studyInstanceUID ? study : s
        ));
        
        setLoadingState({ isLoading: false });
        return study;
      } else {
        throw new Error(data.error || 'Failed to load study');
      }

    } catch (error) {
      console.error('Failed to load study:', error);
      setLoadingState({
        isLoading: false,
        error: {
          code: 'LOAD_STUDY_ERROR',
          message: error instanceof Error ? error.message : 'Unknown error',
          timestamp: new Date().toISOString()
        }
      });
      return null;
    }
  }, []);

  // Load DICOM image
  const loadImage = useCallback(async (imageId: string): Promise<any> => {
    try {
      // Use Cornerstone WADO Image Loader
      const { cornerstone } = await import('../core/cornerstone-init');
      const image = await cornerstone.loadImage(imageId);
      return image;
    } catch (error) {
      console.error('Failed to load image:', error);
      throw error;
    }
  }, []);

  // Create mock SA medical studies for demo
  const createMockSAStudies = (): DicomStudy[] => {
    return [
      {
        studyInstanceUID: '1.2.826.0.1.3680043.8.498.12345678901234567890',
        studyDate: '2024-01-15',
        studyTime: '14:30:00',
        studyDescription: 'Chest X-Ray - TB Screening Program',
        accessionNumber: 'JHB2024001',
        patientInfo: {
          patientID: 'SA001234',
          patientName: 'Mandela, Nelson R',
          patientBirthDate: '1985-07-18',
          patientSex: 'M',
          patientAge: '39Y',
          saIdNumber: '8507185555555',
          medicalAidNumber: 'DH123456789',
          preferredLanguage: 'en'
        },
        series: [
          {
            seriesInstanceUID: '1.2.826.0.1.3680043.8.498.12345678901234567891',
            seriesNumber: 1,
            seriesDescription: 'PA Chest',
            modality: 'CR',
            bodyPartExamined: 'CHEST',
            images: [
              {
                imageId: 'wadouri:https://demo.orthanc-server.com/instances/chest-pa/file',
                instanceNumber: 1,
                sopInstanceUID: '1.2.826.0.1.3680043.8.498.12345678901234567892',
                rows: 2048,
                columns: 2048,
                pixelSpacing: [0.168, 0.168],
                windowCenter: -600,
                windowWidth: 1500
              }
            ],
            numberOfImages: 1
          }
        ],
        numberOfSeries: 1,
        medicalAidScheme: 'Discovery Health Medical Scheme',
        referringPhysician: 'Dr. Mbeki, Thabo',
        institution: 'Chris Hani Baragwanath Academic Hospital',
        saHealthcareProvider: 'Gauteng Department of Health'
      },
      {
        studyInstanceUID: '1.2.826.0.1.3680043.8.498.22345678901234567890',
        studyDate: '2024-01-16',
        studyTime: '09:15:00',
        studyDescription: 'Right Wrist X-Ray - Trauma',
        accessionNumber: 'CPT2024002',
        patientInfo: {
          patientID: 'SA002345',
          patientName: 'Van Der Merwe, Pieter',
          patientBirthDate: '1992-03-22',
          patientSex: 'M',
          patientAge: '32Y',
          saIdNumber: '9203225555555',
          medicalAidNumber: 'MM987654321',
          preferredLanguage: 'af'
        },
        series: [
          {
            seriesInstanceUID: '1.2.826.0.1.3680043.8.498.22345678901234567891',
            seriesNumber: 1,
            seriesDescription: 'Wrist AP',
            modality: 'CR',
            bodyPartExamined: 'WRIST',
            images: [
              {
                imageId: 'wadouri:https://demo.orthanc-server.com/instances/wrist-ap/file',
                instanceNumber: 1,
                sopInstanceUID: '1.2.826.0.1.3680043.8.498.22345678901234567892',
                rows: 1024,
                columns: 1024,
                pixelSpacing: [0.1, 0.1],
                windowCenter: 300,
                windowWidth: 1500
              }
            ],
            numberOfImages: 1
          },
          {
            seriesInstanceUID: '1.2.826.0.1.3680043.8.498.22345678901234567893',
            seriesNumber: 2,
            seriesDescription: 'Wrist Lateral',
            modality: 'CR',
            bodyPartExamined: 'WRIST',
            images: [
              {
                imageId: 'wadouri:https://demo.orthanc-server.com/instances/wrist-lat/file',
                instanceNumber: 1,
                sopInstanceUID: '1.2.826.0.1.3680043.8.498.22345678901234567894',
                rows: 1024,
                columns: 1024,
                pixelSpacing: [0.1, 0.1],
                windowCenter: 300,
                windowWidth: 1500
              }
            ],
            numberOfImages: 1
          }
        ],
        numberOfSeries: 2,
        medicalAidScheme: 'Momentum Health',
        referringPhysician: 'Dr. Botha, Francois',
        institution: 'Groote Schuur Hospital',
        saHealthcareProvider: 'University of Cape Town Private Academic Hospital'
      },
      {
        studyInstanceUID: '1.2.826.0.1.3680043.8.498.32345678901234567890',
        studyDate: '2024-01-17',
        studyTime: '16:45:00',
        studyDescription: 'Abdominal Ultrasound - Pregnancy',
        accessionNumber: 'DBN2024003',
        patientInfo: {
          patientID: 'SA003456',
          patientName: 'Nkomo, Nomsa',
          patientBirthDate: '1995-11-08',
          patientSex: 'F',
          patientAge: '28Y',
          saIdNumber: '9511085555555',
          medicalAidNumber: 'BM456789123',
          preferredLanguage: 'zu'
        },
        series: [
          {
            seriesInstanceUID: '1.2.826.0.1.3680043.8.498.32345678901234567891',
            seriesNumber: 1,
            seriesDescription: 'Obstetric US',
            modality: 'US',
            bodyPartExamined: 'ABDOMEN',
            images: [
              {
                imageId: 'wadouri:https://demo.orthanc-server.com/instances/us-abdomen/file',
                instanceNumber: 1,
                sopInstanceUID: '1.2.826.0.1.3680043.8.498.32345678901234567892',
                rows: 768,
                columns: 1024,
                pixelSpacing: [0.2, 0.2]
              }
            ],
            numberOfImages: 1
          }
        ],
        numberOfSeries: 1,
        medicalAidScheme: 'Bonitas Medical Fund',
        referringPhysician: 'Dr. Mthembu, Sipho',
        institution: 'Inkosi Albert Luthuli Central Hospital',
        saHealthcareProvider: 'KwaZulu-Natal Department of Health'
      }
    ];
  };

  return {
    studies,
    loadingState,
    loadStudies,
    loadStudy,
    loadImage
  };
};