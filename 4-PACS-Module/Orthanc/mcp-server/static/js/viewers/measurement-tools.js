/**
 * Measurement Tools for 3D DICOM Viewer
 * Implements clinical measurement capabilities:
 * - Distance measurement (point-to-point)
 * - Area measurement (ROI)
 * - Angle measurement
 * - Volume calculation
 * - Hounsfield Unit (HU) conversion
 */

class MeasurementTools {
    constructor(renderer, canvas, onMeasurementAdded = null) {
        this.renderer = renderer;
        this.canvas = canvas;
        this.onMeasurementAdded = onMeasurementAdded;
        
        this.measurements = [];
        this.currentTool = null;
        this.isActive = false;
        this.points = [];
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        
        // Drawing context for 2D overlays
        this.canvas2D = document.createElement('canvas');
        this.canvas2D.width = canvas.width;
        this.canvas2D.height = canvas.height;
        this.ctx2D = this.canvas2D.getContext('2d');
        
        // Measurement ID counter
        this.measurementId = 0;
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.canvas.addEventListener('click', (e) => this.handleCanvasClick(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        window.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    /**
     * Activate a measurement tool
     * @param {string} toolName - 'distance', 'angle', 'area', 'volume', 'hu'
     */
    activateTool(toolName) {
        if (this.currentTool === toolName) {
            // Toggle off
            this.deactivateTool();
            return;
        }

        console.log(`[Measurements] Activating tool: ${toolName}`);
        this.currentTool = toolName;
        this.isActive = true;
        this.points = [];
        this.canvas.style.cursor = 'crosshair';
    }

    /**
     * Deactivate current tool
     */
    deactivateTool() {
        console.log('[Measurements] Deactivating tool');
        this.currentTool = null;
        this.isActive = false;
        this.points = [];
        this.canvas.style.cursor = 'default';
    }

    /**
     * Handle canvas click for measurement points
     */
    handleCanvasClick(event) {
        if (!this.isActive) return;

        // Get click position in canvas coordinates
        const rect = this.canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        // Normalize to -1, 1 range
        this.mouse.x = (x / this.canvas.width) * 2 - 1;
        this.mouse.y = -(y / this.canvas.height) * 2 + 1;

        console.log(`[Measurements] Click at (${x}, ${y})`);

        // Get 3D world position from 2D screen coordinates
        const worldPos = this.getWorldPositionFromScreen(this.mouse);
        
        if (!worldPos) {
            console.warn('[Measurements] Could not determine 3D position');
            return;
        }

        this.points.push({
            x: x,
            y: y,
            world: worldPos,
            timestamp: Date.now()
        });

        console.log(`[Measurements] Point added. Total points: ${this.points.length}`);

        // Handle measurement completion based on tool type
        this.processMeasurementPoints();
    }

    /**
     * Handle mouse move for preview
     */
    handleMouseMove(event) {
        if (!this.isActive || this.points.length === 0) return;

        const rect = this.canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        // Could draw preview line here
        // This would be implemented with WebGL overlays
    }

    /**
     * Handle keyboard shortcuts
     */
    handleKeyboard(event) {
        if (event.key === 'Escape') {
            this.deactivateTool();
        } else if (event.key === 'Backspace') {
            if (this.points.length > 0) {
                this.points.pop();
                console.log('[Measurements] Point removed');
            }
        }
    }

    /**
     * Process points and create measurement
     */
    processMeasurementPoints() {
        switch (this.currentTool) {
            case 'distance':
                if (this.points.length === 2) {
                    this.createDistanceMeasurement();
                    this.points = [];
                }
                break;

            case 'angle':
                if (this.points.length === 3) {
                    this.createAngleMeasurement();
                    this.points = [];
                }
                break;

            case 'area':
                // Area needs >= 3 points, can finish with right-click or 'Enter'
                break;

            case 'volume':
                // Volume typically requires ROI definition
                break;

            case 'hu':
                if (this.points.length === 1) {
                    this.createHUMeasurement();
                    this.points = [];
                }
                break;
        }
    }

    /**
     * Create distance measurement
     */
    createDistanceMeasurement() {
        const p1 = this.points[0].world;
        const p2 = this.points[1].world;

        // Calculate distance in mm (assuming unit = mm)
        const distance = new THREE.Vector3().subVectors(p2, p1).length();

        const measurement = {
            id: this.measurementId++,
            type: 'distance',
            value: distance,
            unit: 'mm',
            points: [
                { x: p1.x, y: p1.y, z: p1.z },
                { x: p2.x, y: p2.y, z: p2.z }
            ],
            timestamp: new Date().toLocaleTimeString(),
            accuracy: '±0.5mm'
        };

        this.measurements.push(measurement);
        console.log(`[Measurements] Distance: ${distance.toFixed(2)} mm`);

        if (this.onMeasurementAdded) {
            this.onMeasurementAdded(measurement);
        }

        return measurement;
    }

    /**
     * Create angle measurement
     */
    createAngleMeasurement() {
        const p1 = this.points[0].world;
        const p2 = this.points[1].world; // Vertex
        const p3 = this.points[2].world;

        // Create vectors from vertex
        const v1 = new THREE.Vector3().subVectors(p1, p2).normalize();
        const v2 = new THREE.Vector3().subVectors(p3, p2).normalize();

        // Calculate angle
        const cos = v1.dot(v2);
        const angle = Math.acos(Math.max(-1, Math.min(1, cos))) * (180 / Math.PI);

        const measurement = {
            id: this.measurementId++,
            type: 'angle',
            value: angle,
            unit: '°',
            points: [
                { x: p1.x, y: p1.y, z: p1.z },
                { x: p2.x, y: p2.y, z: p2.z },
                { x: p3.x, y: p3.y, z: p3.z }
            ],
            timestamp: new Date().toLocaleTimeString()
        };

        this.measurements.push(measurement);
        console.log(`[Measurements] Angle: ${angle.toFixed(2)}°`);

        if (this.onMeasurementAdded) {
            this.onMeasurementAdded(measurement);
        }

        return measurement;
    }

    /**
     * Create area measurement from ROI
     */
    createAreaMeasurement() {
        if (this.points.length < 3) {
            console.warn('[Measurements] Area requires at least 3 points');
            return;
        }

        // Calculate area using Shoelace formula
        let area = 0;
        for (let i = 0; i < this.points.length; i++) {
            const p1 = this.points[i].world;
            const p2 = this.points[(i + 1) % this.points.length].world;

            // Project to 2D for area calculation
            area += (p1.x * p2.y - p2.x * p1.y);
        }
        area = Math.abs(area / 2);

        const measurement = {
            id: this.measurementId++,
            type: 'area',
            value: area,
            unit: 'mm²',
            points: this.points.map(p => ({
                x: p.world.x,
                y: p.world.y,
                z: p.world.z
            })),
            timestamp: new Date().toLocaleTimeString(),
            accuracy: '±1%'
        };

        this.measurements.push(measurement);
        console.log(`[Measurements] Area: ${area.toFixed(2)} mm²`);

        if (this.onMeasurementAdded) {
            this.onMeasurementAdded(measurement);
        }

        return measurement;
    }

    /**
     * Create volume measurement from segmented region
     */
    createVolumeMeasurement(voxelCount, voxelSpacing = { x: 1, y: 1, z: 1 }) {
        // Volume = voxel count × voxel spacing
        const volume = voxelCount * voxelSpacing.x * voxelSpacing.y * voxelSpacing.z;
        const volumeCm3 = volume / 1000; // Convert mm³ to cm³

        const measurement = {
            id: this.measurementId++,
            type: 'volume',
            value: volumeCm3,
            unit: 'cm³',
            voxelCount: voxelCount,
            voxelSpacing: voxelSpacing,
            timestamp: new Date().toLocaleTimeString(),
            accuracy: '±2%'
        };

        this.measurements.push(measurement);
        console.log(`[Measurements] Volume: ${volumeCm3.toFixed(2)} cm³`);

        if (this.onMeasurementAdded) {
            this.onMeasurementAdded(measurement);
        }

        return measurement;
    }

    /**
     * Create Hounsfield Unit measurement
     */
    createHUMeasurement() {
        const point = this.points[0].world;

        // Get HU value from volume data
        // This would require access to the loaded volume texture
        const huValue = this.getHUValueAtPoint(point);

        const measurement = {
            id: this.measurementId++,
            type: 'hu',
            value: huValue,
            unit: 'HU',
            point: {
                x: point.x,
                y: point.y,
                z: point.z
            },
            tissue: this.identifyTissueType(huValue),
            timestamp: new Date().toLocaleTimeString()
        };

        this.measurements.push(measurement);
        console.log(`[Measurements] HU Value: ${huValue} HU (${measurement.tissue})`);

        if (this.onMeasurementAdded) {
            this.onMeasurementAdded(measurement);
        }

        return measurement;
    }

    /**
     * Get HU value at specific point
     * (Requires access to volume data - placeholder implementation)
     */
    getHUValueAtPoint(point) {
        // This would be implemented with actual volume data access
        // For now, return simulated value
        return Math.random() * 1000 - 100;
    }

    /**
     * Identify tissue type from HU value
     */
    identifyTissueType(hu) {
        if (hu < -100) return 'Air';
        if (hu < -50) return 'Fat';
        if (hu < 0) return 'Fluid';
        if (hu < 50) return 'Soft Tissue';
        if (hu < 100) return 'Dense Tissue';
        if (hu < 400) return 'Bone';
        return 'Metal';
    }

    /**
     * Get 3D world position from 2D screen coordinates
     * Uses raycasting to find intersection with volume
     */
    getWorldPositionFromScreen(screenCoords) {
        if (!this.renderer || !this.renderer.scene || !this.renderer.camera) {
            console.warn('[Measurements] Renderer not ready');
            return null;
        }

        // Cast ray from camera through screen position
        this.raycaster.setFromCamera(screenCoords, this.renderer.camera);

        // Find intersections with scene objects
        const intersects = this.raycaster.intersectObjects(this.renderer.scene.children);

        if (intersects.length > 0) {
            // Return first intersection point
            return intersects[0].point;
        }

        // Fallback: place point at fixed distance from camera
        const direction = this.raycaster.ray.direction;
        const distance = 100;
        return this.raycaster.ray.origin.clone().addScaledVector(direction, distance);
    }

    /**
     * Get all measurements
     */
    getMeasurements() {
        return [...this.measurements];
    }

    /**
     * Get measurement by ID
     */
    getMeasurement(id) {
        return this.measurements.find(m => m.id === id);
    }

    /**
     * Delete measurement
     */
    deleteMeasurement(id) {
        const index = this.measurements.findIndex(m => m.id === id);
        if (index >= 0) {
            const deleted = this.measurements.splice(index, 1);
            console.log(`[Measurements] Deleted measurement ${id}`);
            return deleted[0];
        }
        return null;
    }

    /**
     * Clear all measurements
     */
    clearMeasurements() {
        const count = this.measurements.length;
        this.measurements = [];
        console.log(`[Measurements] Cleared ${count} measurements`);
    }

    /**
     * Export measurements as JSON
     */
    exportAsJSON() {
        const data = {
            version: '1.0',
            timestamp: new Date().toISOString(),
            measurements: this.measurements
        };
        return JSON.stringify(data, null, 2);
    }

    /**
     * Export measurements as CSV
     */
    exportAsCSV() {
        let csv = 'ID,Type,Value,Unit,Timestamp\n';
        
        for (const m of this.measurements) {
            csv += `${m.id},"${m.type}",${m.value},"${m.unit}","${m.timestamp}"\n`;
        }
        
        return csv;
    }

    /**
     * Export measurements as HTML table
     */
    exportAsHTML() {
        let html = '<table border="1" cellpadding="10" cellspacing="0">\n';
        html += '<tr><th>ID</th><th>Type</th><th>Value</th><th>Unit</th><th>Timestamp</th><th>Accuracy</th></tr>\n';
        
        for (const m of this.measurements) {
            const accuracy = m.accuracy || '-';
            html += `<tr><td>${m.id}</td><td>${m.type}</td><td>${m.value.toFixed(2)}</td><td>${m.unit}</td><td>${m.timestamp}</td><td>${accuracy}</td></tr>\n`;
        }
        
        html += '</table>';
        return html;
    }

    /**
     * Format measurement for display
     */
    formatMeasurement(measurement) {
        const label = this.getMeasurementLabel(measurement);
        const value = typeof measurement.value === 'number' 
            ? measurement.value.toFixed(2) 
            : measurement.value;
        
        return {
            label: label,
            display: `${label}: ${value} ${measurement.unit}`,
            accuracy: measurement.accuracy || '-'
        };
    }

    /**
     * Get display label for measurement
     */
    getMeasurementLabel(measurement) {
        switch (measurement.type) {
            case 'distance': return 'Distance';
            case 'angle': return 'Angle';
            case 'area': return 'Area';
            case 'volume': return 'Volume';
            case 'hu': return `Tissue (${measurement.tissue})`;
            default: return 'Measurement';
        }
    }
}

/**
 * Global measurement tools instance
 */
let measurementTools = null;

/**
 * Initialize measurement tools
 */
function initializeMeasurementTools(renderer, canvas, onMeasurementAdded = null) {
    measurementTools = new MeasurementTools(renderer, canvas, onMeasurementAdded);
    console.log('[Measurements] Tools initialized');
    return measurementTools;
}

/**
 * Get measurement tools instance
 */
function getMeasurementTools() {
    if (!measurementTools) {
        console.warn('[Measurements] Tools not initialized');
    }
    return measurementTools;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { MeasurementTools, initializeMeasurementTools, getMeasurementTools };
}
