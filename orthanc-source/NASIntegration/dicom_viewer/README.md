# 🇿🇦 South African Advanced DICOM Viewer

## 🏥 **World-Class Offline DICOM Viewer**

A professional-grade DICOM viewer specifically designed for South African healthcare, featuring:

- **Offline-First**: Works without internet connectivity
- **SA Medical Context**: Optimized for local workflows and terminology
- **Advanced Tools**: Professional measurement and annotation capabilities
- **AI Integration**: Built-in AI diagnosis assistance
- **Voice Integration**: Connected to SA voice dictation system
- **Multi-Language**: English, Afrikaans, isiZulu support

## 🚀 **Features**

### **Core Viewing**
- Fast DICOM image loading and navigation
- Multi-planar reconstruction (MPR)
- 3D volume rendering
- Window/level adjustment with medical presets
- Zoom, pan, rotate, flip operations

### **Measurement Tools**
- Linear measurements (distance, caliber)
- Angular measurements
- Area and volume calculations
- Hounsfield unit (HU) readouts
- Pixel value analysis

### **Advanced Features**
- Side-by-side comparison
- Multi-study temporal analysis
- Cine loop for dynamic studies
- Annotation and markup tools
- Export capabilities

### **South African Specific**
- Integration with SA voice dictation
- AI diagnosis overlay for SA conditions
- Local medical terminology
- Optimized for SA network conditions
- Medical aid integration

## 🛠️ **Technology Stack**

- **Frontend**: React + TypeScript
- **DICOM Processing**: Cornerstone.js + Cornerstone Tools
- **3D Rendering**: VTK.js
- **UI Framework**: Custom SA medical theme
- **State Management**: React Context + Hooks
- **Performance**: Web Workers for processing

## 📁 **Structure**

```
dicom_viewer/
├── src/
│   ├── components/          # React components
│   ├── core/               # DICOM processing core
│   ├── tools/              # Measurement and annotation tools
│   ├── utils/              # Utility functions
│   ├── hooks/              # Custom React hooks
│   └── types/              # TypeScript definitions
├── public/                 # Static assets
└── docs/                   # Documentation
```

## 🎯 **Getting Started**

```bash
cd dicom_viewer
npm install
npm start
```

The viewer will be available at `http://localhost:3001` and integrates seamlessly with the main SA medical imaging system.