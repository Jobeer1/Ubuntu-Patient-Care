# Clinical-Grade DICOM Viewer

## Overview
Production-ready DICOM viewer optimized for emergency radiology where every second counts. Handles any modality, any slice order, with intelligent rendering and clinical presets.

## Key Features

### Intelligent DICOM Processing
- **Auto-orientation**: Automatically detects and corrects slice order (axial/sagittal/coronal)
- **Smart sorting**: Handles mixed acquisitions, helical CT, multi-phase studies
- **Modality presets**: Optimized window/level for CT, MR, X-Ray, US
- **Metadata parsing**: Extracts patient position, slice location, acquisition time

### Clinical Rendering
- **Window/Level presets**: Brain, Lung, Bone, Soft Tissue, Abdomen, Mediastinum
- **Adaptive contrast**: Auto-adjusts for optimal visualization
- **Noise reduction**: Real-time denoising for low-dose studies
- **Edge enhancement**: Sharpening for subtle findings

### Performance
- **Progressive loading**: Display first slice in <500ms
- **Web Workers**: Background processing doesn't block UI
- **Caching**: Smart prefetch of adjacent slices
- **GPU acceleration**: WebGL for real-time transformations

### Clinical Tools
- **Measurements**: Distance, angle, ROI, Hounsfield units
- **Annotations**: Arrows, text, circles for findings
- **Cine mode**: Auto-scroll through series
- **Stack scrolling**: Mouse wheel navigation
- **Pan/Zoom**: Touch and mouse support
- **Crosshairs**: Multi-planar reference

### Integration
- Works with Orthanc, dcm4chee, any DICOM server
- DICOMweb (WADO-RS) support
- Offline mode with local files
- Export to PNG/JPEG with annotations

## Technology Stack
- **Cornerstone3D**: Modern DICOM rendering engine
- **dicomParser**: Fast DICOM tag parsing
- **WebGL**: GPU-accelerated rendering
- **Web Workers**: Multi-threaded processing
- **IndexedDB**: Client-side caching

## Quick Start

```bash
cd 4-PACS-Module/clinical-viewer
npm install
npm run dev
```

Open http://localhost:3000

## Clinical Presets

### CT Presets
- **Brain**: W:80 L:40 - Stroke, hemorrhage
- **Subdural**: W:200 L:75 - Subdural hematoma
- **Bone**: W:2000 L:300 - Fractures
- **Lung**: W:1500 L:-600 - Pneumonia, nodules
- **Mediastinum**: W:350 L:50 - Aorta, lymph nodes
- **Abdomen**: W:400 L:40 - Liver, spleen, kidneys
- **Spine**: W:250 L:50 - Vertebrae, discs

### MR Presets
- **T1**: Anatomy, contrast enhancement
- **T2**: Edema, fluid
- **FLAIR**: White matter lesions
- **DWI**: Acute stroke

## Architecture

```
clinical-viewer/
├── src/
│   ├── core/
│   │   ├── dicom-loader.js      # DICOM file/network loading
│   │   ├── series-sorter.js     # Intelligent slice ordering
│   │   ├── viewport-manager.js  # Multi-viewport handling
│   │   └── rendering-engine.js  # Cornerstone3D wrapper
│   ├── tools/
│   │   ├── window-level.js      # W/L adjustment
│   │   ├── measurements.js      # Distance, ROI, HU
│   │   ├── annotations.js       # Clinical markup
│   │   └── cine.js              # Auto-scroll
│   ├── presets/
│   │   ├── ct-presets.js        # CT window/level
│   │   ├── mr-presets.js        # MR sequences
│   │   └── modality-config.js   # Per-modality settings
│   ├── ui/
│   │   ├── toolbar.js           # Tool buttons
│   │   ├── series-browser.js    # Thumbnail grid
│   │   └── overlay.js           # Patient info, annotations
│   └── app.js                   # Main application
├── styles/
│   └── clinical.css             # Dark theme, clinical UI
├── workers/
│   ├── dicom-parser.worker.js   # Background DICOM parsing
│   └── image-processor.worker.js # Denoising, enhancement
└── index.html
```

## Usage Examples

### Load from Orthanc
```javascript
const viewer = new ClinicalViewer('viewportElement');
await viewer.loadStudy('orthanc', studyInstanceUID);
```

### Load local files
```javascript
const files = document.getElementById('fileInput').files;
await viewer.loadFiles(files);
```

### Apply preset
```javascript
viewer.applyPreset('CT_BRAIN');
```

### Measure distance
```javascript
viewer.activateTool('length');
```

## Keyboard Shortcuts
- **W**: Window/Level
- **Z**: Zoom
- **P**: Pan
- **M**: Measure
- **A**: Annotate
- **I**: Invert
- **R**: Reset
- **C**: Cine mode
- **1-9**: Quick presets
- **Space**: Play/Pause cine
- **Arrow keys**: Navigate slices

## Browser Support
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Performance Targets
- First slice render: <500ms
- Slice navigation: <50ms
- Window/Level: <16ms (60 FPS)
- Full study load: <5s for 500 slices

## Clinical Validation
- Tested with CT, MR, CR, DX, US, MG, PT, NM
- Validated against OsiriX, Horos, RadiAnt
- DICOM conformance tested with DVTk
- Rendering accuracy verified with test patterns

## License
MIT - Free for clinical and commercial use
