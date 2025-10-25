# Client-Side GPU Architecture for PACS Features

**Date**: October 23, 2025  
**Status**: Implementation Guide  
**Goal**: Move GPU-intensive processing from server to client browser

---

## 🎯 Overview

This document outlines the architecture for moving GPU-intensive PACS features to client-side processing using WebGL, WebGPU, and browser-based ML inference.

### Why Client-Side GPU?

✅ **No Server GPU Required** - Runs on user's hardware  
✅ **Better Performance** - Direct GPU access, no network latency  
✅ **Scalability** - Each user uses their own GPU  
✅ **Privacy** - Medical data stays in browser  
✅ **Cost Effective** - No expensive GPU servers needed  

---

## 📊 Current Status Analysis

### Phase 1: 3D Viewer (100% Complete) ✅
**Current**: Already client-side with Three.js  
**Status**: ✅ No changes needed  
**GPU Usage**: WebGL rendering in browser

### Phase 2: Segmentation (100% Complete) ⚠️
**Current**: Server-side PyTorch/MONAI processing  
**Issue**: Requires server GPU  
**Solution**: Move to TensorFlow.js or ONNX.js

### Phase 3: Cardiac/Calcium (67% Complete) ⚠️
**Current**: Server-side numpy calculations  
**Issue**: CPU-intensive on server  
**Solution**: Move to WebGL compute shaders

### Phase 4: Perfusion/Mammography (100% Complete) ⚠️
**Current**: Server-side processing  
**Issue**: Requires server resources  
**Solution**: Client-side image processing

### Phase 5: Reporting (50% Complete) ✅
**Current**: Speech-to-text via Web Speech API  
**Status**: ✅ Already client-side

---

## 🏗️ Architecture Changes

### 1. Three.js 3D Rendering (Already Done ✅)

**File**: `static/js/viewers/3d-renderer.js`  
**Status**: ✅ Complete - Uses WebGL  
**GPU**: Client-side WebGL  
**No changes needed**

```javascript
// Already using client GPU via Three.js
this.renderer = new THREE.WebGLRenderer({
    canvas: this.canvas,
    antialias: true,
    alpha: true
});
```

---

### 2. ML Segmentation → TensorFlow.js

**Current**: `app/ml_models/segmentation_engine.py` (Server PyTorch)  
**New**: `static/js/ml/segmentation-tfjs.js` (Client TensorFlow.js)

#### Implementation Plan

**Step 1**: Convert PyTorch models to ONNX format
```python
# Server-side conversion (one-time)
import torch
import onnx

model = load_pytorch_model()
dummy_input = torch.randn(1, 1, 128, 128, 128)
torch.onnx.export(model, dummy_input, "vessel_seg.onnx")
```

**Step 2**: Load ONNX in browser with ONNX.js
```javascript
// Client-side inference
import * as ort from 'onnxruntime-web';

class ClientSegmentationEngine {
    async loadModel(modelPath) {
        this.session = await ort.InferenceSession.create(modelPath, {
            executionProviders: ['webgl', 'wasm']  // GPU fallback to CPU
        });
    }
    
    async segment(volumeData) {
        const tensor = new ort.Tensor('float32', volumeData, [1, 1, 128, 128, 128]);
        const results = await this.session.run({ input: tensor });
        return results.output.data;
    }
}
```

**Step 3**: Update API to serve models instead of running inference
```python
# Server only serves model files
@router.get("/api/models/vessel-segmentation")
async def get_vessel_model():
    return FileResponse("models/vessel_seg.onnx")
```

---

### 3. Calcium Scoring → WebGL Compute

**Current**: `app/routes/calcium_scoring.py` (Server numpy)  
**New**: `static/js/compute/calcium-scoring.js` (Client WebGL)

#### Implementation with WebGL Compute Shaders

```javascript
class ClientCalciumScoring {
    constructor() {
        this.gl = document.createElement('canvas').getContext('webgl2');
    }
    
    calculateAgatstonScore(volumeData, threshold = 130) {
        // Create WebGL texture from volume
        const texture = this.createVolumeTexture(volumeData);
        
        // Compile compute shader
        const shader = this.compileShader(`
            #version 300 es
            precision highp float;
            
            uniform sampler3D volume;
            uniform float threshold;
            
            out vec4 fragColor;
            
            void main() {
                vec3 pos = gl_FragCoord.xyz / vec3(512.0, 512.0, 128.0);
                float hu = texture(volume, pos).r;
                
                // Agatston algorithm
                float score = 0.0;
                if (hu > threshold) {
                    float density = hu >= 400.0 ? 4.0 :
                                   hu >= 300.0 ? 3.0 :
                                   hu >= 200.0 ? 2.0 : 1.0;
                    score = density;
                }
                
                fragColor = vec4(score, 0.0, 0.0, 1.0);
            }
        `);
        
        // Run computation on GPU
        this.runCompute(shader, texture);
        
        // Read back results
        return this.readResults();
    }
}
```

---

### 4. Perfusion Analysis → Canvas 2D + WebGL

**Current**: `app/routes/perfusion_analyzer.py` (Server scipy)  
**New**: `static/js/compute/perfusion-analysis.js` (Client)

#### Time-Intensity Curve Extraction

