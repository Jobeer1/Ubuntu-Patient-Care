/**
 * 🇿🇦 South African Medical Imaging System - DICOM Viewport
 * 
 * Individual viewport component for displaying DICOM images
 */

import React, { useRef, useEffect, useState } from 'react';
import { cornerstone, cornerstoneTools, getSAWindowPreset } from '../../core/cornerstone-init';
import { DicomStudy } from '../../types/dicom';
import { useSALocalization } from '../../hooks/useSALocalization';

interface DicomViewportProps {
  viewportIndex: number;
  study: DicomStudy | null;
  seriesIndex: number;
}

export const DicomViewport: React.FC<DicomViewportProps> = ({
  viewportIndex,
  study,
  seriesIndex
}) => {
  const elementRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageInfo, setImageInfo] = useState<any>(null);
  const { t } = useSALocalization();

  useEffect(() => {
    if (!elementRef.current) return;

    const element = elementRef.current;

    try {
      // Enable the element for Cornerstone
      cornerstone.enable(element);

      // Set up tools for this viewport
      cornerstoneTools.addStackStateManager(element, ['stack']);
      cornerstoneTools.addToolState(element, 'stack', {
        imageIds: [],
        currentImageIdIndex: 0
      });

      // Load image if study and series are available
      if (study && study.series[seriesIndex]) {
        loadSeriesImages(element, study.series[seriesIndex]);
      }

    } catch (err) {
      console.error('Failed to initialize viewport:', err);
      setError('Failed to initialize viewport');
    }

    return () => {
      try {
        if (cornerstone.getEnabledElement(element)) {
          cornerstone.disable(element);
        }
      } catch (err) {
        console.error('Error disabling viewport:', err);
      }
    };
  }, [study, seriesIndex]);

  const loadSeriesImages = async (element: HTMLDivElement, series: any) => {
    setIsLoading(true);
    setError(null);

    try {
      const imageIds = series.images.map((image: any) => image.imageId);
      
      if (imageIds.length === 0) {
        setError('No images in series');
        return;
      }

      // Load the first image
      const image = await cornerstone.loadImage(imageIds[0]);
      
      // Display the image
      cornerstone.displayImage(element, image);

      // Apply SA-specific window preset
      const preset = getSAWindowPreset(series.modality, series.bodyPartExamined);
      const viewport = cornerstone.getViewport(element);
      viewport.voi.windowWidth = preset.windowWidth;
      viewport.voi.windowCenter = preset.windowCenter;
      cornerstone.setViewport(element, viewport);

      // Update stack tool state
      const stackState = cornerstoneTools.getToolState(element, 'stack');
      if (stackState && stackState.data && stackState.data[0]) {
        stackState.data[0].imageIds = imageIds;
        stackState.data[0].currentImageIdIndex = 0;
      }

      // Set image info for display
      setImageInfo({
        patientName: study?.patientInfo.patientName,
        studyDescription: study?.studyDescription,
        seriesDescription: series.seriesDescription,
        instanceNumber: series.images[0].instanceNumber,
        imageCount: series.images.length,
        windowCenter: preset.windowCenter,
        windowWidth: preset.windowWidth
      });

      setIsLoading(false);

    } catch (err) {
      console.error('Failed to load series images:', err);
      setError('Failed to load images');
      setIsLoading(false);
    }
  };

  const renderOverlay = () => {
    if (!imageInfo) return null;

    return (
      <div className="viewport-overlay">
        {/* Top Left - Patient Info */}
        <div className="viewport-info top-left">
          <div>{imageInfo.patientName}</div>
          <div>{imageInfo.studyDescription}</div>
          <div>{imageInfo.seriesDescription}</div>
        </div>

        {/* Top Right - Image Info */}
        <div className="viewport-info top-right">
          <div>Image: {imageInfo.instanceNumber}/{imageInfo.imageCount}</div>
          <div>WW: {imageInfo.windowWidth}</div>
          <div>WC: {imageInfo.windowCenter}</div>
        </div>

        {/* Bottom Left - SA Context */}
        <div className="viewport-info bottom-left">
          <div>🇿🇦 SA Medical Imaging</div>
        </div>

        {/* Bottom Right - Measurements */}
        <div className="viewport-measurements bottom-right">
          {/* Measurements will be displayed here */}
        </div>
      </div>
    );
  };

  return (
    <div className="viewport-container">
      <div
        ref={elementRef}
        className="viewport-element"
        onContextMenu={(e) => e.preventDefault()}
      />
      
      {renderOverlay()}

      {isLoading && (
        <div className="loading-overlay">
          <div className="loading-content">
            <div className="loading-spinner"></div>
            <div className="loading-message">{t('loading.images')}</div>
          </div>
        </div>
      )}

      {error && (
        <div className="error-overlay">
          <div className="error-display">
            <div className="error-title">{t('status.error')}</div>
            <div className="error-message">{error}</div>
          </div>
        </div>
      )}

      {!study && !isLoading && !error && (
        <div className="empty-viewport">
          <div className="empty-content">
            <div className="empty-icon">🏥</div>
            <div className="empty-message">{t('ui.selectStudy')}</div>
          </div>
        </div>
      )}
    </div>
  );
};