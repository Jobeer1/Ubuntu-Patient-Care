/**
 * Advanced 3D Volume Renderer for Medical Imaging
 * GPU-accelerated rendering with WebGL 2.0 for CT, MRI, and Ultrasound
 */

class VolumeRenderer {
    constructor(canvas, options = {}) {
        this.canvas = canvas;
        this.gl = null;
        this.programs = {};
        this.textures = {};
        this.framebuffers = {};
        this.uniforms = {};
        
        // Rendering state
        this.camera = {
            position: [0, 0, 2],
            target: [0, 0, 0],
            up: [0, 1, 0],
            fov: 45,
            near: 0.1,
            far: 10
        };
        
        this.renderingMode = 'volume'; // 'volume', 'mip', 'minip', 'surface'
        this.qualityLevel = options.qualityLevel || 'high';
        this.volumeData = null;
        this.transferFunction = null;
        
        // South African optimization flags
        this.saOptimizations = {
            lowBandwidth: false,
            powerSave: false,
            mobileDevice: false
        };
        
        this.init();
    }

    /**
     * Initialize WebGL context and shaders
     */
    async init() {
        try {
            // Get WebGL 2.0 context
            this.gl = this.canvas.getContext('webgl2', {
                alpha: false,
                depth: true,
                stencil: false,
                antialias: true,
                premultipliedAlpha: false,
                preserveDrawingBuffer: false,
                powerPreference: 'high-performance'
            });

            if (!this.gl) {
                throw new Error('WebGL 2.0 not supported');
            }

            // Check for required extensions
            this.checkWebGLExtensions();
            
            // Initialize shaders
            await this.initShaders();
            
            // Initialize buffers and textures
            this.initBuffers();
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Detect South African optimizations
            this.detectSAOptimizations();
            
            console.log('Volume renderer initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize volume renderer:', error);
            throw error;
        }
    }

    /**
     * Check for required WebGL extensions
     */
    checkWebGLExtensions() {
        const requiredExtensions = [
            'EXT_color_buffer_float',
            'OES_texture_float_linear',
            'EXT_float_blend'
        ];

        const supportedExtensions = [];
        const unsupportedExtensions = [];

        requiredExtensions.forEach(ext => {
            if (this.gl.getExtension(ext)) {
                supportedExtensions.push(ext);
            } else {
                unsupportedExtensions.push(ext);
            }
        });

        if (unsupportedExtensions.length > 0) {
            console.warn('Some WebGL extensions not supported:', unsupportedExtensions);
            // Adjust quality level for compatibility
            if (this.qualityLevel === 'high') {
                this.qualityLevel = 'medium';
            }
        }
    }

    /**
     * Initialize shader programs
     */
    async initShaders() {
        // Volume rendering shaders
        this.programs.volume = await this.createShaderProgram(
            this.getVolumeVertexShader(),
            this.getVolumeFragmentShader()
        );

        // MIP (Maximum Intensity Projection) shaders
        this.programs.mip = await this.createShaderProgram(
            this.getVolumeVertexShader(),
            this.getMIPFragmentShader()
        );

        // Surface rendering shaders
        this.programs.surface = await this.createShaderProgram(
            this.getSurfaceVertexShader(),
            this.getSurfaceFragmentShader()
        );

        // Multi-planar reconstruction shaders
        this.programs.mpr = await this.createShaderProgram(
            this.getMPRVertexShader(),
            this.getMPRFragmentShader()
        );
    }

    /**
     * Create shader program from vertex and fragment shader source
     */
    async createShaderProgram(vertexSource, fragmentSource) {
        const vertexShader = this.compileShader(this.gl.VERTEX_SHADER, vertexSource);
        const fragmentShader = this.compileShader(this.gl.FRAGMENT_SHADER, fragmentSource);
        
        const program = this.gl.createProgram();
        this.gl.attachShader(program, vertexShader);
        this.gl.attachShader(program, fragmentShader);
        this.gl.linkProgram(program);
        
        if (!this.gl.getProgramParameter(program, this.gl.LINK_STATUS)) {
            const error = this.gl.getProgramInfoLog(program);
            throw new Error(`Shader program linking failed: ${error}`);
        }
        
        return program;
    }

