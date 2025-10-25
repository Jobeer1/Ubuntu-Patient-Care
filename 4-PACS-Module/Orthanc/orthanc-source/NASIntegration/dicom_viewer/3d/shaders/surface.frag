#version 300 es
precision highp float;

// Inputs from vertex shader
in vec3 v_position;
in vec3 v_normal;
in vec3 v_viewDirection;
in vec2 v_texCoord;
in float v_depth;

// Uniforms
uniform vec3 u_lightDirection;
uniform vec3 u_lightColor;
uniform vec3 u_surfaceColor;
uniform float u_ambient;
uniform float u_diffuse;
uniform float u_specular;
uniform float u_shininess;
uniform float u_opacity;

// Material properties
uniform bool u_useTexture;
uniform sampler2D u_surfaceTexture;
uniform float u_roughness;
uniform float u_metallic;

// Advanced lighting
uniform bool u_enableShadows;
uniform sampler2D u_shadowMap;
uniform mat4 u_lightSpaceMatrix;

// Edge enhancement for medical visualization
uniform bool u_enableEdgeEnhancement;
uniform float u_edgeThreshold;
uniform vec3 u_edgeColor;

// South African medical standards
uniform bool u_medicalVisualization;
uniform float u_diagnosticContrast;

// Output
out vec4 fragColor;

// Calculate shadow factor
float calculateShadow(vec4 lightSpacePos) {
    if (!u_enableShadows) return 1.0;
    
    // Perspective divide
    vec3 projCoords = lightSpacePos.xyz / lightSpacePos.w;
    projCoords = projCoords * 0.5 + 0.5;
    
    // Check if position is outside shadow map
    if (projCoords.z > 1.0 || any(lessThan(projCoords.xy, vec2(0.0))) || any(greaterThan(projCoords.xy, vec2(1.0)))) {
        return 1.0;
    }
    
    float closestDepth = texture(u_shadowMap, projCoords.xy).r;
    float currentDepth = projCoords.z;
    
    // Bias to prevent shadow acne
    float bias = 0.005;
    return currentDepth - bias > closestDepth ? 0.3 : 1.0;
}

// Enhanced Phong lighting model
vec3 calculatePhongLighting(vec3 normal, vec3 viewDir, vec3 lightDir, vec3 baseColor, float shadowFactor) {
    // Ambient component
    vec3 ambient = u_ambient * baseColor;
    
    // Diffuse component
    float diffuseFactor = max(0.0, dot(normal, -lightDir));
    vec3 diffuse = u_diffuse * diffuseFactor * baseColor * u_lightColor * shadowFactor;
    
    // Specular component
    vec3 reflectDir = reflect(lightDir, normal);
    float specularFactor = pow(max(0.0, dot(viewDir, reflectDir)), u_shininess);
    vec3 specular = u_specular * specularFactor * u_lightColor * shadowFactor;
    
    return ambient + diffuse + specular;
}

// Physically Based Rendering (simplified)
vec3 calculatePBRLighting(vec3 normal, vec3 viewDir, vec3 lightDir, vec3 albedo, float shadowFactor) {
    // Simplified PBR for medical visualization
    float NdotL = max(0.0, dot(normal, -lightDir));
    float NdotV = max(0.0, dot(normal, viewDir));
    
    // Fresnel approximation
    float fresnel = pow(1.0 - NdotV, 5.0);
    fresnel = mix(0.04, 1.0, fresnel);
    
    // Diffuse term
    vec3 diffuse = albedo * NdotL * (1.0 - u_metallic);
    
    // Specular term
    float roughness2 = u_roughness * u_roughness;
    float denom = NdotL * sqrt(NdotV * NdotV * (1.0 - roughness2) + roughness2) + 
                  NdotV * sqrt(NdotL * NdotL * (1.0 - roughness2) + roughness2);
    float specular = (denom > 0.0) ? 1.0 / denom : 0.0;
    
    vec3 specularColor = mix(vec3(0.04), albedo, u_metallic);
    vec3 specularTerm = specularColor * specular * fresnel;
    
    return (diffuse + specularTerm) * u_lightColor * shadowFactor + u_ambient * albedo;
}

// Edge detection for medical visualization
float detectEdge(vec3 normal, vec3 viewDir) {
    if (!u_enableEdgeEnhancement) return 0.0;
    
    float edge = 1.0 - abs(dot(normal, viewDir));
    return smoothstep(u_edgeThreshold - 0.1, u_edgeThreshold + 0.1, edge);
}

// Medical visualization enhancements
vec3 applyMedicalEnhancements(vec3 color, vec3 normal, vec3 viewDir) {
    if (!u_medicalVisualization) return color;
    
    // Enhance contrast for diagnostic purposes
    color = pow(color, vec3(1.0 / u_diagnosticContrast));
    
    // Subtle edge enhancement for structure definition
    float edgeFactor = detectEdge(normal, viewDir);
    color = mix(color, u_edgeColor, edgeFactor * 0.3);
    
    // Ensure minimum brightness for visibility
    float luminance = dot(color, vec3(0.299, 0.587, 0.114));
    if (luminance < 0.1) {
        color += vec3(0.05); // Slight brightness boost
    }
    
    return color;
}

void main() {
    vec3 normal = normalize(v_normal);
    vec3 viewDir = normalize(v_viewDirection);
    vec3 lightDir = normalize(u_lightDirection);
    
    // Base color
    vec3 baseColor = u_surfaceColor;
    if (u_useTexture) {
        vec4 texColor = texture(u_surfaceTexture, v_texCoord);
        baseColor *= texColor.rgb;
    }
    
    // Calculate shadow factor
    vec4 lightSpacePos = u_lightSpaceMatrix * vec4(v_position, 1.0);
    float shadowFactor = calculateShadow(lightSpacePos);
    
    // Calculate lighting
    vec3 finalColor;
    if (u_metallic > 0.1 || u_roughness < 0.9) {
        // Use PBR for metallic/smooth surfaces
        finalColor = calculatePBRLighting(normal, viewDir, lightDir, baseColor, shadowFactor);
    } else {
        // Use Phong for standard surfaces
        finalColor = calculatePhongLighting(normal, viewDir, lightDir, baseColor, shadowFactor);
    }
    
    // Apply medical visualization enhancements
    finalColor = applyMedicalEnhancements(finalColor, normal, viewDir);
    
    // Edge enhancement
    float edgeFactor = detectEdge(normal, viewDir);
    if (edgeFactor > 0.0) {
        finalColor = mix(finalColor, u_edgeColor, edgeFactor * 0.5);
    }
    
    // Depth-based fog for depth perception
    float fogFactor = smoothstep(0.7, 1.0, v_depth);
    finalColor = mix(finalColor, vec3(0.2, 0.2, 0.3), fogFactor * 0.3);
    
    // Gamma correction
    finalColor = pow(finalColor, vec3(1.0 / 2.2));
    
    // Clamp to valid range
    finalColor = clamp(finalColor, 0.0, 1.0);
    
    fragColor = vec4(finalColor, u_opacity);
}