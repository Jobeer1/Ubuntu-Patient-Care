# Segmentation Overlay Renderer - Technical Specification

**Version**: 1.0  
**Target File**: `static/js/viewers/segmentation-overlay.js`  
**Lines Required**: 400+ production code  
**Quality Standard**: Best-in-the-world medical imaging visualization  
**Performance Target**: >50fps with GPU acceleration  

---

## 1. Architecture Overview

### System Design

```
┌─────────────────────────────────────────────────────────┐
│                   Web Browser                             │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  SegmentationOverlay Class (GPU-Accelerated)            │
│  ├── WebGL Context Management                          │
│  ├── Shader Programs (Vertex + Fragment)               │
│  ├── Texture Buffer Management                         │
│  └── Event Handling & UI Integration                   │
│                                                           │
│  ↓ API Integration                                       │
│  FastAPI Segmentation Endpoints                         │
│  ├── /api/segment/organs                               │
│  ├── /api/segment/vessels                              │
│  └── /api/segment/nodules                              │
│                                                           │
│  ↓ Backend Processing                                   │
│  Python ML Pipeline                                     │
│  ├── MONAI Models (UNETR, UNet)                       │
│  ├── GPU Inference                                      │
│  └── Mask Post-Processing                              │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### Class Hierarchy

```javascript
SegmentationOverlay
├── WebGL Management
│   ├── gl.createShader()
│   ├── gl.createProgram()
│   └── gl.createTexture()
├── Data Management
│   ├── Mask Data Loading
│   ├── Texture Binding
│   └── Buffer Management
├── Rendering
│   ├── Vertex Shader Processing
│   ├── Fragment Shader Processing
│   └── Compositing
├── Interaction
│   ├── Opacity Control
│   ├── Organ Selection
│   └── Highlighting
└── Export
    ├── PNG Generation
    ├── NIfTI Export
    └── JSON Statistics
```

---

## 2. WebGL Rendering Pipeline

### 2.1 Texture Format Specifications

**For Organ Segmentation (14 classes)**:
```javascript
// Texture storing organ class indices (0-14)
{
  format: WebGL2RenderingContext.RED,           // Single channel
  internalFormat: WebGL2RenderingContext.R8UI,  // Unsigned integer 0-255
  type: WebGL2RenderingContext.UNSIGNED_BYTE,   // 8-bit precision
  width: 512,                                    // Common medical imaging
  height: 512,
  depth: 512                                     // 3D texture
}

// Alternative for probability maps
{
  format: WebGL2RenderingContext.RED,
  internalFormat: WebGL2RenderingContext.R32F,  // 32-bit float
  type: WebGL2RenderingContext.FLOAT,
  width: 512,
  height: 512,
  depth: 512
}
```

**Color Map Texture (Lookup Table)**:
```javascript
// 14 colors × 4 bytes (RGBA) = 56 bytes per row
{
  format: WebGL2RenderingContext.RGBA,
  internalFormat: WebGL2RenderingContext.RGBA8,
  type: WebGL2RenderingContext.UNSIGNED_BYTE,
  width: 14,                                     // 14 organ colors
  height: 1,
  data: colorPaletteData                        // Pre-computed
}
```

### 2.2 Shader Programs

**Vertex Shader** (GPU-side position transformation):
```glsl
#version 300 es
precision highp float;

// Input vertex attributes
in vec3 position;
in vec2 texCoord;

// Uniform matrices for transformation
uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;

// Output to fragment shader
out vec2 vTexCoord;
out vec3 vWorldPos;

void main() {
  // Transform position to world space
  vWorldPos = (modelViewMatrix * vec4(position, 1.0)).xyz;
  vTexCoord = texCoord;
  
  // Transform to clip space
  gl_Position = projectionMatrix * vec4(vWorldPos, 1.0);
}
```

**Fragment Shader** (GPU-side color computation):
```glsl
#version 300 es
precision highp float;

// Input from vertex shader
in vec2 vTexCoord;
in vec3 vWorldPos;

// Texture samplers
uniform sampler2D maskTexture;        // Segmentation mask (0-14)
uniform sampler2D colorMapTexture;    // Organ colors (14×1 RGBA)
uniform sampler2D volumeTexture;      // Background volume

// Control uniforms
uniform float opacity;                 // 0.0 - 1.0
uniform int highlightedOrgan;          // -1 for none, 0-14 for organ
uniform bool showBoundary;             // Edge detection on/off

