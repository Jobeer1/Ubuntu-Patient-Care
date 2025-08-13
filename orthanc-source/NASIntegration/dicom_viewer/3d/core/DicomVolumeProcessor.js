/**
 * Advanced DICOM Volume Processor for 3D Reconstruction
 * Handles CT, MRI, and Ultrasound volume processing with South African optimizations
 */

class DicomVolumeProcessor {
    constructor() {
        this.supportedModalities = ['CT', 'MR', 'US', 'PT', 'NM'];
        this.volumeCache = new Map();
        this.processingQueue = [];
        this.isProcessing = false;
        
        // South African network optimization
        this.networkOptimization = {
            chunkSize: this.getOptimalChunkSize(),
            compressionLevel: this.getCompressionLevel(),
            priorityLoading: true
        };
    }

    /**
     * Process DICOM series into 3D volume
     * @param {Array} dicomSeries - Array of DICOM instances
     * @param {Object} options - Processing options
     */
    async processVolume(dicomSeries, options = {}) {
        const {
            modality = 'CT',
            interpolation = 'linear',
            spacing = 'auto',
            orientation = 'axial',
            qualityLevel = 'high',
            progressCallback = null
        } = options;

        try {
            // Validate and sort series
            const sortedSeries = await this.validateAndSortSeries(dicomSeries, modality);
            
            // Create volume metadata
            const volumeMetadata = this.createVolumeMetadata(sortedSeries, modality);
            
            // Process based on modality
            let volumeData;
            switch (modality) {
                case 'CT':
                    volumeData = await this.processCTVolume(sortedSeries, volumeMetadata, options);
                    break;
                case 'MR':
                    volumeData = await this.processMRVolume(sortedSeries, volumeMetadata, options);
                    break;
                case 'US':
                    volumeData = await this.processUSVolume(sortedSeries, volumeMetadata, options);
                    break;
                default:
                    volumeData = await this.processGenericVolume(sortedSeries, volumeMetadata, options);
            }

            // Apply post-processing
            volumeData = await this.applyPostProcessing(volumeData, modality, options);
            
            // Cache the result
            const cacheKey = this.generateCacheKey(dicomSeries, options);
            this.volumeCache.set(cacheKey, volumeData);
            
            return volumeData;
            
        } catch (error) {
            console.error('Volume processing failed:', error);
            throw new Error(`3D volume processing failed: ${error.message}`);
        }
    }

    /**
     * Process CT volume with Hounsfield unit handling
     */
    async processCTVolume(sortedSeries, metadata, options) {
        const { dimensions, spacing, origin } = metadata;
        const volumeSize = dimensions.x * dimensions.y * dimensions.z;
        
        // Create volume buffer (16-bit for HU values)
        const volumeBuffer = new Int16Array(volumeSize);
        
        let processedSlices = 0;
        
        for (let i = 0; i < sortedSeries.length; i++) {
            const slice = sortedSeries[i];
            
            // Extract pixel data and convert to Hounsfield units
            const pixelData = await this.extractPixelData(slice);
            const hounsFieldData = this.convertToHounsfieldUnits(pixelData, slice);
            
            // Place slice in volume
            const sliceOffset = i * dimensions.x * dimensions.y;
            volumeBuffer.set(hounsFieldData, sliceOffset);
            
            processedSlices++;
            if (options.progressCallback) {
                options.progressCallback(processedSlices / sortedSeries.length);
            }
        }

        return {
            type: 'CT',
            buffer: volumeBuffer,
            dimensions,
            spacing,
            origin,
            dataType: 'int16',
            windowLevel: this.calculateOptimalWindowLevel(volumeBuffer, 'CT'),
            transferFunction: this.createCTTransferFunction(),
            metadata: {
                ...metadata,
                hounsFieldRange: this.calculateHounsfieldRange(volumeBuffer)
            }
        };
    }

