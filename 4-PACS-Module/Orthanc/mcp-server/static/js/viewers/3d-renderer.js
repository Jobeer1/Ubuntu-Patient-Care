/**
 * 3D Volumetric Renderer using Three.js
 * Handles WebGL rendering, volume loading, and user interactions
 */

class VolumetricRenderer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.volumeMesh = null;
        this.volumeData = null;
        this.animationId = null;
        this.autoRotate = false;
        this.fps = 0;
        this.lastFrameTime = Date.now();
        
        this.init();
    }

    init() {
        // Initialize Three.js scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x000000);

        // Setup camera
        const aspect = this.canvas.clientWidth / this.canvas.clientHeight;
        this.camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 1000);
        this.camera.position.z = 300;

        // Setup renderer
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true
        });
        this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);

        // Add lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(1, 1, 1);
        this.scene.add(directionalLight);

        // Setup controls
        this.setupControls();

        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());

        // Start render loop
        this.animate();

        console.log('3D Renderer initialized');
    }

    setupControls() {
        // Mouse controls for rotation, pan, zoom
        let isDragging = false;
        let previousMousePosition = { x: 0, y: 0 };
        let isRightClick = false;

        this.canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            isRightClick = e.button === 2;
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        this.canvas.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const deltaX = e.clientX - previousMousePosition.x;
            const deltaY = e.clientY - previousMousePosition.y;

            if (isRightClick) {
                // Pan
                this.camera.position.x -= deltaX * 0.5;
                this.camera.position.y += deltaY * 0.5;
            } else {
                // Rotate
                if (this.volumeMesh) {
                    this.volumeMesh.rotation.y += deltaX * 0.01;
                    this.volumeMesh.rotation.x += deltaY * 0.01;
                }
            }

            previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        this.canvas.addEventListener('mouseup', () => {
            isDragging = false;
        });

        this.canvas.addEventListener('mouseleave', () => {
            isDragging = false;
        });

        // Prevent context menu on right click
        this.canvas.addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });

        // Zoom with mouse wheel
        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY * 0.1;
            this.camera.position.z += delta;
            this.camera.position.z = Math.max(50, Math.min(500, this.camera.position.z));
        });

        // Double click to reset view
        this.canvas.addEventListener('dblclick', () => {
            this.resetView();
        });
    }

    loadVolume(volumeData) {
        console.log('Loading volume data:', volumeData);
        this.volumeData = volumeData;

        // Remove existing mesh
        if (this.volumeMesh) {
            this.scene.remove(this.volumeMesh);
            this.volumeMesh.geometry.dispose();
            this.volumeMesh.material.dispose();
        }

        // Create volume mesh based on render mode
        const renderMode = document.getElementById('renderMode')?.value || 'volume';
        
        switch(renderMode) {
            case 'volume':
                this.createVolumeRendering(volumeData);
                break;
            case 'mip':
                this.createMIPRendering(volumeData);
                break;
            case 'surface':
                this.createSurfaceRendering(volumeData);
                break;
        }

        this.resetView();
    }

    createVolumeRendering(volumeData) {
        // Create a simple box geometry as placeholder
        // In production, this would use volume texture and ray marching shader
        const geometry = new THREE.BoxGeometry(
            volumeData.dimensions[0] * 0.5,
            volumeData.dimensions[1] * 0.5,
            volumeData.dimensions[2] * 0.5
        );

        const material = new THREE.MeshPhongMaterial({
            color: 0x44aa88,
            transparent: true,
            opacity: 0.8,
            side: THREE.DoubleSide
        });

        this.volumeMesh = new THREE.Mesh(geometry, material);
        this.scene.add(this.volumeMesh);

        // Add wireframe for better visualization
        const wireframe = new THREE.WireframeGeometry(geometry);
        const line = new THREE.LineSegments(wireframe);
        line.material.color.setHex(0xffffff);
        line.material.opacity = 0.3;
        line.material.transparent = true;
        this.volumeMesh.add(line);
    }

    createMIPRendering(volumeData) {
        // Maximum Intensity Projection
        // Simplified version - would use custom shader in production
        const geometry = new THREE.BoxGeometry(
            volumeData.dimensions[0] * 0.5,
            volumeData.dimensions[1] * 0.5,
            volumeData.dimensions[2] * 0.5
        );

        const material = new THREE.MeshBasicMaterial({
            color: 0xffffff,
            transparent: true,
            opacity: 0.9,
            side: THREE.DoubleSide
        });

        this.volumeMesh = new THREE.Mesh(geometry, material);
        this.scene.add(this.volumeMesh);
    }

    createSurfaceRendering(volumeData) {
        // Surface rendering using marching cubes
        // Simplified version
        const geometry = new THREE.BoxGeometry(
            volumeData.dimensions[0] * 0.5,
            volumeData.dimensions[1] * 0.5,
            volumeData.dimensions[2] * 0.5
        );

        const material = new THREE.MeshPhongMaterial({
            color: 0xcccccc,
            shininess: 100,
            side: THREE.DoubleSide
        });

        this.volumeMesh = new THREE.Mesh(geometry, material);
        this.scene.add(this.volumeMesh);
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());

        // Auto-rotate if enabled
        if (this.autoRotate && this.volumeMesh) {
            this.volumeMesh.rotation.y += 0.005;
        }

        // Calculate FPS
        const now = Date.now();
        const delta = now - this.lastFrameTime;
        this.fps = Math.round(1000 / delta);
        this.lastFrameTime = now;

        // Update FPS display
        const fpsElement = document.getElementById('fps');
        if (fpsElement) {
            fpsElement.textContent = this.fps;
        }

        // Update memory display
        if (performance.memory) {
            const memoryMB = Math.round(performance.memory.usedJSHeapSize / 1048576);
            const memoryElement = document.getElementById('memory');
            if (memoryElement) {
                memoryElement.textContent = memoryMB + ' MB';
            }
        }

        this.renderer.render(this.scene, this.camera);
    }

    resetView() {
        this.camera.position.set(0, 0, 300);
        this.camera.lookAt(0, 0, 0);
        
        if (this.volumeMesh) {
            this.volumeMesh.rotation.set(0, 0, 0);
            this.volumeMesh.position.set(0, 0, 0);
        }
    }

    setAutoRotate(enabled) {
        this.autoRotate = enabled;
    }

    updateOpacity(value) {
        if (this.volumeMesh && this.volumeMesh.material) {
            this.volumeMesh.material.opacity = value / 100;
        }
    }

    updateWindowLevel(level) {
        // Adjust material properties based on window level
        if (this.volumeMesh && this.volumeMesh.material) {
            // This would adjust the transfer function in production
            console.log('Window level:', level);
        }
    }

    updateWindowWidth(width) {
        // Adjust material properties based on window width
        if (this.volumeMesh && this.volumeMesh.material) {
            // This would adjust the transfer function in production
            console.log('Window width:', width);
        }
    }

    applyPreset(presetName) {
        const presets = {
            bone: { level: 400, width: 1800, color: 0xeeeeee },
            lung: { level: -600, width: 1500, color: 0x88ccff },
            soft: { level: 40, width: 400, color: 0xffccaa },
            brain: { level: 40, width: 80, color: 0xccaaff },
            liver: { level: 60, width: 150, color: 0xffaa88 }
        };

        const preset = presets[presetName];
        if (preset && this.volumeMesh) {
            // Update window/level
            document.getElementById('windowLevel').value = preset.level;
            document.getElementById('windowLevelValue').textContent = preset.level;
            document.getElementById('windowWidth').value = preset.width;
            document.getElementById('windowWidthValue').textContent = preset.width;

            // Update material color
            if (this.volumeMesh.material) {
                this.volumeMesh.material.color.setHex(preset.color);
            }

            this.updateWindowLevel(preset.level);
            this.updateWindowWidth(preset.width);
        }
    }

    updateClipping(axis, value) {
        // Implement clipping planes
        if (!this.volumeMesh) return;

        const clipValue = value / 100;
        console.log(`Clipping ${axis}: ${clipValue}`);
        
        // This would use THREE.ClippingPlane in production
    }

    takeScreenshot() {
        try {
            const dataURL = this.renderer.domElement.toDataURL('image/png');
            const link = document.createElement('a');
            link.download = `screenshot_${Date.now()}.png`;
            link.href = dataURL;
            link.click();
            
            updateStatus('Screenshot saved');
        } catch (error) {
            console.error('Screenshot failed:', error);
            updateStatus('Screenshot failed');
        }
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            this.canvas.parentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }

    exportVolume(format) {
        if (!this.volumeMesh) {
            alert('No volume loaded');
            return;
        }

        updateStatus(`Exporting as ${format.toUpperCase()}...`);

        // In production, this would export the actual volume data
        setTimeout(() => {
            alert(`Export as ${format.toUpperCase()} not yet implemented`);
            updateStatus('Ready');
        }, 500);
    }

    onWindowResize() {
        const width = this.canvas.clientWidth;
        const height = this.canvas.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();

        this.renderer.setSize(width, height);
    }

    dispose() {
        // Clean up resources
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }

        if (this.volumeMesh) {
            this.scene.remove(this.volumeMesh);
            this.volumeMesh.geometry.dispose();
            this.volumeMesh.material.dispose();
        }

        this.renderer.dispose();
    }
}

