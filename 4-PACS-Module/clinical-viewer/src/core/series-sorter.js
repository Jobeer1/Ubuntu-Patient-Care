/**
 * Intelligent DICOM Series Sorter
 * Handles any slice order, any modality, any acquisition type
 */

export class SeriesSorter {
  /**
   * Sort DICOM instances into correct anatomical order
   * @param {Array} instances - Array of DICOM instances with metadata
   * @returns {Array} Sorted instances
   */
  static sortSeries(instances) {
    if (!instances || instances.length === 0) {
      return [];
    }

    // Detect series type and choose appropriate sorting strategy
    const seriesType = this.detectSeriesType(instances[0]);
    
    switch (seriesType) {
      case 'CT_AXIAL':
      case 'MR_AXIAL':
        return this.sortByImagePosition(instances);
      
      case 'CT_HELICAL':
        return this.sortHelicalCT(instances);
      
      case 'MR_MULTIPHASE':
        return this.sortMultiPhase(instances);
      
      case 'LOCALIZER':
        return this.sortByInstanceNumber(instances);
      
      case 'DYNAMIC':
        return this.sortDynamic(instances);
      
      default:
        return this.sortByBestAvailable(instances);
    }
  }

  /**
   * Detect series acquisition type from metadata
   */
  static detectSeriesType(instance) {
    const metadata = instance.metadata;
    const modality = metadata.modality;
    const seriesDescription = (metadata.seriesDescription || '').toLowerCase();
    
    // Check for localizer/scout
    if (seriesDescription.includes('scout') || 
        seriesDescription.includes('localizer') ||
        seriesDescription.includes('topogram')) {
      return 'LOCALIZER';
    }
    
    // Check for dynamic/4D
    if (metadata.numberOfTemporalPositions > 1 || 
        seriesDescription.includes('dynamic') ||
        seriesDescription.includes('perfusion')) {
      return 'DYNAMIC';
    }
    
    // CT-specific
    if (modality === 'CT') {
      if (metadata.spiralPitchFactor || seriesDescription.includes('helical')) {
        return 'CT_HELICAL';
      }
      return 'CT_AXIAL';
    }
    
    // MR-specific
    if (modality === 'MR') {
      if (metadata.numberOfPhaseEncodingSteps && 
          metadata.echoTrainLength) {
        return 'MR_MULTIPHASE';
      }
      return 'MR_AXIAL';
    }
    
    return 'STANDARD';
  }

  /**
   * Sort by Image Position Patient (most reliable for cross-sectional)
   */
  static sortByImagePosition(instances) {
    return instances.sort((a, b) => {
      const posA = a.metadata.imagePositionPatient;
      const posB = b.metadata.imagePositionPatient;
      
      if (!posA || !posB) {
        return this.fallbackSort(a, b);
      }
      
      // Determine primary axis (usually Z for axial)
      const orientA = a.metadata.imageOrientationPatient;
      const axis = this.getPrimaryAxis(orientA);
      
      // Sort along primary axis
      return posA[axis] - posB[axis];
    });
  }

  /**
   * Sort helical CT with overlapping slices
   */
  static sortHelicalCT(instances) {
    // First sort by acquisition time
    const sorted = instances.sort((a, b) => {
      const timeA = a.metadata.acquisitionTime || a.metadata.contentTime || 0;
      const timeB = b.metadata.acquisitionTime || b.metadata.contentTime || 0;
      return timeA - timeB;
    });
    
    // Then by slice location
    return sorted.sort((a, b) => {
      const locA = a.metadata.sliceLocation || 0;
      const locB = b.metadata.sliceLocation || 0;
      return locA - locB;
    });
  }

  /**
   * Sort multi-phase MR (multiple echoes, phases)
   */
  static sortMultiPhase(instances) {
    // Group by temporal position first
    const groups = {};
    
    instances.forEach(inst => {
      const phase = inst.metadata.temporalPositionIdentifier || 
                    inst.metadata.instanceNumber || 0;
      if (!groups[phase]) {
        groups[phase] = [];
      }
      groups[phase].push(inst);
    });
    
    // Sort each phase by position
    const sorted = [];
    Object.keys(groups).sort((a, b) => a - b).forEach(phase => {
      const phaseSorted = this.sortByImagePosition(groups[phase]);
      sorted.push(...phaseSorted);
    });
    
    return sorted;
  }

  /**
   * Sort dynamic/4D series (perfusion, cardiac)
   */
  static sortDynamic(instances) {
    // Sort by temporal position, then by slice location
    return instances.sort((a, b) => {
      const timeA = a.metadata.temporalPositionIdentifier || 
                    a.metadata.acquisitionTime || 0;
      const timeB = b.metadata.temporalPositionIdentifier || 
                    b.metadata.acquisitionTime || 0;
      
      if (timeA !== timeB) {
        return timeA - timeB;
      }
      
      // Same time point, sort by location
      const locA = a.metadata.sliceLocation || 0;
      const locB = b.metadata.sliceLocation || 0;
      return locA - locB;
    });
  }

