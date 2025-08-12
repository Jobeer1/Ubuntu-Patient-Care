#version 300 es
precision highp float;

// Vertex attributes
in vec3 a_position;
in vec3 a_normal;
in vec2 a_texCoord;

// Uniforms
uniform mat4 u_modelViewMatrix;
uniform mat4 u_projectionMatrix;
uniform mat3 u_normalMatrix;
uniform vec3 u_cameraPosition;

// Outputs to fragment shader
out vec3 v_position;
out vec3 v_normal;
out vec3 v_viewDirection;
out vec2 v_texCoord;
out float v_depth;

void main() {
    // Transform vertex position
    vec4 worldPosition = u_modelViewMatrix * vec4(a_position, 1.0);
    gl_Position = u_projectionMatrix * worldPosition;
    
    // Transform normal
    v_normal = normalize(u_normalMatrix * a_normal);
    
    // World position for lighting calculations
    v_position = worldPosition.xyz;
    
    // View direction for specular lighting
    v_viewDirection = normalize(u_cameraPosition - worldPosition.xyz);
    
    // Pass through texture coordinates
    v_texCoord = a_texCoord;
    
    // Depth for depth-based effects
    v_depth = gl_Position.z / gl_Position.w;
}