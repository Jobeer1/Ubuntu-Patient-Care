# Quick Reference Guide - Dev 1 Session 2 Modules

## API Integration Module Usage

### Basic Setup

```javascript
// Initialize the API client
const api = initializeViewerAPI({ 
    baseURL: '/api/viewer',
    timeout: 30000 
});

// Or get the global instance
const api = getViewerAPI();
```

### Loading a Study

```javascript
try {
    const studyData = await api.loadStudy('study_123', {
        seriesId: 'series_456',
        windowCenter: 40,
        windowWidth: 400,
        useCache: true
    });
    
    console.log('Volume shape:', studyData.volume_shape);
    console.log('Num slices:', studyData.num_slices);
} catch (error) {
    console.error('Failed to load study:', error);
}
```

### Getting Slices

```javascript
// Single slice
const slice = await api.getSlice('study_123', 50, {
    normalize: true,
    useCache: true
});

// Multiple slices
const slices = await api.getSlicesBatch('study_123', 
    [0, 25, 50, 75, 100],
    { normalize: true }
);
```

### Getting MPR Slices

```javascript
// Axial slice at 50% of volume height
const axialSlice = await api.getMPRSlice('study_123', 'axial', 0.5);

// Sagittal slice at 30% position
const sagittalSlice = await api.getMPRSlice('study_123', 'sagittal', 0.3);

// Coronal slice at 70% position
const coronalSlice = await api.getMPRSlice('study_123', 'coronal', 0.7);
```

### Metadata and Status

```javascript
// Get study metadata
const metadata = await api.getMetadata('study_123');

// Get cache status
const cacheStatus = await api.getCacheStatus();

// Check API health
const health = await api.getHealthStatus();

// Get thumbnail URL
const thumbnailUrl = api.getThumbnailURL('study_123');

// Get thumbnail as blob
const blob = await api.getThumbnail('study_123');
```

### Cache Management

```javascript
// Clear specific study
await api.clearStudyCache('study_123');

// Clear all studies
await api.clearStudyCache();

// Clear local cache
api.clearLocalCache();

// Get cache size
const sizeMB = api.getCacheSize();

// Limit cache size
api.limitCacheSize(100); // 100 MB max
```

---

## Measurement Tools Module Usage

### Basic Setup

```javascript
// Initialize measurement tools
const measurements = initializeMeasurementTools(
    renderer,      // VolumetricRenderer instance
    canvas,        // Canvas element
    (measurement) => {
        // Called when measurement is created
        console.log('New measurement:', measurement);
    }
);

// Or get the global instance
const measurements = getMeasurementTools();
```

### Creating Measurements

```javascript
// Activate distance tool - user clicks 2 points
measurements.activateTool('distance');

// User clicks first point
// User clicks second point
// Distance measurement is automatically created

// Deactivate when done
measurements.deactivateTool();
```

### Measurement Types

```javascript
// Each tool is activated by name:
measurements.activateTool('distance');      // 2-point distance
measurements.activateTool('angle');         // 3-point angle
measurements.activateTool('area');          // Multi-point polygon
measurements.activateTool('volume');        // Volume region
measurements.activateTool('hu');            // Hounsfield Unit at point
```

### Getting Measurements

```javascript
// Get all measurements
const allMeasurements = measurements.getMeasurements();

// Get specific measurement
const measurement = measurements.getMeasurement(0);

// Format for display
const formatted = measurements.formatMeasurement(measurement);
console.log(formatted.display);  // "Distance: 25.50 mm"

// Delete measurement
measurements.deleteMeasurement(0);

// Clear all
measurements.clearMeasurements();
```

### Exporting Measurements

```javascript
// Export as JSON
const jsonStr = measurements.exportAsJSON();
downloadFile(jsonStr, 'measurements.json', 'application/json');

// Export as CSV
const csvStr = measurements.exportAsCSV();
downloadFile(csvStr, 'measurements.csv', 'text/csv');

// Export as HTML table
const htmlStr = measurements.exportAsHTML();
downloadFile(htmlStr, 'measurements.html', 'text/html');
```

### Accessing Measurement Data

```javascript
const measurement = measurements.getMeasurement(0);

// All measurements have:
measurement.id           // Unique ID
measurement.type        // 'distance', 'angle', 'area', 'volume', 'hu'
measurement.value       // Numeric value
measurement.unit        // Unit string ('mm', '°', 'mm²', 'cm³', 'HU')
measurement.timestamp   // Creation time
measurement.accuracy    // Accuracy specification
measurement.points      // Array of 3D points used

// Specific to measurement type:
measurement.tissue      // For HU measurements
measurement.voxelCount  // For volume measurements
measurement.voxelSpacing // For volume measurements
```

---

## Keyboard Shortcuts

### Measurement Tools
- **ESC**: Cancel current measurement / Deactivate tool
- **Backspace**: Undo last point

### Viewer Controls
- **R**: Reset view to default
- **F**: Toggle fullscreen
- **A**: Toggle auto-rotate
- **I**: Show/hide info panel
- **V**: Cycle render modes (volume → MIP → surface)
- **S**: Take screenshot