// Output color
out vec4 FragColor;

void main() {
  // Sample segmentation mask
  vec4 maskSample = texture(maskTexture, vTexCoord);
  int organId = int(maskSample.r * 255.0);  // Convert to 0-14
  
  // Skip background (organId == 0)
  if (organId == 0) {
    discard;
  }
  
  // Look up organ color from color map
  float colorIndex = float(organId) / 14.0;
  vec4 organColor = texture(colorMapTexture, vec2(colorIndex, 0.5));
  
  // Apply highlighting if enabled
  if (organId == highlightedOrgan && highlightedOrgan >= 0) {
    // Brighten highlighted organ by 30%
    organColor.rgb = mix(organColor.rgb, vec3(1.0), 0.3);
    
    // Add glow effect
    organColor.rgb += vec3(0.1);
  }
  
  // Edge detection for boundary display
  if (showBoundary) {
    // Simple Sobel-like edge detection
    vec4 neighbors[4];
    neighbors[0] = texture(maskTexture, vTexCoord + vec2(1.0/512.0, 0.0));
    neighbors[1] = texture(maskTexture, vTexCoord - vec2(1.0/512.0, 0.0));
    neighbors[2] = texture(maskTexture, vTexCoord + vec2(0.0, 1.0/512.0));
    neighbors[3] = texture(maskTexture, vTexCoord - vec2(0.0, 1.0/512.0));
    
    bool isEdge = false;
    for (int i = 0; i < 4; i++) {
      if (int(neighbors[i].r * 255.0) != organId) {
        isEdge = true;
        break;
      }
    }
    
    if (isEdge) {
      organColor.rgb = vec3(1.0);  // White boundary
    }
  }
  
  // Apply opacity and blend
  FragColor = vec4(organColor.rgb, opacity);
}
```

### 2.3 Texture Binding

```javascript
// Create and bind 3D mask texture
function createMaskTexture(maskData3D) {
  const texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_3D, texture);
  
  // Set texture parameters
  gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_WRAP_R, gl.CLAMP_TO_EDGE);
  
  // Load texture data
  gl.texImage3D(
    gl.TEXTURE_3D,
    0,                          // mip level
    gl.R8UI,                   // internal format
    512, 512, 512,             // dimensions
    0,                         // border
    gl.RED,                    // format
    gl.UNSIGNED_BYTE,          // type
    maskData3D                 // data
  );
  
  return texture;
}

// Bind color lookup table
function createColorMapTexture(colors) {
  const texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, texture);
  
  // Flatten color array: [r, g, b, a, r, g, b, a, ...] for 14 organs
  const colorData = new Uint8Array(14 * 4);
  colors.forEach((color, idx) => {
    colorData[idx * 4 + 0] = color.r;
    colorData[idx * 4 + 1] = color.g;
    colorData[idx * 4 + 2] = color.b;
    colorData[idx * 4 + 3] = 255;  // Full alpha
  });
  
  gl.texImage2D(
    gl.TEXTURE_2D,
    0,
    gl.RGBA,
    14, 1,
    0,
    gl.RGBA,
    gl.UNSIGNED_BYTE,
    colorData
  );
  
  return texture;
}
```

---

## 3. SegmentationOverlay Class API

### 3.1 Constructor

```javascript
class SegmentationOverlay {
  /**
   * Initialize GPU-accelerated segmentation overlay
   * 
   * @param {THREE.WebGLRenderer} renderer - Three.js renderer
   * @param {object} volumeData - 3D volume data {data, width, height, depth}
   * @param {object} segmentationData - Segmentation mask data {data, affine}
   * @throws {Error} If WebGL2 not supported
   */
  constructor(renderer, volumeData, segmentationData) {
    this.renderer = renderer;
    this.gl = renderer.getContext();
    
    // Verify WebGL 2.0 support
    if (!this.gl) {
      throw new Error('WebGL 2.0 not supported');
    }
    
    // Initialize WebGL resources
    this.textures = {};
    this.shaders = {};
    this.buffers = {};
    this.uniforms = {};
    this.state = {
      opacity: 0.5,
      highlightedOrgan: -1,
      showBoundary: false,
      visible: true
    };
    
    // Performance monitoring
    this.stats = {
      frameTime: 0,
      gpuMemory: 0,
      fps: 0
    };
    
    // Compile shaders and create textures
    this._initializeShaders();
    this._initializeMaskTexture(segmentationData);
    this._initializeColorMap();
  }
}
```

### 3.2 Core Methods

#### loadMask()
```javascript
/**
 * Load segmentation mask from API response or raw data
 * 
 * @param {Uint8Array|object} maskData - Segmentation mask (3D array or API response)
 * @param {Float32Array} [affineMatrix] - Affine transformation (4×4)
 * @returns {Promise<object>} Load status {success, loadTime, memoryUsed}
 * 
 * @example
 * const result = await overlay.loadMask(maskData, affineMatrix);
 * console.log(`Loaded in ${result.loadTime}ms`);
 */