    /**
     * Compile individual shader
     */
    compileShader(type, source) {
        const shader = this.gl.createShader(type);
        this.gl.shaderSource(shader, source);
        this.gl.compileShader(shader);
        
        if (!this.gl.getShaderParameter(shader, this.gl.COMPILE_STATUS)) {
            const error = this.gl.getShaderInfoLog(shader);
            throw new Error(`Shader compilation failed: ${error}`);
        }
        
        return shader;
    }

    /**
     * Volume rendering vertex shader
     */
    getVolumeVertexShader() {
        return `#version 300 es
        precision highp float;
        
        in vec3 a_position;
        in vec2 a_texCoord;
        
        uniform mat4 u_modelViewMatrix;
        uniform mat4 u_projectionMatrix;
        
        out vec3 v_rayDirection;
        out vec3 v_rayOrigin;
        out vec2 v_texCoord;
        
        void main() {
            gl_Position = u_projectionMatrix * u_modelViewMatrix * vec4(a_position, 1.0);
            
            // Calculate ray direction for volume rendering
            v_rayDirection = normalize(a_position);
            v_rayOrigin = a_position;
            v_texCoord = a_texCoord;
        }`;
    }

    /**
     * Volume rendering fragment shader
     */
    getVolumeFragmentShader() {
        return `#version 300 es
        precision highp float;
        
        in vec3 v_rayDirection;
        in vec3 v_rayOrigin;
        in vec2 v_texCoord;
        
        uniform sampler3D u_volumeTexture;
        uniform sampler2D u_transferFunction;
        uniform vec3 u_volumeDimensions;
        uniform vec3 u_volumeSpacing;
        uniform float u_stepSize;
        uniform vec2 u_windowLevel; // x = window, y = level
        uniform int u_maxSteps;
        uniform float u_alphaThreshold;
        
        // Lighting uniforms
        uniform vec3 u_lightDirection;
        uniform vec3 u_lightColor;
        uniform float u_ambient;
        
        out vec4 fragColor;
        
        vec3 calculateGradient(vec3 pos) {
            float stepSize = 1.0 / max(u_volumeDimensions.x, max(u_volumeDimensions.y, u_volumeDimensions.z));
            
            float dx = texture(u_volumeTexture, pos + vec3(stepSize, 0, 0)).r - 
                      texture(u_volumeTexture, pos - vec3(stepSize, 0, 0)).r;
            float dy = texture(u_volumeTexture, pos + vec3(0, stepSize, 0)).r - 
                      texture(u_volumeTexture, pos - vec3(0, stepSize, 0)).r;
            float dz = texture(u_volumeTexture, pos + vec3(0, 0, stepSize)).r - 
                      texture(u_volumeTexture, pos - vec3(0, 0, stepSize)).r;
            
            return normalize(vec3(dx, dy, dz));
        }
        
        vec4 applyTransferFunction(float intensity) {
            // Apply window/level
            float normalizedIntensity = (intensity - (u_windowLevel.y - u_windowLevel.x * 0.5)) / u_windowLevel.x;
            normalizedIntensity = clamp(normalizedIntensity, 0.0, 1.0);
            
            // Sample transfer function
            return texture(u_transferFunction, vec2(normalizedIntensity, 0.5));
        }
        
        void main() {
            vec3 rayDir = normalize(v_rayDirection);
            vec3 rayPos = v_rayOrigin * 0.5 + 0.5; // Transform to [0,1] range
            
            vec4 color = vec4(0.0);
            float alpha = 0.0;
            
            // Ray marching
            for (int i = 0; i < u_maxSteps; i++) {
                if (alpha >= u_alphaThreshold) break;
                
                // Check bounds
                if (any(lessThan(rayPos, vec3(0.0))) || any(greaterThan(rayPos, vec3(1.0)))) {
                    break;
                }
                
                // Sample volume
                float intensity = texture(u_volumeTexture, rayPos).r;
                vec4 sample = applyTransferFunction(intensity);
                
                if (sample.a > 0.01) {
                    // Calculate lighting
                    vec3 gradient = calculateGradient(rayPos);
                    float lighting = u_ambient + max(0.0, dot(gradient, -u_lightDirection));
                    
                    sample.rgb *= lighting * u_lightColor;
                    
                    // Alpha blending (front-to-back)
                    color.rgb += sample.rgb * sample.a * (1.0 - alpha);
                    alpha += sample.a * (1.0 - alpha);
                }
                
                rayPos += rayDir * u_stepSize;
            }
            
            fragColor = vec4(color.rgb, alpha);
        }`;
    }

