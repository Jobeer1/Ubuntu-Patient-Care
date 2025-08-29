# Voice Processing System - Medical Reporting Module

## Overview

The Voice Processing System provides offline-first speech-to-text capabilities specifically designed for South African medical professionals. It includes medical terminology optimization, accent adaptation, and intelligent voice command processing.

## Features

### 🎤 Offline-First Speech-to-Text
- **Local Processing**: Uses OpenAI Whisper for offline speech recognition
- **Medical Terminology**: Optimized vocabulary for South African medical context
- **Accent Support**: Specialized processing for South African English accents
- **Learning Engine**: Adapts to user corrections and improves over time

### 🗣️ Voice Commands
- **Template Loading**: "Load chest x-ray template", "Use TB screening template"
- **Navigation**: "Go to findings section", "Move to impression"
- **Dictation Control**: "Start dictation", "Stop dictation", "Pause dictation"
- **Quick Fill**: "Normal chest study", "No acute findings"
- **System Control**: "Save report", "Submit report"

### 🏥 South African Medical Context
- **TB Screening**: Specialized templates and terminology for tuberculosis
- **Occupational Diseases**: Support for silicosis, pneumoconiosis, asbestosis
- **Trauma**: High-priority templates for gunshot wounds, MVA, fractures
- **HIV-Related**: PCP, Kaposi's sarcoma, opportunistic infections
- **Mining-Related**: Dust lung diseases, occupational health

## Installation

### Prerequisites
```bash
# Install OpenAI Whisper for offline STT (optional but recommended)
pip install openai-whisper

# Install audio processing dependencies
pip install numpy scipy librosa

# Install Flask and other web dependencies
pip install flask flask-socketio
```

### Quick Start
```python
from services.voice_engine import VoiceEngine

# Initialize voice engine
engine = VoiceEngine()

# Start a dictation session
session = engine.start_session("doctor_id", "report_id")

# Start listening
engine.start_listening()

# Simulate dictation (for testing)
engine.simulate_dictation("The lungs are clear bilaterally")

# Get transcription
transcription = engine.get_session_transcription()
print(transcription)
```

## API Endpoints

### Session Management
```http
POST /api/voice/session/start
POST /api/voice/session/end
GET  /api/voice/session/status
```

### Voice Input
```http
POST /api/voice/listen/start
POST /api/voice/listen/stop
POST /api/voice/upload
POST /api/voice/simulate
```

### Learning & Corrections
```http
POST /api/voice/correction
GET  /api/voice/stats
```

### Templates & Commands
```http
GET /api/voice/templates
GET /api/voice/commands
GET /api/voice/examples
```

## Configuration

### STT Configuration
```python
from services.offline_stt_service import STTConfig, STTMode

config = STTConfig(
    mode=STTMode.OFFLINE_ONLY,  # or ONLINE_PREFERRED, HYBRID
    language="en",              # English for South Africa
    model_size="base",          # Whisper model: tiny, base, small, medium, large
    enable_medical_terminology=True,
    enable_learning=True,
    confidence_threshold=0.7
)
```

### Voice Commands
```python
# Add custom template
from services.offline_voice_commands import offline_voice_commands

offline_voice_commands.add_custom_template(
    "mammography screening", 
    "mammography_template"
)
```

## Medical Vocabulary

### Respiratory (High Priority in SA)
- Tuberculosis, TB, MDR-TB, XDR-TB
- Pneumoconiosis, Silicosis, Asbestosis
- Pneumonia, Consolidation, Atelectasis
- Pleural effusion, Pneumothorax

### HIV-Related (High Prevalence)
- Pneumocystis pneumonia (PCP)
- Kaposi's sarcoma
- Cryptococcal meningitis
- Opportunistic infections

### Trauma (High Incidence)
- Gunshot wound (GSW)
- Motor vehicle accident (MVA)
- Stab wound, Fracture, Dislocation

### Common Findings
- Within normal limits
- No acute abnormality
- Unremarkable
- Consistent with
- Suggestive of

## Voice Commands Examples

### Template Loading
```
"Load chest x-ray template"
"Use TB screening template"
"Open fracture template"
"Switch to CT chest template"
```

### Navigation
```
"Go to findings section"
"Move to impression"
"Jump to conclusion"
"Show history section"
```

### Dictation Control
```
"Start dictation"
"Stop dictation"
"Pause dictation"
"Resume dictation"
```

### Quick Fill
```
"Normal chest study"
"No acute findings"
"Within normal limits"
"Unremarkable examination"
```

### System Control
```
"Save report"
"Submit report"
"New report"
"Delete report"
```

## Learning System

### Correction Recording
```python
# Record a correction for learning
engine.record_correction(
    user_id="doctor123",
    original_text="numonia in the lung",
    corrected_text="pneumonia in the lung"
)
```

### Statistics
```python
# Get learning statistics
stats = engine.get_stt_stats("doctor123")
print(f"Total corrections: {stats['total_corrections']}")
print(f"User corrections: {stats['user_corrections']}")
```

