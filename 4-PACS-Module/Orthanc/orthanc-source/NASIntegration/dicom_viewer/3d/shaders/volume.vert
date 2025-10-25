#version 300 es
precision highp float;

// Vertex attributes
in vec3 a_position;
in vec2 a_texCoord;

// Uniforms
uniform mat4 u_modelViewMatrix;
uniform mat4 u_projectionMatrix;
uniform mat4 u_normalMatrix;
uniform vec3 u_cameraPosition;

// Outputs to fragment shader
out vec3 v_rayDirection;
out vec3 v_rayOrigin;
out vec2 v_texCoord;
out vec3 v_worldPosition;
out vec3 v_viewDirection;

void main() {
    // Transform vertex position
    vec4 worldPosition = u_modelViewMatrix * vec4(a_position, 1.0);
    gl_Position = u_projectionMatrix * worldPosition;
    
    // Calculate ray direction for volume rendering
    v_rayDirection = normalize(a_position - u_cameraPosition);
    v_rayOrigin = a_position;
    
    // Pass through texture coordinates
    v_texCoord = a_texCoord;
    
    // World position for lighting calculations
    v_worldPosition = worldPosition.xyz;
    
    // View direction for specular lighting
    v_viewDirection = normalize(u_cameraPosition - worldPosition.xyz);
}