/**
 * Viewport Manager
 * Handles canvas rendering, transformations, and GPU acceleration
 */

export class ViewportManager {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d', {
      willReadFrequently: true,
      alpha: false,
      desynchronized: true // Better performance
    });
    
    this.options = {
      enableGPU: options.enableGPU !== false,
      enableCaching: options.enableCaching !== false,
      ...options
    };
    
    this.imageCache = new Map();
    this.offscreenCanvas = null;
    
    if (this.options.enableGPU && typeof OffscreenCanvas !== 'undefined') {
      this.offscreenCanvas = new OffscreenCanvas(canvas.width, canvas.height);
    }
  }

  /**
   * Render image with transformations
   */
  render(imageData, transforms = {}) {
    const {
      zoom = 1.0,
      pan = { x: 0, y: 0 },
      rotation = 0,
      flip = { horizontal: false, vertical: false }
    } = transforms;
    
    // Save context state
    this.ctx.save();
    
    // Clear canvas
    this.ctx.fillStyle = '#000';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Apply transformations
    this.ctx.translate(this.canvas.width / 2, this.canvas.height / 2);
    this.ctx.rotate((rotation * Math.PI) / 180);
    this.ctx.scale(
      zoom * (flip.horizontal ? -1 : 1),
      zoom * (flip.vertical ? -1 : 1)
    );
    this.ctx.translate(-this.canvas.width / 2 + pan.x, -this.canvas.height / 2 + pan.y);
    
    // Draw image
    this.ctx.putImageData(imageData, 0, 0);
    
    // Restore context state
    this.ctx.restore();
  }

  /**
   * Apply image enhancement
   */
  enhance(imageData, options = {}) {
    const {
      sharpen = false,
      denoise = false,
      contrast = 1.0,
      brightness = 0
    } = options;
    
    if (sharpen) {
      return this.applySharpen(imageData);
    }
    
    if (denoise) {
      return this.applyDenoise(imageData);
    }
    
    if (contrast !== 1.0 || brightness !== 0) {
      return this.adjustContrastBrightness(imageData, contrast, brightness);
    }
    
    return imageData;
  }

  /**
   * Apply sharpening filter
   */
  applySharpen(imageData) {
    const kernel = [
      0, -1, 0,
      -1, 5, -1,
      0, -1, 0
    ];
    
    return this.applyConvolution(imageData, kernel);
  }

  /**
   * Apply denoising (simple blur)
   */
  applyDenoise(imageData) {
    const kernel = [
      1/9, 1/9, 1/9,
      1/9, 1/9, 1/9,
      1/9, 1/9, 1/9
    ];
    
    return this.applyConvolution(imageData, kernel);
  }

  /**
   * Apply convolution kernel
   */
  applyConvolution(imageData, kernel) {
    const width = imageData.width;
    const height = imageData.height;
    const src = imageData.data;
    const dst = new Uint8ClampedArray(src.length);
    
    for (let y = 1; y < height - 1; y++) {
      for (let x = 1; x < width - 1; x++) {
        let r = 0, g = 0, b = 0;
        
        for (let ky = -1; ky <= 1; ky++) {
          for (let kx = -1; kx <= 1; kx++) {
            const idx = ((y + ky) * width + (x + kx)) * 4;
            const k = kernel[(ky + 1) * 3 + (kx + 1)];
            
            r += src[idx] * k;
            g += src[idx + 1] * k;
            b += src[idx + 2] * k;
          }
        }
        
        const idx = (y * width + x) * 4;
        dst[idx] = Math.max(0, Math.min(255, r));
        dst[idx + 1] = Math.max(0, Math.min(255, g));
        dst[idx + 2] = Math.max(0, Math.min(255, b));
        dst[idx + 3] = src[idx + 3];
      }
    }
    
    return new ImageData(dst, width, height);
  }

  /**
   * Adjust contrast and brightness
   */
  adjustContrastBrightness(imageData, contrast, brightness) {
    const data = new Uint8ClampedArray(imageData.data);
    const factor = (259 * (contrast + 255)) / (255 * (259 - contrast));
    
    for (let i = 0; i < data.length; i += 4) {
      data[i] = Math.max(0, Math.min(255, factor * (data[i] - 128) + 128 + brightness));
      data[i + 1] = Math.max(0, Math.min(255, factor * (data[i + 1] - 128) + 128 + brightness));
      data[i + 2] = Math.max(0, Math.min(255, factor * (data[i + 2] - 128) + 128 + brightness));
    }
    
    return new ImageData(data, imageData.width, imageData.height);
  }

  /**
   * Cache image for faster access
   */
  cacheImage(key, imageData) {
    if (this.options.enableCaching) {
      this.imageCache.set(key, imageData);
    }
  }

  /**
   * Get cached image
   */
  getCachedImage(key) {
    return this.imageCache.get(key);
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.imageCache.clear();
  }

  /**
   * Resize canvas
   */
  resize(width, height) {
    this.canvas.width = width;
    this.canvas.height = height;
    
    if (this.offscreenCanvas) {
      this.offscreenCanvas.width = width;
      this.offscreenCanvas.height = height;
    }
  }
}
