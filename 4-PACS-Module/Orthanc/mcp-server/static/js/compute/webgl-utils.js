/**
 * WebGL Utility Functions - GPU Compute Helpers for PACS
 * Provides texture management, shader compilation, and GPU compute helpers
 * 
 * @author GPU Compute Team
 * @version 1.0.0
 * @date October 2025
 */

class WebGLComputeUtils {
    /**
     * Create and compile shader program
     * @param {WebGLRenderingContext} gl - WebGL context
     * @param {string} vertexSrc - Vertex shader source
     * @param {string} fragmentSrc - Fragment shader source
     * @returns {WebGLProgram} - Compiled program or null on error
     */
    static createProgram(gl, vertexSrc, fragmentSrc) {
        const vertexShader = this.compileShader(gl, gl.VERTEX_SHADER, vertexSrc);
        const fragmentShader = this.compileShader(gl, gl.FRAGMENT_SHADER, fragmentSrc);
        
        if (!vertexShader || !fragmentShader) {
            return null;
        }
        
        const program = gl.createProgram();
        gl.attachShader(program, vertexShader);
        gl.attachShader(program, fragmentShader);
        gl.linkProgram(program);
        
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            console.error('Program link error:', gl.getProgramInfoLog(program));
            gl.deleteShader(vertexShader);
            gl.deleteShader(fragmentShader);
            gl.deleteProgram(program);
            return null;
        }
        
        // Clean up after linking
        gl.deleteShader(vertexShader);
        gl.deleteShader(fragmentShader);
        