// Global renderer instance
let renderer = null;

// Initialize renderer when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    renderer = new VolumetricRenderer('viewerCanvas');
    console.log('Volumetric renderer ready');
});

// Override placeholder functions from HTML
function initializeRenderer(data) {
    if (renderer && data.volume) {
        renderer.loadVolume(data.volume);
    }
}

function updateWindowLevel() {
    const level = parseInt(document.getElementById('windowLevel').value);
    if (renderer) {
        renderer.updateWindowLevel(level);
    }
}

function updateWindowWidth() {
    const width = parseInt(document.getElementById('windowWidth').value);
    if (renderer) {
        renderer.updateWindowWidth(width);
    }
}

function updateOpacity() {
    const opacity = parseInt(document.getElementById('opacity').value);
    if (renderer) {
        renderer.updateOpacity(opacity);
    }
}

function updateClipping() {
    const clipX = parseInt(document.getElementById('clipX').value);
    const clipY = parseInt(document.getElementById('clipY').value);
    const clipZ = parseInt(document.getElementById('clipZ').value);
    
    if (renderer) {
        renderer.updateClipping('x', clipX);
        renderer.updateClipping('y', clipY);
        renderer.updateClipping('z', clipZ);
    }
}

function applyPreset(preset) {
    if (renderer) {
        renderer.applyPreset(preset);
        updateStatus(`Applied ${preset} preset`);
    }
}