    /**
     * Process MRI volume with multiple sequences
     */
    async processMRVolume(sortedSeries, metadata, options) {
        const { dimensions, spacing, origin } = metadata;
        const volumeSize = dimensions.x * dimensions.y * dimensions.z;
        
        // Detect MRI sequence type
        const sequenceType = this.detectMRSequence(sortedSeries[0]);
        
        // Create volume buffer (float32 for MR intensity values)
        const volumeBuffer = new Float32Array(volumeSize);
        
        let processedSlices = 0;
        
        for (let i = 0; i < sortedSeries.length; i++) {
            const slice = sortedSeries[i];
            
            // Extract and normalize pixel data
            const pixelData = await this.extractPixelData(slice);
            const normalizedData = this.normalizeMRIntensity(pixelData, slice, sequenceType);
            
            // Handle variable slice thickness
            const adjustedData = this.adjustForSliceThickness(normalizedData, slice, metadata);
            
            const sliceOffset = i * dimensions.x * dimensions.y;
            volumeBuffer.set(adjustedData, sliceOffset);
            
            processedSlices++;
            if (options.progressCallback) {
                options.progressCallback(processedSlices / sortedSeries.length);
            }
        }

        return {
            type: 'MR',
            buffer: volumeBuffer,
            dimensions,
            spacing,
            origin,
            dataType: 'float32',
            sequenceType,
            windowLevel: this.calculateOptimalWindowLevel(volumeBuffer, 'MR'),
            transferFunction: this.createMRTransferFunction(sequenceType),
            metadata: {
                ...metadata,
                intensityRange: this.calculateIntensityRange(volumeBuffer),
                sequenceParameters: this.extractSequenceParameters(sortedSeries[0])
            }
        };
    }

    /**
     * Process Ultrasound volume with fan geometry
     */
    async processUSVolume(sortedSeries, metadata, options) {
        const { dimensions, spacing, origin } = metadata;
        
        // Detect ultrasound geometry (linear, curved, phased array)
        const usGeometry = this.detectUSGeometry(sortedSeries[0]);
        
        // Handle fan-shaped geometry for curved/phased array
        let volumeData;
        if (usGeometry.type === 'curved' || usGeometry.type === 'phased') {
            volumeData = await this.processFanGeometryUS(sortedSeries, metadata, usGeometry);
        } else {
            volumeData = await this.processLinearUS(sortedSeries, metadata);
        }

        return {
            type: 'US',
            buffer: volumeData.buffer,
            dimensions: volumeData.dimensions,
            spacing: volumeData.spacing,
            origin: volumeData.origin,
            dataType: 'uint8',
            geometry: usGeometry,
            windowLevel: this.calculateOptimalWindowLevel(volumeData.buffer, 'US'),
            transferFunction: this.createUSTransferFunction(),
            metadata: {
                ...metadata,
                geometry: usGeometry,
                dopplerInfo: this.extractDopplerInfo(sortedSeries[0])
            }
        };
    }

    /**
     * Validate and sort DICOM series by position
     */
    async validateAndSortSeries(dicomSeries, modality) {
        // Validate series consistency
        const firstInstance = dicomSeries[0];
        const seriesUID = firstInstance.SeriesInstanceUID;
        const studyUID = firstInstance.StudyInstanceUID;
        
        // Filter and validate
        const validInstances = dicomSeries.filter(instance => {
            return instance.SeriesInstanceUID === seriesUID &&
                   instance.StudyInstanceUID === studyUID &&
                   instance.Modality === modality;
        });

        if (validInstances.length === 0) {
            throw new Error('No valid DICOM instances found for 3D reconstruction');
        }

        // Sort by slice position
        return validInstances.sort((a, b) => {
            // Try ImagePositionPatient first
            if (a.ImagePositionPatient && b.ImagePositionPatient) {
                const posA = parseFloat(a.ImagePositionPatient[2]); // Z coordinate
                const posB = parseFloat(b.ImagePositionPatient[2]);
                return posA - posB;
            }
            
            // Fallback to SliceLocation
            if (a.SliceLocation && b.SliceLocation) {
                return parseFloat(a.SliceLocation) - parseFloat(b.SliceLocation);
            }
            
            // Fallback to InstanceNumber
            return parseInt(a.InstanceNumber || 0) - parseInt(b.InstanceNumber || 0);
        });
    }