### Mouse Controls
- **Left drag**: Rotate 3D volume
- **Right drag**: Pan view
- **Scroll**: Zoom in/out

---

## Integration Example

```html
<!DOCTYPE html>
<html>
<head>
    <script src="/static/js/viewers/api-integration.js"></script>
    <script src="/static/js/viewers/3d-renderer.js"></script>
    <script src="/static/js/viewers/measurement-tools.js"></script>
</head>
<body>
    <canvas id="viewerCanvas"></canvas>

    <script>
        async function initializeViewer() {
            // 1. Initialize API
            const api = initializeViewerAPI();
            
            // 2. Initialize 3D renderer
            const renderer = new VolumetricRenderer('viewerCanvas');
            
            // 3. Initialize measurements
            const measurements = initializeMeasurementTools(
                renderer,
                document.getElementById('viewerCanvas'),
                (measurement) => {
                    const fmt = measurements.formatMeasurement(measurement);
                    console.log('Measurement created:', fmt.display);
                }
            );
            
            // 4. Load a study
            const study = await api.loadStudy('study_123');
            console.log('Study loaded:', study);
            
            // 5. User can now:
            // - Use measurement tools
            // - Rotate, pan, zoom
            // - Export measurements
        }
        
        initializeViewer();
    </script>
</body>
</html>
```

---

## Error Handling

### API Client Errors

```javascript
try {
    const study = await api.loadStudy('study_123');
} catch (error) {
    if (error.message.includes('HTTP 404')) {
        console.log('Study not found');
    } else if (error.message.includes('HTTP 500')) {
        console.log('Server error - will retry');
    } else if (error.message.includes('timeout')) {
        console.log('Request timeout');
    } else {
        console.log('Unknown error:', error);
    }
}
```

### Measurement Tool Errors

```javascript
measurements.activateTool('distance');

// If renderer not ready:
if (!measurements.renderer) {
    console.log('Renderer not initialized');
}

// Raycasting returns null if no hit:
const points = measurements.points;  // May be empty
if (points.length === 0) {
    console.log('No valid points selected');
}
```

---

## Performance Tips

1. **Caching**: Always enable caching for repeated access
   ```javascript
   const study = await api.loadStudy('study_123', { useCache: true });
   ```

2. **Batch Loading**: Load multiple slices at once
   ```javascript
   const slices = await api.getSlicesBatch('study_123', 
       [0, 10, 20, 30, 40]
   );
   ```

3. **Cache Limits**: Monitor and limit cache size
   ```javascript
   if (api.getCacheSize() > 100) {  // 100 MB
       api.limitCacheSize(100);
   }
   ```

4. **Measurement Export**: Export in batch, not individual
   ```javascript
   const json = measurements.exportAsJSON();  // All at once
   ```

---

## Debugging

### Enable Logging

All modules log to `console`:
```javascript
// API client logs
[APIClient] Loading study: study_123
[APIClient] Study loaded successfully: {...}
[APIClient] Error loading study: Network timeout

// Measurement tools logs
[Measurements] Activating tool: distance
[Measurements] Click at (256, 512)
[Measurements] Distance: 25.50 mm

// Viewer controller logs
[Viewer] Initializing application...
[Viewer] 3D renderer initialized
[Viewer] Application ready
```

### Debug Cache

```javascript
// View all cached data
console.log(viewerAPI.cache);

// Clear specific cache entry
viewerAPI.cache.delete('study_study_123');

// Get cache statistics
const cacheStatus = await api.getCacheStatus();
console.log('Cached studies:', cacheStatus.count);
console.log('Total size:', cacheStatus.size_mb, 'MB');
```

### Performance Profiling

```javascript
// Measure API call timing
console.time('load-study');
const study = await api.loadStudy('study_123');
console.timeEnd('load-study');

// Monitor memory usage
console.log('Cache size:', api.getCacheSize(), 'MB');

// Get info panel stats (in viewer)
// Shows FPS, Memory, Volume size, Voxel count
```

---

## Common Issues

### Issue: CORS Error
**Solution**: Ensure backend has CORS enabled:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

### Issue: Study Won't Load
**Solution**: Check console for API errors:
```javascript
try {
    await api.loadStudy('study_id');
} catch (error) {
    console.error(error);  // See exact error
}
```

### Issue: Measurements Not Recording
**Solution**: Ensure renderer and canvas are initialized:
```javascript
if (!measurements.renderer || !measurements.renderer.camera) {
    console.log('Renderer not ready for measurements');
}
```

### Issue: Slow Performance
**Solution**: Check cache and disable if needed:
```javascript
const study = await api.loadStudy('study_123', { 
    useCache: false 
});
```

---

## Next Steps

1. **TASK 1.2.4**: Integration Testing (with Dev 2)
   - Load test studies via UI
   - Verify all measurements work
   - Test keyboard shortcuts
   - Cross-browser testing

2. **Phase 2**: Segmentation Module
   - Will use these APIs to display segmentation masks
   - Measurement tools will work with segmented regions

3. **Phase 3+**: Additional Analysis Tools
   - Report generation using exported measurements
   - Statistical analysis of measurements
   - 3D printing file export (STL/OBJ)