        return program;
    }
    
    /**
     * Compile individual shader
     * @param {WebGLRenderingContext} gl - WebGL context
     * @param {number} type - Shader type (VERTEX_SHADER or FRAGMENT_SHADER)
     * @param {string} source - Shader source code
     * @returns {WebGLShader} - Compiled shader or null on error
     */
    static compileShader(gl, type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            const typeStr = type === gl.VERTEX_SHADER ? 'Vertex' : 'Fragment';
            console.error(`${typeStr} shader compile error:`, gl.getShaderInfoLog(shader));
            gl.deleteShader(shader);
            return null;
        }
        
        return shader;
    }
    
    /**
     * Create 3D texture from volume data
     * @param {WebGLRenderingContext} gl - WebGL context
     * @param {Float32Array} volumeData - Volume voxel data
     * @param {Object} dimensions - {width, height, depth}
     * @returns {WebGLTexture} - 3D texture or null on error
     */
    static create3DTexture(gl, volumeData, dimensions) {
        if (!gl.getExtension('EXT_texture_3d')) {
            console.error('3D textures not supported');
            return null;
        }
        
        const texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_3D, texture);
        
        // Set texture parameters
        gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_WRAP_R, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        
        try {
            // Upload data with proper error handling
            gl.texImage3D(
                gl.TEXTURE_3D,
                0,
                gl.R32F,
                dimensions.width,
                dimensions.height,
                dimensions.depth,
                0,
                gl.RED,
                gl.FLOAT,
                volumeData
            );
            
            // Check for errors
            const err = gl.getError();
            if (err !== gl.NO_ERROR) {
                console.error('3D texture upload error:', err);
                gl.deleteTexture(texture);
                return null;
            }
        } catch (e) {
            console.error('Exception creating 3D texture:', e);
            gl.deleteTexture(texture);
            return null;
        }
        
        return texture;
    }
    
    /**
     * Create 2D texture from image data
     * @param {WebGLRenderingContext} gl - WebGL context
     * @param {Float32Array|Uint8Array} data - Texture data
     * @param {number} width - Texture width
     * @param {number} height - Texture height
     * @param {Object} options - {internalFormat, format, type, filter}
     * @returns {WebGLTexture} - 2D texture
     */
    static create2DTexture(gl, data, width, height, options = {}) {
        const {
            internalFormat = gl.R32F,
            format = gl.RED,
            type = gl.FLOAT,
            filter = gl.LINEAR
        } = options;
        
        const texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, texture);
        
        // Set parameters
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
        
        // Upload data
        gl.texImage2D(gl.TEXTURE_2D, 0, internalFormat, width, height, 0, 
                      format, type, data);
        
        return texture;
    }
    
    /**
     * Create framebuffer for off-screen rendering
     * @param {WebGLRenderingContext} gl - WebGL context
     * @param {number} width - Framebuffer width
     * @param {number} height - Framebuffer height
     * @returns {Object} - {framebuffer, texture, renderbuffer} or null on error
     */
    static createFramebuffer(gl, width, height) {
        const framebuffer = gl.createFramebuffer();
        gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
        
        // Create color texture
        const texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, texture);
        
        // Allocate texture storage
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, width, height, 0, 
                      gl.RGBA, gl.FLOAT, null);
        
        // Set parameters
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        
        // Attach texture to framebuffer
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0,
                                gl.TEXTURE_2D, texture, 0);
        
        // Create and attach depth renderbuffer
        const renderbuffer = gl.createRenderbuffer();
        gl.bindRenderbuffer(gl.RENDERBUFFER, renderbuffer);
        gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT24, width, height);
        gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT,
                                   gl.RENDERBUFFER, renderbuffer);
        
        // Check framebuffer status
        const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
        if (status !== gl.FRAMEBUFFER_COMPLETE) {
            console.error('Framebuffer incomplete, status:', status);
            gl.deleteFramebuffer(framebuffer);
            gl.deleteTexture(texture);
            gl.deleteRenderbuffer(renderbuffer);
            return null;
        }
        
        return { framebuffer, texture, renderbuffer };
    }
    
    /**
     * Create vertex array object for fullscreen quad
     * @param {WebGLRenderingContext} gl - WebGL context
     * @param {WebGLProgram} program - Shader program
     * @returns {Object} - {vao, vertexCount, vbo, ebo}
     */
    static createFullscreenQuad(gl, program) {
        // Vertex data: position (2), texCoord (2)
        const vertices = new Float32Array([
            -1, -1,  0, 0,
             1, -1,  1, 0,
            -1,  1,  0, 1,
             1,  1,  1, 1
        ]);
        
        // Element indices
        const indices = new Uint16Array([
            0, 1, 2,
            1, 3, 2
        ]);
        
        // Create VBO
        const vbo = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
        gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
        
        // Create EBO
        const ebo = gl.createBuffer();
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ebo);
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
        
        // Create VAO
        const vao = gl.createVertexArray();
        gl.bindVertexArray(vao);
        
        gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ebo);
        
        // Position attribute
        const posLoc = gl.getAttribLocation(program, 'position');
        gl.enableVertexAttribArray(posLoc);
        gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 16, 0);
        
        // TexCoord attribute
        const texLoc = gl.getAttribLocation(program, 'texCoord');
        gl.enableVertexAttribArray(texLoc);
        gl.vertexAttribPointer(texLoc, 2, gl.FLOAT, false, 16, 8);
        
        return { vao, vertexCount: 6, vbo, ebo };
    }
    
    /**
     * Read pixels from GPU back to CPU (async)
     * @param {WebGLRenderingContext} gl - WebGL context
     * @param {number} width - Pixel width
     * @param {number} height - Pixel height
     * @param {Object} options - {format, type}
     * @returns {Promise<TypedArray>} - Pixel data
     */
    static async readPixels(gl, width, height, options = {}) {
        const {
            format = gl.RGBA,
            type = gl.UNSIGNED_BYTE
        } = options;
        
        const pixelSize = format === gl.RGBA ? 4 : (format === gl.RGB ? 3 : 1);
        const PixelType = type === gl.FLOAT ? Float32Array : Uint8Array;
        
        return new Promise((resolve, reject) => {
            try {
                const pixels = new PixelType(width * height * pixelSize);
                
                // Use pixel buffer objects for async read if available
                const ext = gl.getExtension('EXT_pixel_pack_buffer');
                if (ext) {
                    const pbo = gl.createBuffer();
                    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, pbo);
                    gl.bufferData(gl.PIXEL_PACK_BUFFER, pixels.byteLength, gl.STREAM_READ);
                    
                    gl.readPixels(0, 0, width, height, format, type, pixels);
                    
                    // Read from PBO
                    const mapBuffer = gl.getBufferSubData(gl.PIXEL_PACK_BUFFER, 0, pixels);
                    gl.deleteBuffer(pbo);
                    
                    gl.finish();
                    resolve(mapBuffer || pixels);
                } else {
                    // Fallback: synchronous read
                    gl.readPixels(0, 0, width, height, format, type, pixels);
                    gl.finish();
                    resolve(pixels);
                }
            } catch (error) {
                reject(error);
            }
        });
    }
    
    /**
     * Check if WebGL extension is available
     * @param {WebGLRenderingContext} gl - WebGL context
     * @param {string} extensionName - Extension name
     * @returns {boolean} - Whether extension is available
     */
    static hasExtension(gl, extensionName) {
        try {
            const ext = gl.getExtension(extensionName);
            return ext !== null;
        } catch (e) {
            return false;
        }
    }
    
    /**
     * Get GPU capabilities and limitations
     * @param {WebGLRenderingContext} gl - WebGL context
     * @returns {Object} - GPU capabilities
     */
    static getCapabilities(gl) {
        return {
            version: gl.getParameter(gl.VERSION),
            renderer: gl.getParameter(gl.RENDERER),
            vendor: gl.getParameter(gl.VENDOR),
            maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
            max3DTextureSize: this.hasExtension(gl, 'EXT_texture_3d') ? 
                              gl.getParameter(gl.MAX_3D_TEXTURE_SIZE) : 0,
            maxRenderbufferSize: gl.getParameter(gl.MAX_RENDERBUFFER_SIZE),
            maxViewportDims: gl.getParameter(gl.MAX_VIEWPORT_DIMS),
            maxUniformComponents: gl.getParameter(gl.MAX_VERTEX_UNIFORM_COMPONENTS),
            maxVaryingVectors: gl.getParameter(gl.MAX_VARYING_VECTORS),
            maxTextureImageUnits: gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS),
            hasFloat32: this.hasExtension(gl, 'EXT_color_buffer_float'),
            hasFloat16: this.hasExtension(gl, 'EXT_color_buffer_half_float'),
            hasAnisotropic: this.hasExtension(gl, 'EXT_texture_filter_anisotropic'),
            hasCompressed: this.hasExtension(gl, 'WEBGL_compressed_texture_s3tc'),
            hasDrawBuffers: this.hasExtension(gl, 'WEBGL_draw_buffers'),
            hasDebugInfo: this.hasExtension(gl, 'WEBGL_debug_renderer_info'),
            maxDrawBuffers: this.hasExtension(gl, 'WEBGL_draw_buffers') ? 
                           gl.getParameter(gl.MAX_DRAW_BUFFERS_WEBGL) : 1
        };
    }
    
    /**
     * Validate shader compilation
     * @param {WebGLRenderingContext} gl - WebGL context
     * @param {string} source - Shader source code
     * @param {number} type - Shader type
     * @returns {Object} - {valid, error}
     */
    static validateShader(gl, source, type) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        
        const valid = gl.getShaderParameter(shader, gl.COMPILE_STATUS);
        const error = valid ? null : gl.getShaderInfoLog(shader);
        
        gl.deleteShader(shader);
        
        return { valid, error };
    }
    
    /**
     * Cleanup WebGL resources
     * @param {WebGLRenderingContext} gl - WebGL context
     * @param {Array<WebGLResource>} resources - Resources to delete
     */
    static cleanup(gl, resources) {
        for (const resource of resources) {
            if (!resource) continue;
            
            if (resource instanceof WebGLProgram) {
                gl.deleteProgram(resource);
            } else if (resource instanceof WebGLShader) {
                gl.deleteShader(resource);
            } else if (resource instanceof WebGLTexture) {
                gl.deleteTexture(resource);
            } else if (resource instanceof WebGLFramebuffer) {
                gl.deleteFramebuffer(resource);
            } else if (resource instanceof WebGLRenderbuffer) {
                gl.deleteRenderbuffer(resource);
            } else if (resource instanceof WebGLBuffer) {
                gl.deleteBuffer(resource);
            } else if (resource instanceof WebGLVertexArrayObject) {
                gl.deleteVertexArray(resource);
            }
        }
    }
    
    /**
     * Log GPU debug information
     * @param {WebGLRenderingContext} gl - WebGL context
     */
    static logDebugInfo(gl) {
        const caps = this.getCapabilities(gl);
        console.group('WebGL Debug Info');
        console.log('Version:', caps.version);
        console.log('Renderer:', caps.renderer);
        console.log('Vendor:', caps.vendor);
        console.log('Max Texture Size:', caps.maxTextureSize);
        console.log('Max 3D Texture Size:', caps.max3DTextureSize);
        console.log('Float32 Support:', caps.hasFloat32);
        console.log('Float16 Support:', caps.hasFloat16);
        console.log('Max Draw Buffers:', caps.maxDrawBuffers);
        console.groupEnd();
    }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebGLComputeUtils;
}