    /**
     * Create volume metadata from DICOM series
     */
    createVolumeMetadata(sortedSeries, modality) {
        const firstSlice = sortedSeries[0];
        const lastSlice = sortedSeries[sortedSeries.length - 1];
        
        // Get dimensions
        const rows = parseInt(firstSlice.Rows);
        const columns = parseInt(firstSlice.Columns);
        const slices = sortedSeries.length;
        
        // Calculate spacing
        const pixelSpacing = firstSlice.PixelSpacing || [1, 1];
        const sliceThickness = this.calculateSliceSpacing(sortedSeries);
        
        // Get orientation and position
        const imageOrientation = firstSlice.ImageOrientationPatient || [1, 0, 0, 0, 1, 0];
        const imagePosition = firstSlice.ImagePositionPatient || [0, 0, 0];
        
        return {
            dimensions: {
                x: columns,
                y: rows,
                z: slices
            },
            spacing: {
                x: parseFloat(pixelSpacing[0]),
                y: parseFloat(pixelSpacing[1]),
                z: sliceThickness
            },
            origin: {
                x: parseFloat(imagePosition[0]),
                y: parseFloat(imagePosition[1]),
                z: parseFloat(imagePosition[2])
            },
            orientation: imageOrientation.map(v => parseFloat(v)),
            modality,
            seriesUID: firstSlice.SeriesInstanceUID,
            studyUID: firstSlice.StudyInstanceUID
        };
    }

    /**
     * Calculate slice spacing from sorted series
     */
    calculateSliceSpacing(sortedSeries) {
        if (sortedSeries.length < 2) {
            return parseFloat(sortedSeries[0].SliceThickness || 1);
        }

        // Calculate average spacing between slices
        let totalSpacing = 0;
        let validSpacings = 0;

        for (let i = 1; i < sortedSeries.length; i++) {
            const curr = sortedSeries[i];
            const prev = sortedSeries[i - 1];
            
            if (curr.ImagePositionPatient && prev.ImagePositionPatient) {
                const currPos = parseFloat(curr.ImagePositionPatient[2]);
                const prevPos = parseFloat(prev.ImagePositionPatient[2]);
                totalSpacing += Math.abs(currPos - prevPos);
                validSpacings++;
            } else if (curr.SliceLocation && prev.SliceLocation) {
                const currLoc = parseFloat(curr.SliceLocation);
                const prevLoc = parseFloat(prev.SliceLocation);
                totalSpacing += Math.abs(currLoc - prevLoc);
                validSpacings++;
            }
        }

        if (validSpacings > 0) {
            return totalSpacing / validSpacings;
        }

        // Fallback to SliceThickness
        return parseFloat(sortedSeries[0].SliceThickness || 1);
    }

    /**
     * Convert pixel data to Hounsfield units for CT
     */
    convertToHounsfieldUnits(pixelData, dicomSlice) {
        const rescaleSlope = parseFloat(dicomSlice.RescaleSlope || 1);
        const rescaleIntercept = parseFloat(dicomSlice.RescaleIntercept || 0);
        
        const hounsFieldData = new Int16Array(pixelData.length);
        
        for (let i = 0; i < pixelData.length; i++) {
            hounsFieldData[i] = Math.round(pixelData[i] * rescaleSlope + rescaleIntercept);
        }
        
        return hounsFieldData;
    }

    /**
     * Detect MRI sequence type
     */
    detectMRSequence(dicomSlice) {
        const sequenceName = dicomSlice.SequenceName || '';
        const protocolName = dicomSlice.ProtocolName || '';
        const seriesDescription = dicomSlice.SeriesDescription || '';
        
        const combined = (sequenceName + protocolName + seriesDescription).toLowerCase();
        
        if (combined.includes('t1')) return 'T1';
        if (combined.includes('t2')) return 'T2';
        if (combined.includes('flair')) return 'FLAIR';
        if (combined.includes('dwi') || combined.includes('diffusion')) return 'DWI';
        if (combined.includes('adc')) return 'ADC';
        if (combined.includes('swi')) return 'SWI';
        if (combined.includes('tof')) return 'TOF';
        
        return 'UNKNOWN';
    }