    /**
     * MIP (Maximum Intensity Projection) fragment shader
     */
    getMIPFragmentShader() {
        return `#version 300 es
        precision highp float;
        
        in vec3 v_rayDirection;
        in vec3 v_rayOrigin;
        in vec2 v_texCoord;
        
        uniform sampler3D u_volumeTexture;
        uniform sampler2D u_transferFunction;
        uniform vec3 u_volumeDimensions;
        uniform float u_stepSize;
        uniform vec2 u_windowLevel;
        uniform int u_maxSteps;
        
        out vec4 fragColor;
        
        vec4 applyTransferFunction(float intensity) {
            float normalizedIntensity = (intensity - (u_windowLevel.y - u_windowLevel.x * 0.5)) / u_windowLevel.x;
            normalizedIntensity = clamp(normalizedIntensity, 0.0, 1.0);
            return texture(u_transferFunction, vec2(normalizedIntensity, 0.5));
        }
        
        void main() {
            vec3 rayDir = normalize(v_rayDirection);
            vec3 rayPos = v_rayOrigin * 0.5 + 0.5;
            
            float maxIntensity = 0.0;
            
            // Ray marching for MIP
            for (int i = 0; i < u_maxSteps; i++) {
                if (any(lessThan(rayPos, vec3(0.0))) || any(greaterThan(rayPos, vec3(1.0)))) {
                    break;
                }
                
                float intensity = texture(u_volumeTexture, rayPos).r;
                maxIntensity = max(maxIntensity, intensity);
                
                rayPos += rayDir * u_stepSize;
            }
            
            vec4 color = applyTransferFunction(maxIntensity);
            fragColor = vec4(color.rgb, 1.0);
        }`;
    }

    /**
     * Surface rendering vertex shader
     */
    getSurfaceVertexShader() {
        return `#version 300 es
        precision highp float;
        
        in vec3 a_position;
        in vec3 a_normal;
        
        uniform mat4 u_modelViewMatrix;
        uniform mat4 u_projectionMatrix;
        uniform mat3 u_normalMatrix;
        
        out vec3 v_normal;
        out vec3 v_position;
        
        void main() {
            vec4 worldPosition = u_modelViewMatrix * vec4(a_position, 1.0);
            gl_Position = u_projectionMatrix * worldPosition;
            
            v_normal = normalize(u_normalMatrix * a_normal);
            v_position = worldPosition.xyz;
        }`;
    }

