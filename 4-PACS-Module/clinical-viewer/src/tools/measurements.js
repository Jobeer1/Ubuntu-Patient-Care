/**
 * Measurement Tools
 * Distance, angle, ROI, Hounsfield units
 */

export class MeasurementTools {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.measurements = [];
    this.activeTool = null;
    this.currentMeasurement = null;
  }

  /**
   * Activate measurement tool
   */
  activate(toolType) {
    this.activeTool = toolType;
    this.currentMeasurement = null;
  }

  /**
   * Deactivate tool
   */
  deactivate() {
    this.activeTool = null;
    this.currentMeasurement = null;
  }

  /**
   * Handle mouse down
   */
  handleMouseDown(x, y, pixelSpacing = [1, 1]) {
    if (!this.activeTool) return;
    
    switch (this.activeTool) {
      case 'length':
        this.startLength(x, y, pixelSpacing);
        break;
      case 'angle':
        this.startAngle(x, y, pixelSpacing);
        break;
      case 'roi':
        this.startROI(x, y, pixelSpacing);
        break;
    }
  }

  /**
   * Handle mouse move
   */
  handleMouseMove(x, y) {
    if (!this.currentMeasurement) return;
    
    this.currentMeasurement.points[this.currentMeasurement.points.length - 1] = { x, y };
    this.render();
  }

  /**
   * Handle mouse up
   */
  handleMouseUp(x, y, pixelData = null) {
    if (!this.currentMeasurement) return;
    
    this.currentMeasurement.points[this.currentMeasurement.points.length - 1] = { x, y };
    
    // Calculate measurement
    this.calculateMeasurement(this.currentMeasurement, pixelData);
    
    // Save measurement
    this.measurements.push(this.currentMeasurement);
    this.currentMeasurement = null;
    
    this.render();
  }

  /**
   * Start length measurement
   */
  startLength(x, y, pixelSpacing) {
    this.currentMeasurement = {
      type: 'length',
      points: [{ x, y }, { x, y }],
      pixelSpacing,
      value: 0,
      unit: 'mm'
    };
  }

  /**
   * Start angle measurement
   */
  startAngle(x, y, pixelSpacing) {
    if (!this.currentMeasurement) {
      this.currentMeasurement = {
        type: 'angle',
        points: [{ x, y }, { x, y }],
        pixelSpacing,
        value: 0,
        unit: '°'
      };
    } else if (this.currentMeasurement.points.length === 2) {
      this.currentMeasurement.points.push({ x, y });
    }
  }

  /**
   * Start ROI measurement
   */
  startROI(x, y, pixelSpacing) {
    this.currentMeasurement = {
      type: 'roi',
      points: [{ x, y }, { x, y }],
      pixelSpacing,
      value: { mean: 0, std: 0, min: 0, max: 0 },
      unit: 'HU'
    };
  }

  /**
   * Calculate measurement value
   */
  calculateMeasurement(measurement, pixelData) {
    switch (measurement.type) {
      case 'length':
        measurement.value = this.calculateLength(measurement);
        break;
      case 'angle':
        measurement.value = this.calculateAngle(measurement);
        break;
      case 'roi':
        measurement.value = this.calculateROI(measurement, pixelData);
        break;
    }
  }

  /**
   * Calculate length in mm
   */
  calculateLength(measurement) {
    const [p1, p2] = measurement.points;
    const [sx, sy] = measurement.pixelSpacing;
    
    const dx = (p2.x - p1.x) * sx;
    const dy = (p2.y - p1.y) * sy;
    
    return Math.sqrt(dx * dx + dy * dy);
  }

  /**
   * Calculate angle in degrees
   */
  calculateAngle(measurement) {
    if (measurement.points.length < 3) return 0;
    
    const [p1, p2, p3] = measurement.points;
    
    // Vector 1: p1 -> p2
    const v1x = p2.x - p1.x;
    const v1y = p2.y - p1.y;
    
    // Vector 2: p2 -> p3
    const v2x = p3.x - p2.x;
    const v2y = p3.y - p2.y;
    
    // Calculate angle
    const dot = v1x * v2x + v1y * v2y;
    const mag1 = Math.sqrt(v1x * v1x + v1y * v1y);
    const mag2 = Math.sqrt(v2x * v2x + v2y * v2y);
    
    const angle = Math.acos(dot / (mag1 * mag2));
    return (angle * 180) / Math.PI;
  }

  /**
   * Calculate ROI statistics
   */
  calculateROI(measurement, pixelData) {
    if (!pixelData) {
      return { mean: 0, std: 0, min: 0, max: 0 };
    }
    
    const [p1, p2] = measurement.points;
    const x1 = Math.min(p1.x, p2.x);
    const y1 = Math.min(p1.y, p2.y);
    const x2 = Math.max(p1.x, p2.x);
    const y2 = Math.max(p1.y, p2.y);
    
    const width = this.canvas.width;
    const values = [];
    
    for (let y = y1; y <= y2; y++) {
      for (let x = x1; x <= x2; x++) {
        const idx = y * width + x;
        if (idx < pixelData.length) {
          values.push(pixelData[idx]);
        }
      }
    }
    
    if (values.length === 0) {
      return { mean: 0, std: 0, min: 0, max: 0 };
    }
    
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length;
    const std = Math.sqrt(variance);
    const min = Math.min(...values);
    const max = Math.max(...values);
    
    return { mean, std, min, max };
  }

  /**
   * Render all measurements
   */
  render() {
    // Clear previous drawings
    this.ctx.save();
    
    // Render saved measurements
    this.measurements.forEach(m => this.renderMeasurement(m));
    
    // Render current measurement
    if (this.currentMeasurement) {
      this.renderMeasurement(this.currentMeasurement, true);
    }
    
    this.ctx.restore();
  }

  /**
   * Render single measurement
   */
  renderMeasurement(measurement, isActive = false) {
    this.ctx.strokeStyle = isActive ? '#ffc107' : '#00a8e8';
    this.ctx.fillStyle = isActive ? '#ffc107' : '#00a8e8';
    this.ctx.lineWidth = 2;
    this.ctx.font = '14px monospace';
    
    switch (measurement.type) {
      case 'length':
        this.renderLength(measurement);
        break;
      case 'angle':
        this.renderAngle(measurement);
        break;
      case 'roi':
        this.renderROI(measurement);
        break;
    }
  }

  /**
   * Render length measurement
   */
  renderLength(measurement) {
    const [p1, p2] = measurement.points;
    
    // Draw line
    this.ctx.beginPath();
    this.ctx.moveTo(p1.x, p1.y);
    this.ctx.lineTo(p2.x, p2.y);
    this.ctx.stroke();
    
    // Draw endpoints
    this.ctx.fillRect(p1.x - 3, p1.y - 3, 6, 6);
    this.ctx.fillRect(p2.x - 3, p2.y - 3, 6, 6);
    
    // Draw label
    const midX = (p1.x + p2.x) / 2;
    const midY = (p1.y + p2.y) / 2;
    const label = `${measurement.value.toFixed(1)} ${measurement.unit}`;
    
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    this.ctx.fillRect(midX - 30, midY - 20, 60, 20);
    this.ctx.fillStyle = '#00a8e8';
    this.ctx.fillText(label, midX - 25, midY - 5);
  }

  /**
   * Render angle measurement
   */
  renderAngle(measurement) {
    if (measurement.points.length < 2) return;
    
    const [p1, p2, p3] = measurement.points;
    
    // Draw lines
    this.ctx.beginPath();
    this.ctx.moveTo(p1.x, p1.y);
    this.ctx.lineTo(p2.x, p2.y);
    if (p3) {
      this.ctx.lineTo(p3.x, p3.y);
    }
    this.ctx.stroke();
    
    // Draw points
    this.ctx.fillRect(p1.x - 3, p1.y - 3, 6, 6);
    this.ctx.fillRect(p2.x - 3, p2.y - 3, 6, 6);
    if (p3) {
      this.ctx.fillRect(p3.x - 3, p3.y - 3, 6, 6);
      
      // Draw label
      const label = `${measurement.value.toFixed(1)}${measurement.unit}`;
      this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      this.ctx.fillRect(p2.x - 30, p2.y - 30, 60, 20);
      this.ctx.fillStyle = '#00a8e8';
      this.ctx.fillText(label, p2.x - 25, p2.y - 15);
    }
  }

  /**
   * Render ROI measurement
   */
  renderROI(measurement) {
    const [p1, p2] = measurement.points;
    const x = Math.min(p1.x, p2.x);
    const y = Math.min(p1.y, p2.y);
    const w = Math.abs(p2.x - p1.x);
    const h = Math.abs(p2.y - p1.y);
    
    // Draw rectangle
    this.ctx.strokeRect(x, y, w, h);
    
    // Draw label
    const label = `Mean: ${measurement.value.mean.toFixed(1)} ${measurement.unit}`;
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    this.ctx.fillRect(x, y - 25, 150, 20);
    this.ctx.fillStyle = '#00a8e8';
    this.ctx.fillText(label, x + 5, y - 10);
  }

  /**
   * Clear all measurements
   */
  clear() {
    this.measurements = [];
    this.currentMeasurement = null;
  }

  /**
   * Delete last measurement
   */
  deleteLast() {
    this.measurements.pop();
    this.render();
  }

  /**
   * Export measurements
   */
  export() {
    return this.measurements.map(m => ({
      type: m.type,
      value: m.value,
      unit: m.unit,
      points: m.points
    }));
  }
}
