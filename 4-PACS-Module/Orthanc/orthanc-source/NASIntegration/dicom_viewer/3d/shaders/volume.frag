#version 300 es
precision highp float;

// Inputs from vertex shader
in vec3 v_rayDirection;
in vec3 v_rayOrigin;
in vec2 v_texCoord;
in vec3 v_worldPosition;
in vec3 v_viewDirection;

// Uniforms
uniform sampler3D u_volumeTexture;
uniform sampler2D u_transferFunction;
uniform sampler2D u_noiseTexture;

// Volume properties
uniform vec3 u_volumeDimensions;
uniform vec3 u_volumeSpacing;
uniform vec3 u_volumeOrigin;
uniform mat4 u_volumeMatrix;

// Rendering parameters
uniform float u_stepSize;
uniform int u_maxSteps;
uniform float u_alphaThreshold;
uniform vec2 u_windowLevel; // x = window, y = level
uniform float u_densityScale;
uniform float u_gradientThreshold;

// Lighting parameters
uniform vec3 u_lightDirection;
uniform vec3 u_lightColor;
uniform float u_ambient;
uniform float u_diffuse;
uniform float u_specular;
uniform float u_shininess;

// Clipping planes
uniform bool u_clippingEnabled;
uniform vec4 u_clippingPlanes[6];
uniform int u_numClippingPlanes;

// Quality settings
uniform int u_qualityLevel; // 0=low, 1=medium, 2=high
uniform bool u_jitteringEnabled;
uniform bool u_gradientShadingEnabled;

// South African optimization flags
uniform bool u_lowBandwidthMode;
uniform bool u_powerSaveMode;

// Output
out vec4 fragColor;

// Noise function for jittering
float random(vec2 st) {
    return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
}

// Calculate gradient using central differences
vec3 calculateGradient(vec3 pos) {
    float stepSize = 1.0 / max(u_volumeDimensions.x, max(u_volumeDimensions.y, u_volumeDimensions.z));
    
    // Adjust step size based on quality level
    if (u_qualityLevel == 0) {
        stepSize *= 2.0; // Lower quality, larger steps
    } else if (u_qualityLevel == 2) {
        stepSize *= 0.5; // Higher quality, smaller steps
    }
    
    float dx = texture(u_volumeTexture, pos + vec3(stepSize, 0, 0)).r - 
               texture(u_volumeTexture, pos - vec3(stepSize, 0, 0)).r;
    float dy = texture(u_volumeTexture, pos + vec3(0, stepSize, 0)).r - 
               texture(u_volumeTexture, pos - vec3(0, stepSize, 0)).r;
    float dz = texture(u_volumeTexture, pos + vec3(0, 0, stepSize)).r - 
               texture(u_volumeTexture, pos - vec3(0, 0, stepSize)).r;
    
    vec3 gradient = vec3(dx, dy, dz) / (2.0 * stepSize);
    
    // Normalize gradient if above threshold
    float gradientMagnitude = length(gradient);
    if (gradientMagnitude > u_gradientThreshold) {
        return gradient / gradientMagnitude;
    }
    
    return vec3(0.0);
}

// Apply window/level transformation
float applyWindowLevel(float intensity) {
    float minValue = u_windowLevel.y - u_windowLevel.x * 0.5;
    float maxValue = u_windowLevel.y + u_windowLevel.x * 0.5;
    return clamp((intensity - minValue) / (maxValue - minValue), 0.0, 1.0);
}

// Sample transfer function
vec4 sampleTransferFunction(float intensity) {
    float normalizedIntensity = applyWindowLevel(intensity);
    return texture(u_transferFunction, vec2(normalizedIntensity, 0.5));
}

// Check clipping planes
bool isClipped(vec3 worldPos) {
    if (!u_clippingEnabled) return false;
    
    for (int i = 0; i < u_numClippingPlanes && i < 6; i++) {
        vec4 plane = u_clippingPlanes[i];
        float distance = dot(worldPos, plane.xyz) + plane.w;
        if (distance < 0.0) return true;
    }
    
    return false;
}