async loadMask(maskData, affineMatrix = null) {
  const startTime = performance.now();
  
  try {
    // Handle API response format
    if (maskData.data && maskData.meta) {
      maskData = new Uint8Array(maskData.data);
      affineMatrix = maskData.affine;
    }
    
    // Verify data size (512×512×512 = 134MB for 8-bit)
    if (maskData.length !== 512 * 512 * 512) {
      throw new Error(`Invalid mask size: ${maskData.length}`);
    }
    
    // Update texture asynchronously to avoid blocking
    await this._updateMaskTexture(maskData);
    
    // Store affine matrix for export
    this.affineMatrix = affineMatrix || Matrix4.identity();
    
    const loadTime = performance.now() - startTime;
    this.stats.gpuMemory = this._calculateGPUMemory();
    
    return {
      success: true,
      loadTime,
      memoryUsed: this.stats.gpuMemory,
      dimensions: {width: 512, height: 512, depth: 512}
    };
  } catch (error) {
    console.error('Mask loading failed:', error);
    return {success: false, error: error.message};
  }
}

// Helper: Asynchronously update texture
async _updateMaskTexture(maskData) {
  return new Promise((resolve, reject) => {
    try {
      this.gl.bindTexture(this.gl.TEXTURE_3D, this.textures.mask);
      this.gl.texImage3D(
        this.gl.TEXTURE_3D, 0, this.gl.R8UI,
        512, 512, 512, 0,
        this.gl.RED, this.gl.UNSIGNED_BYTE, maskData
      );
      resolve();
    } catch (error) {
      reject(error);
    }
  });
}
```

#### setOpacity()
```javascript
/**
 * Set mask opacity/transparency
 * 
 * @param {number} opacity - Opacity value (0.0 = transparent, 1.0 = opaque)
 * @returns {void}
 * 
 * @example
 * overlay.setOpacity(0.7);  // 70% opaque
 * overlay.setOpacity(0.3);  // 30% opaque (very transparent)
 */
setOpacity(opacity) {
  // Clamp to valid range
  this.state.opacity = Math.max(0.0, Math.min(1.0, opacity));
  
  // Update shader uniform
  this.gl.useProgram(this.shaders.program);
  const opacityLoc = this.gl.getUniformLocation(
    this.shaders.program, 
    'opacity'
  );
  this.gl.uniform1f(opacityLoc, this.state.opacity);
  
  // Trigger re-render
  this._render();
}

// Property getter for UI binding
get opacity() {
  return this.state.opacity;
}

// Property setter for reactive updates
set opacity(value) {
  this.setOpacity(value);
}
```

#### setColor()
```javascript
/**
 * Define or update color for specific organ
 * 
 * @param {string|number} organ - Organ name or ID (0-14)
 * @param {string|object} color - Color as hex string or {r, g, b} object
 * @returns {void}
 * 
 * @example
 * overlay.setColor('Spleen', '#FF0000');
 * overlay.setColor(1, {r: 255, g: 0, b: 0});
 * overlay.setColor(6, '#00FF00');  // Liver to green
 */
setColor(organ, color) {
  // Resolve organ ID
  const organId = typeof organ === 'string' 
    ? this._getOrganId(organ) 
    : organ;
  
  if (organId < 0 || organId > 14) {
    throw new Error(`Invalid organ ID: ${organId}`);
  }
  
  // Parse color
  const rgbColor = this._parseColor(color);
  
  // Update color palette
  this.colorPalette[organId] = rgbColor;
  
  // Update GPU color map texture
  this._updateColorMapTexture();
  
  // Trigger re-render
  this._render();
}