```javascript
class ClientPerfusionAnalysis {
    extractTIC(dynamicSeries, roi) {
        // Use Canvas 2D for pixel operations
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        const tic = [];
        for (let frame of dynamicSeries) {
            ctx.putImageData(frame, 0, 0);
            const pixels = ctx.getImageData(roi.x, roi.y, roi.width, roi.height);
            const mean = this.calculateMean(pixels.data);
            tic.push(mean);
        }
        
        return tic;
    }
    
    generatePerfusionMap(tic, method = 'CBF') {
        // Use WebGL for parallel computation
        const shader = this.getShaderForMethod(method);
        return this.computeOnGPU(shader, tic);
    }
}
```

---

### 5. Mammography CAD → TensorFlow.js

**Current**: `app/routes/mammography_tools.py` (Server)  
**New**: `static/js/ml/mammography-cad.js` (Client)

```javascript
class ClientMammographyCAD {
    async detectLesions(mammogramImage) {
        // Load pre-trained model
        const model = await tf.loadGraphModel('/models/mammo_cad/model.json');
        
        // Preprocess image
        const tensor = tf.browser.fromPixels(mammogramImage)
            .resizeBilinear([512, 512])
            .expandDims(0)
            .div(255.0);
        
        // Run inference on client GPU
        const predictions = await model.predict(tensor);
        
        // Post-process results
        return this.extractLesions(predictions);
    }
}
```

---

## 📦 Required Libraries

### Add to HTML Files

```html
<!-- TensorFlow.js for ML inference -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.11.0"></script>

<!-- ONNX Runtime Web for model inference -->
<script src="https://cdn.jsdelivr.net/npm/onnxruntime-web@1.16.0/dist/ort.min.js"></script>

<!-- GPU.js for general GPU compute -->
<script src="https://cdn.jsdelivr.net/npm/gpu.js@2.16.0/dist/gpu-browser.min.js"></script>

<!-- Already have Three.js for 3D rendering -->
<script src="https://cdn.jsdelivr.net/npm/three@0.157.0/build/three.min.js"></script>
```

---

## 🔄 Migration Strategy

### Phase 1: Parallel Implementation (Week 1)
- ✅ Keep server-side code working
- ✅ Implement client-side versions
- ✅ Add feature flag to switch between modes

### Phase 2: Testing (Week 2)
- ✅ Test client-side performance
- ✅ Verify accuracy matches server results
- ✅ Test on different GPUs/browsers

### Phase 3: Gradual Rollout (Week 3)
- ✅ Enable client-side for 10% of users
- ✅ Monitor performance and errors
- ✅ Increase to 50%, then 100%

### Phase 4: Server Deprecation (Week 4)
- ✅ Remove server-side GPU code
- ✅ Keep server for model serving only
- ✅ Update documentation

---

## 🎯 Implementation Priority

### High Priority (Do First)
1. **Segmentation** - Most GPU-intensive
2. **Calcium Scoring** - Clinical critical
3. **Perfusion Analysis** - Real-time needed

### Medium Priority
4. **Mammography CAD** - Less frequent use
5. **Advanced 3D features** - Already mostly client-side

### Low Priority
6. **Optimization** - After core features work
7. **Fallbacks** - For old browsers

---

## 💻 Browser Compatibility

### WebGL 2.0 Support
- ✅ Chrome 56+ (2017)
- ✅ Firefox 51+ (2017)
- ✅ Safari 15+ (2021)
- ✅ Edge 79+ (2020)

### WebGPU Support (Future)
- ✅ Chrome 113+ (2023)
- ⏳ Firefox (in development)
- ⏳ Safari (in development)

### Fallback Strategy
```javascript
function getComputeBackend() {
    if (navigator.gpu) {
        return 'webgpu';  // Best performance
    } else if (hasWebGL2()) {
        return 'webgl';   // Good performance
    } else {
        return 'wasm';    // CPU fallback
    }
}
```

---

## 📊 Performance Expectations

### Client-Side GPU (Expected)
- **Segmentation**: 10-30s (vs 30-60s server)
- **Calcium Scoring**: <5s (vs 5-10s server)
- **Perfusion Maps**: <10s (vs 15-30s server)
- **3D Rendering**: 60 FPS (already achieved)

### Benefits
- ✅ No network latency
- ✅ Parallel processing per user
- ✅ Scales infinitely
- ✅ No server GPU costs

---

## 🔒 Security Considerations

### Data Privacy
- ✅ Medical images never leave browser
- ✅ Processing happens locally
- ✅ Only results sent to server (optional)

### Model Security
- ✅ Models served over HTTPS
- ✅ Model integrity verification
- ✅ No sensitive data in models

---

## 📝 Next Steps

1. **Create client-side ML module** (2 hours)
2. **Convert PyTorch models to ONNX** (1 hour)
3. **Implement WebGL compute shaders** (3 hours)
4. **Test on real medical data** (2 hours)
5. **Update documentation** (1 hour)

**Total Estimated Time**: 9 hours

---

## 🎓 Learning Resources

- [TensorFlow.js Guide](https://www.tensorflow.org/js/guide)
- [ONNX.js Documentation](https://onnxruntime.ai/docs/tutorials/web/)
- [WebGL Compute Shaders](https://webgl2fundamentals.org/)
- [GPU.js Examples](https://gpu.rocks/)

---

**Status**: Ready for implementation  
**Blocker**: None - All technologies available  
**Risk**: Low - Proven technologies