// Calculate lighting
vec3 calculateLighting(vec3 normal, vec3 viewDir, vec3 lightDir, vec3 baseColor) {
    if (!u_gradientShadingEnabled || length(normal) < 0.1) {
        return baseColor;
    }
    
    // Ambient component
    vec3 ambient = u_ambient * baseColor;
    
    // Diffuse component
    float diffuseFactor = max(0.0, dot(normal, -lightDir));
    vec3 diffuse = u_diffuse * diffuseFactor * baseColor * u_lightColor;
    
    // Specular component
    vec3 reflectDir = reflect(lightDir, normal);
    float specularFactor = pow(max(0.0, dot(viewDir, reflectDir)), u_shininess);
    vec3 specular = u_specular * specularFactor * u_lightColor;
    
    return ambient + diffuse + specular;
}

// Adaptive step size based on gradient
float getAdaptiveStepSize(vec3 gradient) {
    float baseStepSize = u_stepSize;
    
    // Reduce step size in areas with high gradient (edges)
    float gradientMagnitude = length(gradient);
    if (gradientMagnitude > u_gradientThreshold) {
        baseStepSize *= 0.5;
    }
    
    // Adjust for quality level
    if (u_qualityLevel == 0) {
        baseStepSize *= 2.0; // Low quality - larger steps
    } else if (u_qualityLevel == 2) {
        baseStepSize *= 0.5; // High quality - smaller steps
    }
    
    // South African optimizations
    if (u_lowBandwidthMode || u_powerSaveMode) {
        baseStepSize *= 1.5; // Larger steps for performance
    }
    
    return baseStepSize;
}

void main() {
    vec3 rayDir = normalize(v_rayDirection);
    vec3 rayPos = v_rayOrigin * 0.5 + 0.5; // Transform to [0,1] range
    
    // Apply jittering to reduce artifacts
    if (u_jitteringEnabled && u_qualityLevel > 0) {
        float jitter = random(gl_FragCoord.xy) * u_stepSize;
        rayPos += rayDir * jitter;
    }
    
    vec4 color = vec4(0.0);
    float alpha = 0.0;
    
    // Adaptive step count based on quality
    int maxSteps = u_maxSteps;
    if (u_qualityLevel == 0) {
        maxSteps = maxSteps / 2; // Low quality - fewer steps
    } else if (u_qualityLevel == 2) {
        maxSteps = int(float(maxSteps) * 1.5); // High quality - more steps
    }
    
    // Ray marching loop
    for (int i = 0; i < maxSteps; i++) {
        // Early termination if alpha is high enough
        if (alpha >= u_alphaThreshold) break;
        
        // Check bounds
        if (any(lessThan(rayPos, vec3(0.0))) || any(greaterThan(rayPos, vec3(1.0)))) {
            break;
        }
        
        // Transform to world coordinates for clipping
        vec4 worldPos = u_volumeMatrix * vec4(rayPos * 2.0 - 1.0, 1.0);
        if (isClipped(worldPos.xyz)) {
            rayPos += rayDir * u_stepSize;
            continue;
        }
        
        // Sample volume
        float intensity = texture(u_volumeTexture, rayPos).r;
        
        // Apply density scaling
        intensity *= u_densityScale;
        
        // Sample transfer function
        vec4 sample = sampleTransferFunction(intensity);
        
        if (sample.a > 0.01) {
            vec3 sampleColor = sample.rgb;
            
            // Calculate gradient for lighting
            if (u_gradientShadingEnabled) {
                vec3 gradient = calculateGradient(rayPos);
                sampleColor = calculateLighting(gradient, v_viewDirection, u_lightDirection, sampleColor);
            }
            
            // Get adaptive step size
            float currentStepSize = u_gradientShadingEnabled ? 
                getAdaptiveStepSize(calculateGradient(rayPos)) : u_stepSize;
            
            // Opacity correction for step size
            float correctedAlpha = 1.0 - pow(1.0 - sample.a, currentStepSize / u_stepSize);
            
            // Front-to-back alpha blending
            color.rgb += sampleColor * correctedAlpha * (1.0 - alpha);
            alpha += correctedAlpha * (1.0 - alpha);
            
            // Use adaptive step size
            rayPos += rayDir * currentStepSize;
        } else {
            rayPos += rayDir * u_stepSize;
        }
    }
    
    // Apply final color corrections
    color.rgb = clamp(color.rgb, 0.0, 1.0);
    
    // South African medical imaging standards
    // Ensure minimum contrast for diagnostic quality
    if (alpha > 0.1) {
        float contrast = 1.2; // Slight contrast boost for medical viewing
        color.rgb = ((color.rgb - 0.5) * contrast) + 0.5;
        color.rgb = clamp(color.rgb, 0.0, 1.0);
    }
    
    fragColor = vec4(color.rgb, alpha);
}