// Helper: Parse color formats
_parseColor(color) {
  if (typeof color === 'string') {
    // Parse hex color (#RRGGBB)
    const hex = color.replace('#', '');
    return {
      r: parseInt(hex.substring(0, 2), 16),
      g: parseInt(hex.substring(2, 4), 16),
      b: parseInt(hex.substring(4, 6), 16)
    };
  }
  return color;  // Assume {r, g, b} format
}
```

#### highlightOrgan()
```javascript
/**
 * Highlight or emphasize specific organ with visual effects
 * 
 * @param {string|number} organ - Organ name or ID
 * @param {boolean} [enabled=true] - Enable/disable highlighting
 * @returns {void}
 * 
 * @example
 * overlay.highlightOrgan('Liver', true);    // Highlight liver
 * overlay.highlightOrgan('Spleen', false);  // Remove highlight
 * overlay.highlightOrgan(6);                // Highlight organ ID 6
 */
highlightOrgan(organ, enabled = true) {
  const organId = typeof organ === 'string'
    ? this._getOrganId(organ)
    : organ;
  
  if (!enabled) {
    this.state.highlightedOrgan = -1;
  } else {
    this.state.highlightedOrgan = organId;
  }
  
  // Update shader uniform
  this.gl.useProgram(this.shaders.program);
  const highlightLoc = this.gl.getUniformLocation(
    this.shaders.program,
    'highlightedOrgan'
  );
  this.gl.uniform1i(highlightLoc, this.state.highlightedOrgan);
  
  // Optional: Add border/outline effect
  if (enabled) {
    this._drawOrganOutline(organId);
  }
  
  // Trigger re-render
  this._render();
}

// Helper: Organ name to ID mapping
_getOrganId(name) {
  const organMap = {
    'spleen': 1, 'right kidney': 2, 'left kidney': 3,
    'gallbladder': 4, 'esophagus': 5, 'liver': 6,
    'stomach': 7, 'aorta': 8, 'ivc': 9,
    'portal vein': 10, 'pancreas': 11,
    'left adrenal': 12, 'right adrenal': 13, 'duodenum': 14
  };
  return organMap[name.toLowerCase()] ?? -1;
}
```

#### export()
```javascript
/**
 * Export segmentation visualization or mask data
 * 
 * @param {string} format - Export format ('png' | 'nifti' | 'json' | 'dicom')
 * @param {object} [options] - Format-specific options
 * @returns {Promise<Blob|object>} Exported data
 * 
 * @example
 * // Export current rendering as PNG
 * const pngBlob = await overlay.export('png');
 * downloadFile(pngBlob, 'segmentation.png');
 * 
 * // Export mask as NIfTI
 * const niftiBlob = await overlay.export('nifti', {
 *   affine: affineMatrix,
 *   metadata: {description: 'Organ segmentation'}
 * });
 * 
 * // Export statistics as JSON
 * const stats = await overlay.export('json');
 * console.log(stats.organs);
 */
async export(format, options = {}) {
  switch (format.toLowerCase()) {
    case 'png':
      return this._exportPNG(options);
    case 'nifti':
      return this._exportNIfTI(options);
    case 'json':
      return this._exportJSON(options);
    case 'dicom':
      return this._exportDICOM(options);
    default:
      throw new Error(`Unsupported format: ${format}`);
  }
}

// Helper: Export as PNG
async _exportPNG(options) {
  // Render to framebuffer
  const width = options.width || 512;
  const height = options.height || 512;
  
  // Create framebuffer
  const framebuffer = this.gl.createFramebuffer();
  this.gl.bindFramebuffer(this.gl.FRAMEBUFFER, framebuffer);
  
  // Render scene
  this._render();
  
  // Read pixels from framebuffer
  const pixels = new Uint8Array(width * height * 4);
  this.gl.readPixels(
    0, 0, width, height,
    this.gl.RGBA, this.gl.UNSIGNED_BYTE, pixels
  );
  
  // Convert to PNG using canvas
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  const imageData = ctx.createImageData(width, height);
  imageData.data.set(pixels);
  ctx.putImageData(imageData, 0, 0);
  
  return new Promise(resolve => {
    canvas.toBlob(blob => resolve(blob), 'image/png');
  });
}

// Helper: Export as NIfTI
async _exportNIfTI(options) {
  // Get mask data from GPU
  const maskData = this._readMaskFromGPU();
  
  // Create NIfTI header
  const header = {
    sizeof_hdr: 348,
    data_type: 'uint8',
    dim: [3, 512, 512, 512, 1, 1, 1, 1],
    pixdim: [1.0, options.voxelSize || 1.0, options.voxelSize || 1.0, options.voxelSize || 1.0],
    affine: options.affine || this.affineMatrix
  };
  
  // Encode NIfTI file
  const niftiData = this._encodeNIfTI(maskData, header);
  return new Blob([niftiData], {type: 'application/nifti'});
}