    /**
     * Detect ultrasound geometry
     */
    detectUSGeometry(dicomSlice) {
        const sequenceName = dicomSlice.SequenceName || '';
        const seriesDescription = dicomSlice.SeriesDescription || '';
        
        // Analyze ultrasound region calibration data if available
        const regionCalibration = dicomSlice.SequenceOfUltrasoundRegions;
        
        if (regionCalibration && regionCalibration.length > 0) {
            const region = regionCalibration[0];
            const regionSpatialFormat = region.RegionSpatialFormat;
            
            if (regionSpatialFormat === 1) return { type: 'linear', format: regionSpatialFormat };
            if (regionSpatialFormat === 2) return { type: 'curved', format: regionSpatialFormat };
            if (regionSpatialFormat === 3) return { type: 'phased', format: regionSpatialFormat };
        }
        
        // Fallback to description analysis
        const description = (sequenceName + seriesDescription).toLowerCase();
        if (description.includes('linear')) return { type: 'linear' };
        if (description.includes('curved') || description.includes('convex')) return { type: 'curved' };
        if (description.includes('phased') || description.includes('sector')) return { type: 'phased' };
        
        return { type: 'linear' }; // Default assumption
    }

    /**
     * Get optimal chunk size based on network conditions
     */
    getOptimalChunkSize() {
        // South African network optimization
        if (navigator.connection) {
            const effectiveType = navigator.connection.effectiveType;
            switch (effectiveType) {
                case '2g': return 64 * 1024; // 64KB
                case '3g': return 256 * 1024; // 256KB
                case '4g': return 1024 * 1024; // 1MB
                default: return 512 * 1024; // 512KB
            }
        }
        return 512 * 1024; // Default 512KB
    }

    /**
     * Get compression level based on device capabilities
     */
    getCompressionLevel() {
        const isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const isLowMemory = navigator.deviceMemory && navigator.deviceMemory < 4;
        
        if (isMobile || isLowMemory) {
            return 'high'; // More compression for mobile/low memory
        }
        return 'medium';
    }

    /**
     * Extract pixel data from DICOM slice
     */
    async extractPixelData(dicomSlice) {
        // This would integrate with your DICOM parsing library
        // For now, return mock data structure
        const rows = parseInt(dicomSlice.Rows);
        const columns = parseInt(dicomSlice.Columns);
        const bitsAllocated = parseInt(dicomSlice.BitsAllocated || 16);
        
        // Mock pixel data - in real implementation, this would come from DICOM parser
        const pixelCount = rows * columns;
        const pixelData = new Uint16Array(pixelCount);
        
        // Fill with mock data for demonstration
        for (let i = 0; i < pixelCount; i++) {
            pixelData[i] = Math.floor(Math.random() * (2 ** bitsAllocated));
        }
        
        return pixelData;
    }

    /**
     * Calculate optimal window/level for modality
     */
    calculateOptimalWindowLevel(volumeBuffer, modality) {
        const min = Math.min(...volumeBuffer);
        const max = Math.max(...volumeBuffer);
        
        switch (modality) {
            case 'CT':
                return {
                    presets: {
                        'Soft Tissue': { window: 400, level: 40 },
                        'Lung': { window: 1500, level: -600 },
                        'Bone': { window: 1800, level: 400 },
                        'Brain': { window: 80, level: 40 }
                    },
                    default: { window: 400, level: 40 }
                };
            case 'MR':
                return {
                    presets: {
                        'Default': { window: max - min, level: (max + min) / 2 }
                    },
                    default: { window: max - min, level: (max + min) / 2 }
                };
            case 'US':
                return {
                    presets: {
                        'Default': { window: 255, level: 128 }
                    },
                    default: { window: 255, level: 128 }
                };
            default:
                return {
                    presets: {
                        'Default': { window: max - min, level: (max + min) / 2 }
                    },
                    default: { window: max - min, level: (max + min) / 2 }
                };
        }
    }

