import os
import io
import threading
import queue
import time

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
_model_lock = threading.Lock()
_initialization_queue = queue.Queue()

def init_silero():
    """Initialize Silero TTS model (thread-safe, lazy-loaded)"""
    global _model, _device
    
    if not AVAILABLE:
        return None
        
    if _model is not None:
        return _model

    with _model_lock:
        # Double-check pattern: model might have been loaded while waiting for lock
        if _model is not None:
            return _model
        
        try:
            _device = torch.device('cpu')
            print("⏳ Loading Silero TTS model (background)...")
            start = time.time()
            
            # Load the latest v3_en model
            # We use torch.hub which caches the model locally
            _model, _ = torch.hub.load(repo_or_dir='snakers4/silero-models',
                                       model='silero_tts',
                                       language='en',
                                       speaker='v3_en')
            _model.to(_device)
            # Note: Silero model doesn't support .eval() - it's not a standard nn.Module
            
            elapsed = time.time() - start
            print(f"✅ Silero TTS model loaded in {elapsed:.2f}s")
            return _model
        except Exception as e:
            print(f"⚠️ Failed to load Silero TTS: {e}")
            return None

def warmup_tts():
    """Warmup TTS in background thread on startup"""
    def _warmup():
        try:
            model = init_silero()
            if model:
                # Generate a short test audio to warmup
                print("🔥 Warming up TTS model...")
                test_audio = model.apply_tts(text="Hi", speaker='en_0', sample_rate=48000)
                print("✅ TTS warmup complete - ready for fast generation")
        except Exception as e:
            print(f"⚠️ TTS warmup failed: {e}")
    
    # Run in background thread, don't block startup
    t = threading.Thread(target=_warmup, daemon=True)
    t.start()

def generate_audio(text, speaker='en_0'):
    """
    Generate audio using Silero TTS (fast, ~100ms after warmup)
    Returns: BytesIO object containing WAV data
    """
    if not AVAILABLE:
        raise Exception("Local TTS dependencies (torch/torchaudio) not installed")

    model = init_silero()
    if not model:
        raise Exception("TTS model not available")

    # Generate audio
    sample_rate = 48000
    
    try:
        # Text preprocessing: remove extra whitespace, limit length to prevent hangs
        text = ' '.join(text.split())[:500]  # Max 500 chars
        
        if not text:
            raise ValueError("Empty text after preprocessing")
        
        # With torch.no_grad() for faster inference (no gradient computation)
        with torch.no_grad():
            audio = model.apply_tts(text=text,
                                    speaker=speaker,
                                    sample_rate=sample_rate)
        
        # Audio is a 1D tensor. Add channel dimension for torchaudio
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
