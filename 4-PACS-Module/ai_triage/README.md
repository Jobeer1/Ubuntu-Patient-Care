# AI Triage Pipeline for Ultra-Low Bandwidth Teleradiology

## Overview

This module implements an AI-driven data economy solution that reduces medical imaging data transfer by >90% while maintaining diagnostic quality.

**The Core Insight**: Diagnostic information is the 1% signal; the 99% noise is the cost.

## Architecture

```
DICOM Study (1 GB) → CNN Triage → Critical Slices (20 MB) → GAN Enhancement → Radiologist
```

## Components

### 1. CNN Model Manager (`model_manager.py`)
Manages lightweight, quantized CNN models for different imaging modalities.

### 2. Slice Triage Engine (`triage_engine.py`)
Performs anomaly detection and selects critical ROI slices.

### 3. GAN Enhancement Service (`gan_service.py`)
Denoises and enhances image quality for better diagnosis.

### 4. Audit Service (`audit_service.py`)
Logs cost savings to blockchain ledger.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Download models
python download_models.py

# Process a study
python run_triage.py --study-uid 1.2.840.113619.2.55.3...

# View results
python visualize_results.py --study-uid 1.2.840.113619.2.55.3...
```

## Configuration

Edit `config.yaml`:

```yaml
models:
  chest_ct_nodule: models/chest_ct_squeezenet_v1.onnx
  abdomen_mr_bleed: models/abdomen_mr_shufflenet_v1.onnx
  
triage:
  top_k_slices: 15
  confidence_threshold: 0.75
  max_processing_time: 300
  
enhancement:
  enabled: true
  model: models/unet_denoiser_v1.onnx
```

## Model Training

See [TRAINING.md](./TRAINING.md) for instructions on training custom models.

## Contributing

This is a community challenge! See [COMMUNITY_CHALLENGE.md](../../specs/ai-teleradiology/COMMUNITY_CHALLENGE.md) for how to contribute.

## License

MIT License - See [LICENSE](../../LICENSE)
