/**
 * Clinical CT Window/Level Presets
 * Optimized for emergency radiology diagnosis
 */

export const CT_PRESETS = {
  // Brain imaging
  BRAIN: {
    name: 'Brain',
    window: 80,
    level: 40,
    description: 'Stroke, hemorrhage, mass effect',
    hotkey: '1',
    color: 'grayscale'
  },
  
  SUBDURAL: {
    name: 'Subdural',
    window: 200,
    level: 75,
    description: 'Subdural hematoma, extra-axial collections',
    hotkey: '2',
    color: 'grayscale'
  },
  
  STROKE: {
    name: 'Stroke',
    window: 40,
    level: 40,
    description: 'Acute ischemic stroke, early changes',
    hotkey: '3',
    color: 'grayscale'
  },
  
  // Chest imaging
  LUNG: {
    name: 'Lung',
    window: 1500,
    level: -600,
    description: 'Pneumonia, nodules, interstitial disease',
    hotkey: '4',
    color: 'grayscale'
  },
  
  MEDIASTINUM: {
    name: 'Mediastinum',
    window: 350,
    level: 50,
    description: 'Aorta, lymph nodes, mediastinal masses',
    hotkey: '5',
    color: 'grayscale'
  },
  
  PE: {
    name: 'PE (Pulmonary Embolism)',
    window: 700,
    level: 100,
    description: 'Pulmonary embolism protocol',
    hotkey: '6',
    color: 'grayscale'
  },
  
  // Abdomen/Pelvis
  ABDOMEN: {
    name: 'Abdomen',
    window: 400,
    level: 40,
    description: 'Liver, spleen, kidneys, soft tissue',
    hotkey: '7',
    color: 'grayscale'
  },
  
  LIVER: {
    name: 'Liver',
    window: 150,
    level: 60,
    description: 'Hepatic lesions, metastases',
    hotkey: '8',
    color: 'grayscale'
  },
  
  // Bone imaging
  BONE: {
    name: 'Bone',
    window: 2000,
    level: 300,
    description: 'Fractures, bone lesions',
    hotkey: '9',
    color: 'grayscale'
  },
  
  SPINE: {
    name: 'Spine',
    window: 250,
    level: 50,
    description: 'Vertebrae, discs, spinal canal',
    hotkey: '0',
    color: 'grayscale'
  },
  
  // Vascular
  ANGIO: {
    name: 'Angiography',
    window: 600,
    level: 200,
    description: 'CTA, contrast-enhanced vessels',
    hotkey: 'A',
    color: 'hot'
  },
  
  // Soft tissue
  SOFT_TISSUE: {
    name: 'Soft Tissue',
    window: 350,
    level: 40,
    description: 'Muscles, fat planes, inflammation',
    hotkey: 'S',
    color: 'grayscale'
  }
};

/**
 * Auto-select preset based on series description
 */
export function autoSelectPreset(seriesDescription, bodyPart) {
  const desc = (seriesDescription || '').toLowerCase();
  const part = (bodyPart || '').toLowerCase();
  
  // Brain
  if (part.includes('head') || part.includes('brain') || desc.includes('brain')) {
    if (desc.includes('stroke')) return 'STROKE';
    if (desc.includes('subdural') || desc.includes('sdh')) return 'SUBDURAL';
    return 'BRAIN';
  }
  
  // Chest
  if (part.includes('chest') || part.includes('thorax') || desc.includes('chest')) {
    if (desc.includes('pe') || desc.includes('pulmonary embolism') || desc.includes('ctpa')) {
      return 'PE';
    }
    if (desc.includes('lung') || desc.includes('parenchyma')) return 'LUNG';
    if (desc.includes('mediastin') || desc.includes('aorta')) return 'MEDIASTINUM';
    return 'MEDIASTINUM';
  }
  
  // Abdomen
  if (part.includes('abdomen') || part.includes('liver') || desc.includes('abdomen')) {
    if (desc.includes('liver')) return 'LIVER';
    return 'ABDOMEN';
  }
  
  // Spine
  if (part.includes('spine') || part.includes('cervical') || 
      part.includes('thoracic') || part.includes('lumbar')) {
    return 'SPINE';
  }
  
  // Bone
  if (desc.includes('bone') || desc.includes('fracture') || desc.includes('trauma')) {
    return 'BONE';
  }
  
  // Angio
  if (desc.includes('angio') || desc.includes('cta') || desc.includes('vessel')) {
    return 'ANGIO';
  }
  
  // Default to soft tissue
  return 'SOFT_TISSUE';
}

/**
 * Get preset by name or hotkey
 */
export function getPreset(identifier) {
  // Direct name lookup
  if (CT_PRESETS[identifier]) {
    return CT_PRESETS[identifier];
  }
  
  // Hotkey lookup
  for (const [key, preset] of Object.entries(CT_PRESETS)) {
    if (preset.hotkey === identifier) {
      return preset;
    }
  }
  
  return null;
}

/**
 * Calculate optimal window/level from image statistics
 */
export function calculateOptimalWL(pixelData, modality = 'CT') {
  if (!pixelData || pixelData.length === 0) {
    return { window: 400, level: 40 };
  }
  
  // Calculate histogram
  const histogram = new Array(4096).fill(0);
  let min = Infinity;
  let max = -Infinity;
  
  for (let i = 0; i < pixelData.length; i++) {
    const value = pixelData[i];
    min = Math.min(min, value);
    max = Math.max(max, value);
    
    // Bin into histogram (shift to positive range)
    const bin = Math.floor((value + 1024) / 2);
    if (bin >= 0 && bin < 4096) {
      histogram[bin]++;
    }
  }
  
  // Find 1st and 99th percentile (ignore outliers)
  const totalPixels = pixelData.length;
  const p1 = Math.floor(totalPixels * 0.01);
  const p99 = Math.floor(totalPixels * 0.99);
  
  let count = 0;
  let p1Value = min;
  let p99Value = max;
  
  for (let i = 0; i < histogram.length; i++) {
    count += histogram[i];
    if (count >= p1 && p1Value === min) {
      p1Value = (i * 2) - 1024;
    }
    if (count >= p99) {
      p99Value = (i * 2) - 1024;
      break;
    }
  }
  
  // Calculate window and level
  const window = p99Value - p1Value;
  const level = (p1Value + p99Value) / 2;
  
  return {
    window: Math.round(window),
    level: Math.round(level)
  };
}

/**
 * Adjust window/level for better visualization
 */
export function adjustWL(currentWL, delta, type = 'window') {
  const { window, level } = currentWL;
  
  if (type === 'window') {
    // Adjust window (contrast)
    const newWindow = Math.max(1, window + delta);
    return { window: newWindow, level };
  } else {
    // Adjust level (brightness)
    const newLevel = level + delta;
    return { window, level: newLevel };
  }
}

/**
 * Apply window/level to pixel data
 */
export function applyWindowLevel(pixelValue, window, level) {
  const minValue = level - window / 2;
  const maxValue = level + window / 2;
  
  if (pixelValue <= minValue) {
    return 0;
  } else if (pixelValue >= maxValue) {
    return 255;
  } else {
    return Math.round(((pixelValue - minValue) / window) * 255);
  }
}
