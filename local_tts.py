import os
import io

try:
    import torch
    import torchaudio
    AVAILABLE = True
except ImportError:
    AVAILABLE = False
    print("⚠️ Local TTS unavailable: torch or torchaudio not found")

# Global model cache
_model = None
_device = None

def init_silero():
    """Initialize Silero TTS model"""
    global _model, _device
    
    if not AVAILABLE:
        return None
        
    if _model is not None:
        return _model

    try:
        _device = torch.device('cpu')
        print("Loading Silero TTS model...")
        # Load the latest v3_en model
        # We use torch.hub which caches the model locally
        _model, _ = torch.hub.load(repo_or_dir='snakers4/silero-models',
                                   model='silero_tts',
                                   language='en',
                                   speaker='v3_en')
        _model.to(_device)
        print("✅ Silero TTS model loaded successfully")
        return _model
    except Exception as e:
        print(f"⚠️ Failed to load Silero TTS: {e}")
        return None

def generate_audio(text, speaker='en_0'):
    """
    Generate audio using Silero TTS
    Returns: BytesIO object containing WAV data
    """
    if not AVAILABLE:
        raise Exception("Local TTS dependencies (torch/torchaudio) not installed")

    model = init_silero()
    if not model:
        raise Exception("TTS model not available")

    # Generate audio
    # sample_rate is typically 48000 for v3_en
    sample_rate = 48000
    
    # Silero expects text and speaker
    # Speakers: 'en_0' to 'en_117' (v3 has many speakers)
    # 'en_0' is a good neutral voice
    
    try:
        audio = model.apply_tts(text=text,
                                speaker=speaker,
                                sample_rate=sample_rate)
        
        # Audio is a 1D tensor. Add channel dimension for torchaudio
        # shape: [channels, time]
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)
            
        # Save to in-memory buffer
        buff = io.BytesIO()
        torchaudio.save(buff, audio, sample_rate, format="wav")
        buff.seek(0)
        
        return buff
    except Exception as e:
        print(f"Error generating local audio: {e}")
        raise e