// Helper: Export statistics as JSON
async _exportJSON(options) {
  const stats = this._calculateStatistics();
  
  return {
    timestamp: new Date().toISOString(),
    format: 'segmentation-statistics',
    volume: {
      dimensions: [512, 512, 512],
      voxelSize: options.voxelSize || 1.0
    },
    organs: stats,
    colorPalette: this.colorPalette,
    affine: this.affineMatrix
  };
}
```

#### render()
```javascript
/**
 * Render overlay to canvas (internal use)
 * Called automatically on updates; can be called manually for debugging
 * 
 * @returns {void}
 * 
 * @private
 */
_render() {
  // Update performance counter
  const frameStart = performance.now();
  
  // Use shader program
  this.gl.useProgram(this.shaders.program);
  
  // Bind textures
  this.gl.activeTexture(this.gl.TEXTURE0);
  this.gl.bindTexture(this.gl.TEXTURE_3D, this.textures.mask);
  this.gl.uniform1i(this.gl.getUniformLocation(this.shaders.program, 'maskTexture'), 0);
  
  this.gl.activeTexture(this.gl.TEXTURE1);
  this.gl.bindTexture(this.gl.TEXTURE_2D, this.textures.colorMap);
  this.gl.uniform1i(this.gl.getUniformLocation(this.shaders.program, 'colorMapTexture'), 1);
  
  // Update uniforms
  this.gl.uniform1f(
    this.gl.getUniformLocation(this.shaders.program, 'opacity'),
    this.state.opacity
  );
  
  this.gl.uniform1i(
    this.gl.getUniformLocation(this.shaders.program, 'highlightedOrgan'),
    this.state.highlightedOrgan
  );
  
  this.gl.uniform1i(
    this.gl.getUniformLocation(this.shaders.program, 'showBoundary'),
    this.state.showBoundary ? 1 : 0
  );
  
  // Draw quad
  this.gl.drawArrays(this.gl.TRIANGLES, 0, 6);
  
  // Update performance stats
  this.stats.frameTime = performance.now() - frameStart;
  this.stats.fps = 1000 / this.stats.frameTime;
}
```

#### dispose()
```javascript
/**
 * Clean up GPU resources and memory
 * Call when overlay is no longer needed
 * 
 * @returns {void}
 * 
 * @example
 * overlay.dispose();
 */
dispose() {
  // Clean up textures
  Object.values(this.textures).forEach(texture => {
    this.gl.deleteTexture(texture);
  });
  
  // Clean up shader program
  this.gl.deleteProgram(this.shaders.program);
  this.gl.deleteShader(this.shaders.vertex);
  this.gl.deleteShader(this.shaders.fragment);
  
  // Clean up buffers
  Object.values(this.buffers).forEach(buffer => {
    this.gl.deleteBuffer(buffer);
  });
  
  // Clear references
  this.textures = {};
  this.shaders = {};
  this.buffers = {};
  
  console.log('SegmentationOverlay disposed successfully');
}
```

---

## 4. 14-Organ Medical Color Palette

### Color Specifications

```javascript
const ORGAN_COLORS = {
  0: { name: 'Background', hex: '#000000', rgb: [0, 0, 0] },
  1: { name: 'Spleen', hex: '#E74C3C', rgb: [231, 76, 60] },           // Red
  2: { name: 'Right Kidney', hex: '#3498DB', rgb: [52, 152, 219] },    // Blue
  3: { name: 'Left Kidney', hex: '#2980B9', rgb: [41, 128, 185] },     // Dark Blue
  4: { name: 'Gallbladder', hex: '#F39C12', rgb: [243, 156, 18] },     // Orange
  5: { name: 'Esophagus', hex: '#E67E22', rgb: [230, 126, 34] },       // Dark Orange
  6: { name: 'Liver', hex: '#27AE60', rgb: [39, 174, 96] },            // Green
  7: { name: 'Stomach', hex: '#16A085', rgb: [22, 160, 133] },         // Teal
  8: { name: 'Aorta', hex: '#8E44AD', rgb: [142, 68, 173] },           // Purple
  9: { name: 'IVC', hex: '#9B59B6', rgb: [155, 89, 182] },             // Light Purple
  10: { name: 'Portal Vein', hex: '#C0392B', rgb: [192, 57, 43] },     // Dark Red
  11: { name: 'Pancreas', hex: '#F1C40F', rgb: [241, 196, 15] },       // Yellow
  12: { name: 'Left Adrenal', hex: '#95A5A6', rgb: [149, 165, 166] },  // Gray
  13: { name: 'Right Adrenal', hex: '#7F8C8D', rgb: [127, 140, 141] }, // Dark Gray
  14: { name: 'Duodenum', hex: '#D35400', rgb: [211, 84, 0] }          // Dark Orange
};

