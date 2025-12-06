/**
 * 🇿🇦 South African Medical Imaging System - Cornerstone Initialization
 * 
 * Initializes Cornerstone.js and related libraries for DICOM viewing
 * Optimized for South African healthcare workflows
 */

import * as cornerstone from 'cornerstone-core';
import * as cornerstoneWADOImageLoader from 'cornerstone-wado-image-loader';
import * as cornerstoneWebImageLoader from 'cornerstone-web-image-loader';
import * as cornerstoneTools from 'cornerstone-tools';
import * as dicomParser from 'dicom-parser';
import Hammer from 'hammerjs';

// Configure WADO Image Loader
function configureWADOImageLoader() {
  const config = {
    maxWebWorkers: navigator.hardwareConcurrency || 1,
    startWebWorkersOnDemand: false,
    taskConfiguration: {
      decodeTask: {
        initializeCodecsOnStartup: false,
        strict: false,
      },
    },
  };

  cornerstoneWADOImageLoader.external.cornerstone = cornerstone;
  cornerstoneWADOImageLoader.external.dicomParser = dicomParser;
  cornerstoneWADOImageLoader.webWorkerManager.initialize(config);
}

// Configure Web Image Loader
function configureWebImageLoader() {
  cornerstoneWebImageLoader.external.cornerstone = cornerstone;
}

// Configure Cornerstone Tools
function configureCornerstoneTools() {
  cornerstoneTools.external.cornerstone = cornerstone;
  cornerstoneTools.external.Hammer = Hammer;
  
  // Initialize tools
  cornerstoneTools.init({
    mouseEnabled: true,
    touchEnabled: true,
    globalToolSyncEnabled: false,
    showSVGCursors: true,
  });

  // Add tools for South African medical workflows
  const tools = [
    // Basic tools
    cornerstoneTools.PanTool,
    cornerstoneTools.ZoomTool,
    cornerstoneTools.WwwcTool,
    cornerstoneTools.StackScrollMouseWheelTool,
    cornerstoneTools.StackScrollTool,
    
    // Measurement tools (critical for SA medical practice)
    cornerstoneTools.LengthTool,
    cornerstoneTools.AngleTool,
    cornerstoneTools.RectangleRoiTool,
    cornerstoneTools.EllipticalRoiTool,
    cornerstoneTools.CircleRoiTool,
    cornerstoneTools.FreehandRoiTool,
    
    // Annotation tools
    cornerstoneTools.ArrowAnnotateTool,
    cornerstoneTools.TextMarkerTool,
    cornerstoneTools.ProbeTool,
    
    // Advanced tools
    cornerstoneTools.MagnifyTool,
    cornerstoneTools.CrosshairsTool,
    cornerstoneTools.ReferenceLinesTool,
    
    // Touch tools for mobile/tablet use
    cornerstoneTools.PanMultiTouchTool,
    cornerstoneTools.ZoomTouchPinchTool,
    cornerstoneTools.StackScrollMultiTouchTool,
  ];

  // Add all tools to Cornerstone Tools
  tools.forEach(tool => {
    cornerstoneTools.addTool(tool);
  });

  // Set default tool states for SA medical workflows
  cornerstoneTools.setToolActive('Pan', { mouseButtonMask: 4 }); // Middle mouse
  cornerstoneTools.setToolActive('Zoom', { mouseButtonMask: 2 }); // Right mouse
  cornerstoneTools.setToolActive('Wwwc', { mouseButtonMask: 1 }); // Left mouse
  cornerstoneTools.setToolActive('StackScrollMouseWheel', {});
  
  // Touch tools for mobile devices
  cornerstoneTools.setToolActive('PanMultiTouch', {});
  cornerstoneTools.setToolActive('ZoomTouchPinch', {});
  cornerstoneTools.setToolActive('StackScrollMultiTouch', {});
}

// South African specific presets for common medical imaging
export const SA_WINDOW_PRESETS = {
  // Chest X-Ray (common in SA for TB screening)
  chest: { windowCenter: -600, windowWidth: 1500, name: 'Chest' },
  
  // Bone (fractures common in SA trauma centers)
  bone: { windowCenter: 300, windowWidth: 1500, name: 'Bone' },
  
  // Soft Tissue
  softTissue: { windowCenter: 40, windowWidth: 400, name: 'Soft Tissue' },
  
  // Lung (TB and respiratory conditions)
  lung: { windowCenter: -500, windowWidth: 1400, name: 'Lung' },
  
  // Brain (stroke and trauma)
  brain: { windowCenter: 40, windowWidth: 80, name: 'Brain' },
  
  // Abdomen
  abdomen: { windowCenter: 60, windowWidth: 400, name: 'Abdomen' },
  
  // Liver (hepatitis screening)
  liver: { windowCenter: 90, windowWidth: 150, name: 'Liver' },
  
  // Mediastinum
  mediastinum: { windowCenter: 50, windowWidth: 350, name: 'Mediastinum' },
};

// Initialize Cornerstone and all related libraries
export function initializeCornerstone(): void {
  try {
    console.log('🇿🇦 Initializing SA DICOM Viewer...');
    
    // Configure image loaders
    configureWADOImageLoader();
    configureWebImageLoader();
    
    // Configure tools
    configureCornerstoneTools();
    
    // Enable Cornerstone
    cornerstone.enable(document.createElement('div'));
    
    console.log('✅ SA DICOM Viewer initialized successfully');
    console.log('🏥 Ready for South African medical imaging workflows');
    
  } catch (error) {
    console.error('❌ Failed to initialize SA DICOM Viewer:', error);
    throw error;
  }
}

// Utility function to get appropriate window preset for SA medical conditions
export function getSAWindowPreset(modality: string, bodyPart: string): any {
  const key = `${modality}_${bodyPart}`.toLowerCase();
  
  // SA-specific mappings for common conditions
  const saPresets: { [key: string]: any } = {
    'cr_chest': SA_WINDOW_PRESETS.chest,
    'dx_chest': SA_WINDOW_PRESETS.chest,
    'ct_chest': SA_WINDOW_PRESETS.lung,
    'ct_head': SA_WINDOW_PRESETS.brain,
    'ct_abdomen': SA_WINDOW_PRESETS.abdomen,
    'cr_bone': SA_WINDOW_PRESETS.bone,
    'dx_bone': SA_WINDOW_PRESETS.bone,
  };
  
  return saPresets[key] || SA_WINDOW_PRESETS.softTissue;
}

// Export Cornerstone and tools for use in components
export { cornerstone, cornerstoneTools, cornerstoneWADOImageLoader };