  /**
   * Sort by instance number (fallback)
   */
  static sortByInstanceNumber(instances) {
    return instances.sort((a, b) => {
      const numA = a.metadata.instanceNumber || 0;
      const numB = b.metadata.instanceNumber || 0;
      return numA - numB;
    });
  }

  /**
   * Best available sorting (tries multiple strategies)
   */
  static sortByBestAvailable(instances) {
    // Try image position first
    if (instances[0].metadata.imagePositionPatient) {
      return this.sortByImagePosition(instances);
    }
    
    // Try slice location
    if (instances[0].metadata.sliceLocation !== undefined) {
      return instances.sort((a, b) => {
        return a.metadata.sliceLocation - b.metadata.sliceLocation;
      });
    }
    
    // Fallback to instance number
    return this.sortByInstanceNumber(instances);
  }

  /**
   * Determine primary axis from image orientation
   */
  static getPrimaryAxis(orientation) {
    if (!orientation || orientation.length < 6) {
      return 2; // Default to Z
    }
    
    // Calculate normal vector (cross product of row and column vectors)
    const rowVec = orientation.slice(0, 3);
    const colVec = orientation.slice(3, 6);
    
    const normal = [
      rowVec[1] * colVec[2] - rowVec[2] * colVec[1],
      rowVec[2] * colVec[0] - rowVec[0] * colVec[2],
      rowVec[0] * colVec[1] - rowVec[1] * colVec[0]
    ];
    
    // Find dominant axis
    const absNormal = normal.map(Math.abs);
    return absNormal.indexOf(Math.max(...absNormal));
  }

  /**
   * Fallback sort when position data missing
   */
  static fallbackSort(a, b) {
    // Try slice location
    if (a.metadata.sliceLocation !== undefined && 
        b.metadata.sliceLocation !== undefined) {
      return a.metadata.sliceLocation - b.metadata.sliceLocation;
    }
    
    // Try instance number
    if (a.metadata.instanceNumber !== undefined && 
        b.metadata.instanceNumber !== undefined) {
      return a.metadata.instanceNumber - b.metadata.instanceNumber;
    }
    
    // Last resort: acquisition time
    const timeA = a.metadata.acquisitionTime || 0;
    const timeB = b.metadata.acquisitionTime || 0;
    return timeA - timeB;
  }

  /**
   * Validate sorting quality
   * @returns {Object} Quality metrics
   */
  static validateSorting(instances) {
    if (instances.length < 2) {
      return { valid: true, confidence: 1.0 };
    }
    
    let positionGaps = 0;
    let timeGaps = 0;
    
    for (let i = 1; i < instances.length; i++) {
      const prev = instances[i - 1].metadata;
      const curr = instances[i].metadata;
      
      // Check position continuity
      if (prev.sliceLocation !== undefined && curr.sliceLocation !== undefined) {
        const gap = Math.abs(curr.sliceLocation - prev.sliceLocation);
        const expectedGap = prev.sliceThickness || 1;
        if (Math.abs(gap - expectedGap) > expectedGap * 0.5) {
          positionGaps++;
        }
      }
      
      // Check temporal continuity
      if (prev.acquisitionTime && curr.acquisitionTime) {
        if (curr.acquisitionTime < prev.acquisitionTime) {
          timeGaps++;
        }
      }
    }
    
    const totalChecks = instances.length - 1;
    const confidence = 1.0 - ((positionGaps + timeGaps) / (totalChecks * 2));
    
    return {
      valid: confidence > 0.8,
      confidence: Math.max(0, confidence),
      positionGaps,
      timeGaps
    };
  }

  /**
   * Detect and fix reversed series
   */
  static detectReversed(instances) {
    if (instances.length < 3) {
      return false;
    }
    
    // Check if positions are decreasing when they should increase
    const positions = instances
      .map(i => i.metadata.sliceLocation || i.metadata.imagePositionPatient?.[2])
      .filter(p => p !== undefined);
    
    if (positions.length < 3) {
      return false;
    }
    
    // Calculate trend
    let increasing = 0;
    let decreasing = 0;
    
    for (let i = 1; i < positions.length; i++) {
      if (positions[i] > positions[i - 1]) increasing++;
      if (positions[i] < positions[i - 1]) decreasing++;
    }
    
    // If mostly decreasing, series is likely reversed
    return decreasing > increasing;
  }

  /**
   * Auto-correct reversed series
   */
  static autoCorrect(instances) {
    if (this.detectReversed(instances)) {
      console.log('Detected reversed series, auto-correcting...');
      return instances.reverse();
    }
    return instances;
  }
}