// Convert to WebGL-compatible format
const COLOR_MAP_DATA = Object.entries(ORGAN_COLORS)
  .map(([id, color]) => [color.rgb[0], color.rgb[1], color.rgb[2], 255])
  .flat();
```

---

## 5. Performance Specifications

### GPU Memory Budget

| Component | Size | Notes |
|-----------|------|-------|
| Mask Texture (512³, R8UI) | 128 MB | Primary segmentation data |
| Color Map (14×1, RGBA8) | 56 bytes | Negligible |
| Framebuffers (2×) | 8 MB | Double-buffering for smooth rendering |
| Shader Programs | <1 MB | Compiled GLSL |
| Buffers | <10 MB | Vertex/index buffers |
| **Total** | **~136 MB** | Well under 500 MB target |

### Frame Rate Targets

| Resolution | Target FPS | Hardware |
|------------|-----------|----------|
| 512×512 2D | >60 fps | Modern GPU (GTX 1060+) |
| 1024×1024 2D | >50 fps | Modern GPU |
| Volume raycasting | >30 fps | High-end GPU required |
| Expected typical | >50 fps | Standard medical workstation |

### Load Time Targets

| Operation | Target Time | Method |
|-----------|-------------|--------|
| Shader compilation | <500 ms | Precompiled, cached |
| Texture creation | <1 s | Async GPU transfer |
| Mask loading | <2 s | Streaming, LOD system |
| Color map update | <100 ms | CPU-side, cached |

---

## 6. Error Handling

### WebGL Errors

```javascript
// Comprehensive error checking
function checkGLError(operation) {
  const error = gl.getError();
  if (error !== gl.NO_ERROR) {
    const errorMap = {
      [gl.INVALID_ENUM]: 'Invalid enum',
      [gl.INVALID_VALUE]: 'Invalid value',
      [gl.INVALID_OPERATION]: 'Invalid operation',
      [gl.OUT_OF_MEMORY]: 'Out of memory',
      [gl.INVALID_FRAMEBUFFER_OPERATION]: 'Invalid framebuffer'
    };
    console.error(`WebGL Error in ${operation}: ${errorMap[error]}`);
    throw new Error(`WebGL error: ${errorMap[error]}`);
  }
}
```

### Resource Validation

```javascript
// Validate input data
function validateMaskData(maskData) {
  if (!maskData || !(maskData instanceof Uint8Array)) {
    throw new TypeError('Mask data must be Uint8Array');
  }
  if (maskData.length !== 512 * 512 * 512) {
    throw new Error(`Invalid mask size: ${maskData.length} (expected ${512*512*512})`);
  }
  // Check value range (0-14 for organ IDs)
  const max = Math.max(...maskData);
  if (max > 14) {
    console.warn(`Mask contains values > 14: max=${max}. Will be clamped.`);
  }
}
```

---

## 7. Testing Strategy

### Unit Tests

```javascript
describe('SegmentationOverlay', () => {
  let overlay, renderer, mockData;
  
  beforeEach(() => {
    renderer = new THREE.WebGLRenderer();
    mockData = generateMockSegmentation();
    overlay = new SegmentationOverlay(renderer, mockData.volume, mockData.segmentation);
  });
  
  afterEach(() => {
    overlay.dispose();
  });
  
  // Test opacity control
  it('should set opacity 0-1', () => {
    overlay.setOpacity(0.5);
    expect(overlay.opacity).toBe(0.5);
    
    overlay.setOpacity(-0.1);  // Clamped to 0
    expect(overlay.opacity).toBe(0);
    
    overlay.setOpacity(1.5);   // Clamped to 1
    expect(overlay.opacity).toBe(1);
  });
  
  // Test color mapping
  it('should update organ colors', () => {
    overlay.setColor('Liver', '#00FF00');
    const liverColor = overlay.colorPalette[6];
    expect(liverColor.r).toBe(0);
    expect(liverColor.g).toBe(255);
    expect(liverColor.b).toBe(0);
  });
  
  // Test highlighting
  it('should highlight organs', () => {
    overlay.highlightOrgan('Spleen', true);
    expect(overlay.state.highlightedOrgan).toBe(1);
    
    overlay.highlightOrgan('Spleen', false);
    expect(overlay.state.highlightedOrgan).toBe(-1);
  });
  
  // Test performance
  it('should render at >50 fps', () => {
    const fps = [];
    for (let i = 0; i < 100; i++) {
      overlay._render();
      fps.push(overlay.stats.fps);
    }
    const avgFps = fps.reduce((a, b) => a + b) / fps.length;
    expect(avgFps).toBeGreaterThan(50);
  });
});
```

### Integration Tests

```javascript
describe('Segmentation Integration', () => {
  it('should integrate with viewer HTML', async () => {
    // Load HTML viewer
    const viewer = new SegmentationViewer(
      document.getElementById('viewer-container')
    );
    
    // Create overlay
    const overlay = await viewer.createOverlay(mockSegmentationData);
    
    // Simulate user interactions
    viewer.opacitySlider.value = 0.7;
    viewer.opacitySlider.dispatchEvent(new Event('input'));
    
    expect(overlay.opacity).toBe(0.7);
  });
});
```

---

## 8. Integration with Existing Code

### HTML Viewer Integration

```html
<!-- static/viewers/segmentation-viewer.html -->
<div id="overlay-container"></div>