    /**
     * Surface rendering fragment shader
     */
    getSurfaceFragmentShader() {
        return `#version 300 es
        precision highp float;
        
        in vec3 v_normal;
        in vec3 v_position;
        
        uniform vec3 u_lightDirection;
        uniform vec3 u_lightColor;
        uniform vec3 u_surfaceColor;
        uniform float u_ambient;
        uniform float u_shininess;
        
        out vec4 fragColor;
        
        void main() {
            vec3 normal = normalize(v_normal);
            vec3 lightDir = normalize(-u_lightDirection);
            
            // Diffuse lighting
            float diffuse = max(0.0, dot(normal, lightDir));
            
            // Specular lighting
            vec3 viewDir = normalize(-v_position);
            vec3 reflectDir = reflect(-lightDir, normal);
            float specular = pow(max(0.0, dot(viewDir, reflectDir)), u_shininess);
            
            vec3 color = u_surfaceColor * (u_ambient + diffuse) * u_lightColor + 
                        vec3(specular);
            
            fragColor = vec4(color, 1.0);
        }`;
    }

    /**
     * MPR vertex shader
     */
    getMPRVertexShader() {
        return `#version 300 es
        precision highp float;
        
        in vec3 a_position;
        in vec2 a_texCoord;
        
        uniform mat4 u_modelViewMatrix;
        uniform mat4 u_projectionMatrix;
        
        out vec2 v_texCoord;
        
        void main() {
            gl_Position = u_projectionMatrix * u_modelViewMatrix * vec4(a_position, 1.0);
            v_texCoord = a_texCoord;
        }`;
    }

    /**
     * MPR fragment shader
     */
    getMPRFragmentShader() {
        return `#version 300 es
        precision highp float;
        
        in vec2 v_texCoord;
        
        uniform sampler3D u_volumeTexture;
        uniform sampler2D u_transferFunction;
        uniform vec3 u_sliceNormal;
        uniform vec3 u_slicePosition;
        uniform vec2 u_windowLevel;
        uniform mat4 u_volumeMatrix;
        
        out vec4 fragColor;
        
        vec4 applyTransferFunction(float intensity) {
            float normalizedIntensity = (intensity - (u_windowLevel.y - u_windowLevel.x * 0.5)) / u_windowLevel.x;
            normalizedIntensity = clamp(normalizedIntensity, 0.0, 1.0);
            return texture(u_transferFunction, vec2(normalizedIntensity, 0.5));
        }
        
        void main() {
            // Calculate 3D position from 2D texture coordinates
            vec3 worldPos = vec3(v_texCoord.x - 0.5, v_texCoord.y - 0.5, 0.0);
            
            // Transform to volume space
            vec4 volumePos = u_volumeMatrix * vec4(worldPos + u_slicePosition, 1.0);
            vec3 texCoord = volumePos.xyz * 0.5 + 0.5;
            
            if (any(lessThan(texCoord, vec3(0.0))) || any(greaterThan(texCoord, vec3(1.0)))) {
                fragColor = vec4(0.0, 0.0, 0.0, 1.0);
                return;
            }
            
            float intensity = texture(u_volumeTexture, texCoord).r;
            vec4 color = applyTransferFunction(intensity);
            
            fragColor = vec4(color.rgb, 1.0);
        }`;
    }

    /**
     * Initialize vertex buffers
     */
    initBuffers() {
        // Create cube vertices for volume rendering
        const cubeVertices = new Float32Array([
            // Front face
            -1, -1,  1,  0, 0,
             1, -1,  1,  1, 0,
             1,  1,  1,  1, 1,
            -1,  1,  1,  0, 1,
            
            // Back face
            -1, -1, -1,  1, 0,
            -1,  1, -1,  1, 1,
             1,  1, -1,  0, 1,
             1, -1, -1,  0, 0,
            
            // Top face
            -1,  1, -1,  0, 1,
            -1,  1,  1,  0, 0,
             1,  1,  1,  1, 0,
             1,  1, -1,  1, 1,
            
            // Bottom face
            -1, -1, -1,  1, 1,
             1, -1, -1,  0, 1,
             1, -1,  1,  0, 0,
            -1, -1,  1,  1, 0,
            
            // Right face
             1, -1, -1,  1, 0,
             1,  1, -1,  1, 1,
             1,  1,  1,  0, 1,
             1, -1,  1,  0, 0,
            
            // Left face
            -1, -1, -1,  0, 0,
            -1, -1,  1,  1, 0,
            -1,  1,  1,  1, 1,
            -1,  1, -1,  0, 1
        ]);

        const cubeIndices = new Uint16Array([
            0,  1,  2,    0,  2,  3,    // front
            4,  5,  6,    4,  6,  7,    // back
            8,  9,  10,   8,  10, 11,   // top
            12, 13, 14,   12, 14, 15,   // bottom
            16, 17, 18,   16, 18, 19,   // right
            20, 21, 22,   20, 22, 23    // left
        ]);

        // Create and bind vertex buffer
        this.vertexBuffer = this.gl.createBuffer();
        this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.vertexBuffer);
        this.gl.bufferData(this.gl.ARRAY_BUFFER, cubeVertices, this.gl.STATIC_DRAW);