function resetView() {
    if (renderer) {
        renderer.resetView();
        updateStatus('View reset');
    }
}

function takeScreenshot() {
    if (renderer) {
        renderer.takeScreenshot();
    }
}

function toggleFullscreen() {
    if (renderer) {
        renderer.toggleFullscreen();
    }
}

function toggleAutoRotate() {
    const enabled = document.getElementById('autoRotate').checked;
    if (renderer) {
        renderer.setAutoRotate(enabled);
        updateStatus(enabled ? 'Auto-rotate enabled' : 'Auto-rotate disabled');
    }
}

function exportVolume(format) {
    if (renderer) {
        renderer.exportVolume(format);
    }
}

function resetClipping() {
    document.getElementById('clipX').value = 0;
    document.getElementById('clipY').value = 0;
    document.getElementById('clipZ').value = 0;
    document.getElementById('clipXValue').textContent = '0%';
    document.getElementById('clipYValue').textContent = '0%';
    document.getElementById('clipZValue').textContent = '0%';
    updateClipping();
    updateStatus('Clipping reset');
}

// Measurement tools (placeholder implementations)
let activeTool = null;
let measurements = [];

function activateTool(tool) {
    activeTool = tool;
    
    // Remove active class from all buttons
    document.querySelectorAll('.btn-tool').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Add active class to selected tool
    const toolBtn = document.querySelector(`[data-tool="${tool}"]`);
    if (toolBtn) {
        toolBtn.classList.add('active');
    }
    
    updateStatus(`${tool.charAt(0).toUpperCase() + tool.slice(1)} tool activated`);
}

function clearAllMeasurements() {
    measurements = [];
    const list = document.getElementById('measurementsList');
    list.innerHTML = '<p class="empty-state">No measurements yet</p>';
    updateStatus('All measurements cleared');
}

function generateReport() {
    updateStatus('Generating report...');
    
    // In production, this would generate a comprehensive report
    setTimeout(() => {
        alert('Report generation not yet implemented');
        updateStatus('Ready');
    }, 500);
}