<script src="segmentation-overlay.js"></script>
<script>
  // Initialize overlay when viewer loads
  document.addEventListener('SegmentationLoaded', async (event) => {
    const overlay = new SegmentationOverlay(
      renderer,
      event.detail.volume,
      event.detail.segmentation
    );
    
    // Connect UI controls
    document.getElementById('opacity-slider').addEventListener('input', (e) => {
      overlay.setOpacity(e.target.value / 100);
    });
  });
</script>
```

### API Integration

```javascript
// Fetch segmentation from backend
async function loadSegmentationFromAPI(jobId) {
  try {
    const response = await fetch(`/api/segment/results/${jobId}`);
    const result = await response.json();
    
    // Load into overlay
    return await overlay.loadMask(
      result.mask_data,
      result.affine_matrix
    );
  } catch (error) {
    console.error('Failed to load segmentation:', error);
  }
}
```

---

## 9. Deliverables Checklist

### Code Completion
- [ ] SegmentationOverlay class (core)
- [ ] loadMask() method with error handling
- [ ] setOpacity() with smooth blending
- [ ] setColor() with palette support
- [ ] highlightOrgan() with effects
- [ ] export() with multiple formats
- [ ] render() with GPU optimization
- [ ] dispose() with cleanup
- [ ] 400+ lines total

### Performance
- [ ] >50fps frame rate verified
- [ ] <500MB GPU memory
- [ ] <2 second load time
- [ ] Responsive UI (<16ms)
- [ ] No memory leaks

### Quality
- [ ] WebGL best practices followed
- [ ] Comprehensive error handling
- [ ] Full JSDoc documentation
- [ ] Unit tests passing
- [ ] Integration tests passing

### Integration
- [ ] Works with segmentation-viewer.html
- [ ] API endpoints properly integrated
- [ ] Statistics display working
- [ ] Export functions tested
- [ ] Cross-browser compatible

---

## 10. References & Resources

### Medical Imaging Standards
- **NIfTI Format**: Brain Imaging Data Structure
- **DICOM Standard**: Digital Imaging and Communications in Medicine
- **MONAI Framework**: Medical Open Network for AI

### WebGL Documentation
- **Khronos WebGL Specification**: https://www.khronos.org/webgl/
- **Three.js Documentation**: https://threejs.org/docs/
- **WebGL 2.0 Best Practices**: Khronos best practices guide

### Reference Implementations
- **Three.js Medical Viewer**: Examples in Three.js repo
- **Babylon.js DICOM Viewer**: Reference implementation
- **ITK/VTK.js**: Open source medical imaging

---

**Document Version**: 1.0  
**Last Updated**: October 22, 2025  
**Status**: Ready for implementation ✅  
**Quality Standard**: Best-in-the-world medical imaging visualization 🏆