    /**
     * Create transfer function for CT rendering
     */
    createCTTransferFunction() {
        return {
            opacity: [
                { value: -1000, opacity: 0.0 },  // Air
                { value: -500, opacity: 0.0 },   // Lung
                { value: 0, opacity: 0.1 },      // Water
                { value: 200, opacity: 0.3 },    // Soft tissue
                { value: 1000, opacity: 0.8 },   // Bone
                { value: 3000, opacity: 1.0 }    // Dense bone
            ],
            color: [
                { value: -1000, color: [0, 0, 0] },      // Black for air
                { value: -500, color: [0.2, 0.2, 0.2] }, // Dark gray for lung
                { value: 0, color: [0.4, 0.4, 0.4] },    // Gray for water
                { value: 200, color: [0.8, 0.6, 0.6] },  // Pink for soft tissue
                { value: 1000, color: [1.0, 1.0, 0.9] }, // Bone white
                { value: 3000, color: [1.0, 1.0, 1.0] }  // Pure white
            ]
        };
    }

    /**
     * Create transfer function for MR rendering
     */
    createMRTransferFunction(sequenceType) {
        const baseFunction = {
            opacity: [
                { value: 0.0, opacity: 0.0 },
                { value: 0.2, opacity: 0.1 },
                { value: 0.5, opacity: 0.3 },
                { value: 0.8, opacity: 0.7 },
                { value: 1.0, opacity: 1.0 }
            ]
        };

        switch (sequenceType) {
            case 'T1':
                baseFunction.color = [
                    { value: 0.0, color: [0, 0, 0] },
                    { value: 0.3, color: [0.3, 0.3, 0.3] },
                    { value: 0.7, color: [0.8, 0.8, 0.8] },
                    { value: 1.0, color: [1.0, 1.0, 1.0] }
                ];
                break;
            case 'T2':
                baseFunction.color = [
                    { value: 0.0, color: [0, 0, 0] },
                    { value: 0.3, color: [0.2, 0.2, 0.4] },
                    { value: 0.7, color: [0.6, 0.6, 0.9] },
                    { value: 1.0, color: [0.9, 0.9, 1.0] }
                ];
                break;
            case 'FLAIR':
                baseFunction.color = [
                    { value: 0.0, color: [0, 0, 0] },
                    { value: 0.3, color: [0.4, 0.2, 0.2] },
                    { value: 0.7, color: [0.9, 0.6, 0.6] },
                    { value: 1.0, color: [1.0, 0.9, 0.9] }
                ];
                break;
            default:
                baseFunction.color = [
                    { value: 0.0, color: [0, 0, 0] },
                    { value: 0.5, color: [0.5, 0.5, 0.5] },
                    { value: 1.0, color: [1.0, 1.0, 1.0] }
                ];
        }

        return baseFunction;
    }

    /**
     * Create transfer function for US rendering
     */
    createUSTransferFunction() {
        return {
            opacity: [
                { value: 0, opacity: 0.0 },
                { value: 64, opacity: 0.1 },
                { value: 128, opacity: 0.3 },
                { value: 192, opacity: 0.7 },
                { value: 255, opacity: 1.0 }
            ],
            color: [
                { value: 0, color: [0, 0, 0] },
                { value: 64, color: [0.2, 0.1, 0.0] },
                { value: 128, color: [0.6, 0.4, 0.2] },
                { value: 192, color: [0.9, 0.7, 0.5] },
                { value: 255, color: [1.0, 1.0, 1.0] }
            ]
        };
    }

    /**
     * Generate cache key for volume
     */
    generateCacheKey(dicomSeries, options) {
        const seriesUID = dicomSeries[0]?.SeriesInstanceUID || 'unknown';
        const optionsHash = JSON.stringify(options);
        return `${seriesUID}_${btoa(optionsHash).slice(0, 8)}`;
    }

    /**
     * Clear volume cache
     */
    clearCache() {
        this.volumeCache.clear();
    }

    /**
     * Get cache statistics
     */
    getCacheStats() {
        return {
            size: this.volumeCache.size,
            keys: Array.from(this.volumeCache.keys())
        };
    }
}

export default DicomVolumeProcessor;