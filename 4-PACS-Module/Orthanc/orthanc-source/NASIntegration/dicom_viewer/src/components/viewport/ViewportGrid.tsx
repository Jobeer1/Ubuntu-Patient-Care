/**
 * 🇿🇦 South African Medical Imaging System - Viewport Grid
 * 
 * Component for displaying DICOM images in configurable grid layouts
 */

import React, { useRef, useEffect } from 'react';
import { DicomStudy, LayoutConfig } from '../../types/dicom';
import { DicomViewport } from './DicomViewport';

interface ViewportGridProps {
  layoutConfig: LayoutConfig;
  selectedStudy: DicomStudy | null;
  onLayoutChange: (rows: number, columns: number) => void;
}

export const ViewportGrid: React.FC<ViewportGridProps> = ({
  layoutConfig,
  selectedStudy,
  onLayoutChange
}) => {
  const gridRef = useRef<HTMLDivElement>(null);

  const gridStyle = {
    gridTemplateRows: `repeat(${layoutConfig.rows}, 1fr)`,
    gridTemplateColumns: `repeat(${layoutConfig.columns}, 1fr)`
  };

  const totalViewports = layoutConfig.rows * layoutConfig.columns;

  return (
    <div 
      ref={gridRef}
      className="viewport-grid"
      style={gridStyle}
    >
      {Array.from({ length: totalViewports }, (_, index) => (
        <DicomViewport
          key={index}
          viewportIndex={index}
          study={selectedStudy}
          seriesIndex={index < (selectedStudy?.series.length || 0) ? index : 0}
        />
      ))}
    </div>
  );
};