        // Create and bind index buffer
        this.indexBuffer = this.gl.createBuffer();
        this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, this.indexBuffer);
        this.gl.bufferData(this.gl.ELEMENT_ARRAY_BUFFER, cubeIndices, this.gl.STATIC_DRAW);

        this.indexCount = cubeIndices.length;
    }

    /**
     * Load volume data into 3D texture
     */
    loadVolumeData(volumeData) {
        this.volumeData = volumeData;
        
        const { buffer, dimensions, dataType } = volumeData;
        
        // Create 3D texture
        if (this.textures.volume) {
            this.gl.deleteTexture(this.textures.volume);
        }
        
        this.textures.volume = this.gl.createTexture();
        this.gl.bindTexture(this.gl.TEXTURE_3D, this.textures.volume);
        
        // Set texture parameters
        this.gl.texParameteri(this.gl.TEXTURE_3D, this.gl.TEXTURE_WRAP_S, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_3D, this.gl.TEXTURE_WRAP_T, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_3D, this.gl.TEXTURE_WRAP_R, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_3D, this.gl.TEXTURE_MIN_FILTER, this.gl.LINEAR);
        this.gl.texParameteri(this.gl.TEXTURE_3D, this.gl.TEXTURE_MAG_FILTER, this.gl.LINEAR);
        
        // Upload texture data
        let format, internalFormat, type;
        
        switch (dataType) {
            case 'int16':
                // Normalize to [0,1] range for texture
                const normalizedBuffer = new Float32Array(buffer.length);
                const min = Math.min(...buffer);
                const max = Math.max(...buffer);
                const range = max - min;
                
                for (let i = 0; i < buffer.length; i++) {
                    normalizedBuffer[i] = (buffer[i] - min) / range;
                }
                
                format = this.gl.RED;
                internalFormat = this.gl.R32F;
                type = this.gl.FLOAT;
                
                this.gl.texImage3D(
                    this.gl.TEXTURE_3D, 0, internalFormat,
                    dimensions.x, dimensions.y, dimensions.z,
                    0, format, type, normalizedBuffer
                );
                break;
                
            case 'float32':
                format = this.gl.RED;
                internalFormat = this.gl.R32F;
                type = this.gl.FLOAT;
                
                this.gl.texImage3D(
                    this.gl.TEXTURE_3D, 0, internalFormat,
                    dimensions.x, dimensions.y, dimensions.z,
                    0, format, type, buffer
                );
                break;
                
            case 'uint8':
                format = this.gl.RED;
                internalFormat = this.gl.R8;
                type = this.gl.UNSIGNED_BYTE;
                
                this.gl.texImage3D(
                    this.gl.TEXTURE_3D, 0, internalFormat,
                    dimensions.x, dimensions.y, dimensions.z,
                    0, format, type, buffer
                );
                break;
        }
        
        // Load transfer function
        this.loadTransferFunction(volumeData.transferFunction);
        
        console.log(`Volume texture loaded: ${dimensions.x}x${dimensions.y}x${dimensions.z}`);
    }

    /**
     * Load transfer function into 2D texture
     */
    loadTransferFunction(transferFunction) {
        this.transferFunction = transferFunction;
        
        // Create 1D texture (implemented as 2D with height=1)
        const width = 256;
        const height = 1;
        const transferData = new Uint8Array(width * height * 4); // RGBA
        
        // Generate transfer function data
        for (let i = 0; i < width; i++) {
            const t = i / (width - 1);
            
            // Interpolate color
            const color = this.interpolateTransferFunction(t, transferFunction.color);
            const opacity = this.interpolateTransferFunction(t, transferFunction.opacity);
            
            const index = i * 4;
            transferData[index] = Math.floor(color[0] * 255);     // R
            transferData[index + 1] = Math.floor(color[1] * 255); // G
            transferData[index + 2] = Math.floor(color[2] * 255); // B
            transferData[index + 3] = Math.floor(opacity * 255);  // A
        }
        
        // Create texture
        if (this.textures.transferFunction) {
            this.gl.deleteTexture(this.textures.transferFunction);
        }
        
        this.textures.transferFunction = this.gl.createTexture();
        this.gl.bindTexture(this.gl.TEXTURE_2D, this.textures.transferFunction);
        
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_WRAP_S, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_WRAP_T, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_MIN_FILTER, this.gl.LINEAR);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_MAG_FILTER, this.gl.LINEAR);
        
        this.gl.texImage2D(
            this.gl.TEXTURE_2D, 0, this.gl.RGBA,
            width, height, 0,
            this.gl.RGBA, this.gl.UNSIGNED_BYTE, transferData
        );
    }

    /**
     * Interpolate transfer function values
     */
    interpolateTransferFunction(t, controlPoints) {
        if (controlPoints.length === 0) return [0, 0, 0];
        if (controlPoints.length === 1) return controlPoints[0].color || [controlPoints[0].opacity, controlPoints[0].opacity, controlPoints[0].opacity];
        
        // Find surrounding control points
        let i = 0;
        while (i < controlPoints.length - 1 && controlPoints[i + 1].value < t) {
            i++;
        }
        
        if (i === controlPoints.length - 1) {
            return controlPoints[i].color || [controlPoints[i].opacity, controlPoints[i].opacity, controlPoints[i].opacity];
        }
        
        const p1 = controlPoints[i];
        const p2 = controlPoints[i + 1];
        const alpha = (t - p1.value) / (p2.value - p1.value);
        
        if (p1.color && p2.color) {
            return [
                p1.color[0] + alpha * (p2.color[0] - p1.color[0]),
                p1.color[1] + alpha * (p2.color[1] - p1.color[1]),
                p1.color[2] + alpha * (p2.color[2] - p1.color[2])
            ];
        } else {
            const opacity = p1.opacity + alpha * (p2.opacity - p1.opacity);
            return opacity;
        }
    }

    /**
     * Render the volume
     */
    render() {
        if (!this.volumeData || !this.textures.volume) {
            return;
        }
        
        const gl = this.gl;
        
        // Set viewport
        gl.viewport(0, 0, this.canvas.width, this.canvas.height);
        
        // Clear
        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        
        // Enable blending for volume rendering
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        
        // Select shader program based on rendering mode
        let program;
        switch (this.renderingMode) {
            case 'mip':
                program = this.programs.mip;
                break;
            case 'surface':
                program = this.programs.surface;
                break;
            case 'mpr':
                program = this.programs.mpr;
                break;
            default:
                program = this.programs.volume;
        }
        
        gl.useProgram(program);
        
        // Set up vertex attributes
        this.setupVertexAttributes(program);
        
        // Set uniforms
        this.setUniforms(program);
        
        // Draw
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.indexBuffer);
        gl.drawElements(gl.TRIANGLES, this.indexCount, gl.UNSIGNED_SHORT, 0);
        
        gl.disable(gl.BLEND);
    }

    /**
     * Set up vertex attributes
     */
    setupVertexAttributes(program) {
        const gl = this.gl;
        
        gl.bindBuffer(gl.ARRAY_BUFFER, this.vertexBuffer);
        
        const positionLocation = gl.getAttribLocation(program, 'a_position');
        if (positionLocation !== -1) {
            gl.enableVertexAttribArray(positionLocation);
            gl.vertexAttribPointer(positionLocation, 3, gl.FLOAT, false, 5 * 4, 0);
        }
        
        const texCoordLocation = gl.getAttribLocation(program, 'a_texCoord');
        if (texCoordLocation !== -1) {
            gl.enableVertexAttribArray(texCoordLocation);
            gl.vertexAttribPointer(texCoordLocation, 2, gl.FLOAT, false, 5 * 4, 3 * 4);
        }
    }

    /**
     * Set shader uniforms
     */
    setUniforms(program) {
        const gl = this.gl;
        
        // Matrices
        const modelViewMatrix = this.calculateModelViewMatrix();
        const projectionMatrix = this.calculateProjectionMatrix();
        
        const modelViewLocation = gl.getUniformLocation(program, 'u_modelViewMatrix');
        if (modelViewLocation) {
            gl.uniformMatrix4fv(modelViewLocation, false, modelViewMatrix);
        }
        
        const projectionLocation = gl.getUniformLocation(program, 'u_projectionMatrix');
        if (projectionLocation) {
            gl.uniformMatrix4fv(projectionLocation, false, projectionMatrix);
        }
        
        // Volume texture
        const volumeTextureLocation = gl.getUniformLocation(program, 'u_volumeTexture');
        if (volumeTextureLocation) {
            gl.activeTexture(gl.TEXTURE0);
            gl.bindTexture(gl.TEXTURE_3D, this.textures.volume);
            gl.uniform1i(volumeTextureLocation, 0);
        }
        
        // Transfer function texture
        const transferFunctionLocation = gl.getUniformLocation(program, 'u_transferFunction');
        if (transferFunctionLocation) {
            gl.activeTexture(gl.TEXTURE1);
            gl.bindTexture(gl.TEXTURE_2D, this.textures.transferFunction);
            gl.uniform1i(transferFunctionLocation, 1);
        }
        
        // Volume parameters
        const dimensionsLocation = gl.getUniformLocation(program, 'u_volumeDimensions');
        if (dimensionsLocation) {
            gl.uniform3f(dimensionsLocation, 
                this.volumeData.dimensions.x,
                this.volumeData.dimensions.y,
                this.volumeData.dimensions.z
            );
        }
        
        const spacingLocation = gl.getUniformLocation(program, 'u_volumeSpacing');
        if (spacingLocation) {
            gl.uniform3f(spacingLocation,
                this.volumeData.spacing.x,
                this.volumeData.spacing.y,
                this.volumeData.spacing.z
            );
        }
        
        // Rendering parameters
        const stepSize = this.calculateStepSize();
        const stepSizeLocation = gl.getUniformLocation(program, 'u_stepSize');
        if (stepSizeLocation) {
            gl.uniform1f(stepSizeLocation, stepSize);
        }
        
        const maxStepsLocation = gl.getUniformLocation(program, 'u_maxSteps');
        if (maxStepsLocation) {
            gl.uniform1i(maxStepsLocation, Math.floor(2.0 / stepSize));
        }
        
        // Window/Level
        const windowLevel = this.volumeData.windowLevel.default;
        const windowLevelLocation = gl.getUniformLocation(program, 'u_windowLevel');
        if (windowLevelLocation) {
            gl.uniform2f(windowLevelLocation, windowLevel.window, windowLevel.level);
        }
        
        // Lighting
        const lightDirectionLocation = gl.getUniformLocation(program, 'u_lightDirection');
        if (lightDirectionLocation) {
            gl.uniform3f(lightDirectionLocation, 0.5, 0.5, -1.0);
        }
        
        const lightColorLocation = gl.getUniformLocation(program, 'u_lightColor');
        if (lightColorLocation) {
            gl.uniform3f(lightColorLocation, 1.0, 1.0, 1.0);
        }
        
        const ambientLocation = gl.getUniformLocation(program, 'u_ambient');
        if (ambientLocation) {
            gl.uniform1f(ambientLocation, 0.3);
        }
    }

    /**
     * Calculate step size based on quality level and SA optimizations
     */
    calculateStepSize() {
        let baseStepSize;
        
        switch (this.qualityLevel) {
            case 'low':
                baseStepSize = 0.01;
                break;
            case 'medium':
                baseStepSize = 0.005;
                break;
            case 'high':
                baseStepSize = 0.002;
                break;
            default:
                baseStepSize = 0.005;
        }
        
        // Adjust for South African optimizations
        if (this.saOptimizations.lowBandwidth) {
            baseStepSize *= 2; // Larger steps for faster rendering
        }
        
        if (this.saOptimizations.powerSave) {
            baseStepSize *= 1.5; // Reduce quality to save battery
        }
        
        if (this.saOptimizations.mobileDevice) {
            baseStepSize *= 1.2; // Slightly larger steps for mobile
        }
        
        return baseStepSize;
    }

    /**
     * Calculate model-view matrix
     */
    calculateModelViewMatrix() {
        // This would use a proper matrix library in production
        // For now, return identity matrix
        return new Float32Array([
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        ]);
    }

    /**
     * Calculate projection matrix
     */
    calculateProjectionMatrix() {
        const aspect = this.canvas.width / this.canvas.height;
        const fov = this.camera.fov * Math.PI / 180;
        const near = this.camera.near;
        const far = this.camera.far;
        
        const f = 1.0 / Math.tan(fov / 2);
        
        return new Float32Array([
            f / aspect, 0, 0, 0,
            0, f, 0, 0,
            0, 0, (far + near) / (near - far), (2 * far * near) / (near - far),
            0, 0, -1, 0
        ]);
    }

    /**
     * Detect South African optimizations
     */
    detectSAOptimizations() {
        // Network condition
        if (navigator.connection) {
            const effectiveType = navigator.connection.effectiveType;
            this.saOptimizations.lowBandwidth = effectiveType === '2g' || effectiveType === 'slow-2g';
        }
        
        // Mobile device
        this.saOptimizations.mobileDevice = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        
        // Power save mode
        if (navigator.getBattery) {
            navigator.getBattery().then(battery => {
                this.saOptimizations.powerSave = battery.level < 0.2 && !battery.charging;
            });
        }
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Handle canvas resize
        const resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
                const { width, height } = entry.contentRect;
                this.canvas.width = width;
                this.canvas.height = height;
                this.render();
            }
        });
        
        resizeObserver.observe(this.canvas);
    }

    /**
     * Set rendering mode
     */
    setRenderingMode(mode) {
        this.renderingMode = mode;
        this.render();
    }

    /**
     * Set quality level
     */
    setQualityLevel(level) {
        this.qualityLevel = level;
        this.render();
    }

    /**
     * Update camera
     */
    updateCamera(camera) {
        Object.assign(this.camera, camera);
        this.render();
    }

    /**
     * Cleanup resources
     */
    dispose() {
        const gl = this.gl;
        
        // Delete textures
        Object.values(this.textures).forEach(texture => {
            if (texture) gl.deleteTexture(texture);
        });
        
        // Delete buffers
        if (this.vertexBuffer) gl.deleteBuffer(this.vertexBuffer);
        if (this.indexBuffer) gl.deleteBuffer(this.indexBuffer);
        
        // Delete programs
        Object.values(this.programs).forEach(program => {
            if (program) gl.deleteProgram(program);
        });
        
        this.volumeCache?.clear();
    }
}

export default VolumeRenderer;