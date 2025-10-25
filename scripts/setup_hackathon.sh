#!/bin/bash

# Setup script for Ubuntu Patient Care Hackathon Demo
echo "🏥 Setting up Ubuntu Patient Care System..."

# Create models directory if it doesn't exist
mkdir -p Orthanc/medical-reporting-module/models/whisper/cache

# Download model weights from cloud storage
echo "📥 Downloading Whisper model weights..."

# You can replace these URLs with actual cloud storage URLs (Google Drive, OneDrive, etc.)
# For now, we'll download from Hugging Face as a fallback
echo "⚠️  Please upload your model weights to cloud storage and update these URLs:"
echo "   - base.pt (138MB)"
echo "   - medium_temp.pt (1.16GB)"

# Fallback: Download smaller model from Hugging Face
echo "🔄 Downloading fallback Whisper models from Hugging Face..."
cd Orthanc/medical-reporting-module/models/whisper

# Install required packages if not already installed
pip install -q transformers torch

# Download smaller model as fallback
python -c "
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration

print('Downloading Whisper base model...')
processor = WhisperProcessor.from_pretrained('openai/whisper-base')
model = WhisperForConditionalGeneration.from_pretrained('openai/whisper-base')

# Save model in the expected format
torch.save(model.state_dict(), 'base_fallback.pt')
print('✅ Fallback model downloaded successfully!')
"

cd ../../../..

echo "🚀 Setup complete! You can now run the Ubuntu Patient Care system."
echo "📝 Note: For full functionality, upload your custom model weights to cloud storage."
echo "🌐 Start the system with: python Orthanc/medical-reporting-module/core/app_factory.py"