## Audio Quality Analysis

### Quality Assessment
```python
from utils.voice_utils import analyze_voice_audio

# Analyze audio quality
audio_data = open("recording.wav", "rb").read()
analysis = analyze_voice_audio(audio_data)

print(f"Quality: {analysis['quality']}")
print(f"Recommendations: {analysis['recommendations']}")
```

### Quality Levels
- **Excellent**: Clear audio, low noise, good volume
- **Good**: Minor background noise, acceptable quality
- **Fair**: Some noise or volume issues, usable
- **Poor**: High noise, low volume, may affect accuracy

## South African Accent Processing

### Accent Variations
```python
from utils.voice_utils import SouthAfricanAccentProcessor

processor = SouthAfricanAccentProcessor()
variations = processor.process_accent_variations("tuberculosis")
# Returns: ["tuberculosis", "tuberkulosis", ...]
```

### Common Patterns
- TH-fronting: "think" → "fink"
- R-dropping: "water" → "wata"
- Vowel shifts: "kit" → "ket"
- Diphthong reduction: "about" → "aboot"

## Testing

### Run Voice Processing Tests
```bash
# Simple test (no Whisper required)
python test_voice_simple.py

# Full test suite (requires pytest)
python -m pytest tests/test_voice_processing.py -v
```

### Test Coverage
- ✅ Voice Engine initialization and session management
- ✅ Offline STT engine with medical vocabulary
- ✅ Voice command processing and recognition
- ✅ South African accent processing
- ✅ Medical terminology correction
- ✅ Audio quality analysis
- ✅ Learning engine and corrections
- ✅ API endpoints and error handling

## Performance Optimization

### Offline Processing
- **Model Size**: Use "base" model for balance of speed/accuracy
- **Chunking**: Process audio in 5-second chunks for real-time feel
- **Caching**: Cache frequently used medical terms
- **Threading**: Background processing to avoid UI blocking

### Memory Management
- **Model Loading**: Load Whisper model once at startup
- **Audio Buffering**: Efficient audio data handling
- **Correction Limits**: Keep last 100 corrections per user
- **Cleanup**: Automatic cleanup of old audio files

## Troubleshooting

### Common Issues

#### Whisper Not Installed
```
Error: OpenAI Whisper not installed
Solution: pip install openai-whisper
```

#### Poor Audio Quality
```
Issue: Low transcription accuracy
Solutions:
- Check microphone positioning
- Reduce background noise
- Increase speaking volume
- Use better quality microphone
```

#### Voice Commands Not Recognized
```
Issue: Commands not executing
Solutions:
- Speak clearly and slowly
- Use exact command phrases
- Check command examples in API
- Verify active voice session
```

#### Database Errors
```
Issue: Cache database errors
Solution: Check write permissions in cache directory
```

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed logging for voice components
logger = logging.getLogger('services.voice_engine')
logger.setLevel(logging.DEBUG)
```

## Production Deployment

### Requirements
- Python 3.8+
- 4GB RAM minimum (8GB recommended for Whisper)
- SSD storage for model files
- Microphone access permissions
- Audio processing libraries

### Configuration
```python
# Production settings
VOICE_CONFIG = {
    'STT_MODE': 'OFFLINE_ONLY',
    'WHISPER_MODEL': 'base',
    'CACHE_SIZE': '1GB',
    'MAX_AUDIO_DURATION': 300,  # 5 minutes
    'CONFIDENCE_THRESHOLD': 0.8
}
```

### Monitoring
- Audio processing latency
- STT accuracy rates
- Voice command success rates
- User correction frequency
- System resource usage

## Security Considerations

### Voice Data Protection
- **Encryption**: All voice recordings encrypted at rest
- **Retention**: Automatic deletion after processing
- **Access Control**: Role-based access to voice data
- **Audit Logging**: All voice operations logged

### POPIA Compliance
- User consent for voice processing
- Data minimization principles
- Right to deletion
- Secure data transmission

## Future Enhancements

### Planned Features
- **Multi-language Support**: Afrikaans, Zulu, Xhosa
- **Speaker Recognition**: User-specific voice models
- **Real-time Collaboration**: Multi-user dictation sessions
- **Advanced Commands**: Complex workflow automation
- **Cloud Sync**: Optional cloud-based learning sync

### Integration Opportunities
- **PACS Integration**: Direct DICOM metadata dictation
- **RIS Integration**: Automated report routing
- **Mobile Apps**: Smartphone dictation support
- **Wearables**: Smart watch voice commands

## Support

### Documentation
- API Reference: `/docs/api/voice`
- User Guide: `/docs/user/voice-dictation`
- Admin Guide: `/docs/admin/voice-setup`

### Contact
- Technical Support: support@medical-reporting.co.za
- Feature Requests: features@medical-reporting.co.za
- Bug Reports: bugs@medical-reporting.co.za

---

**Note**: This voice processing system is specifically designed for South African medical professionals and includes terminology, accents, and disease patterns common in the South African healthcare context.