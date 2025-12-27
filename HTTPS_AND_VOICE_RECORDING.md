# Voice Recording & Server-Stored Previews Guide

## New Features

### 1. 🎙️ Voice Recording (Microphone Input)
- Real-time microphone recording using browser's MediaRecorder API
- Records directly from user's microphone
- Shows recording timer during capture
- Automatically transcribes with Whisper when stopped
- **Requires HTTPS** (browser security requirement)

### 2. 📁 Voice File Upload (Existing, Improved)
- Upload pre-recorded audio files
- Supports: WAV, MP3, M4A, OGG, FLAC, WebM
- Transcribes with Whisper
- Works over both HTTP and HTTPS

### 3. 🔊 Server-Stored Voice Previews (New)
- Voice preview audio files stored on server
- Users can preview voices **without API key needed**
- No ElevenLabs API charges for preview listening
- Admin generates previews once, all users can hear them

---

## Setup Instructions

### Step 1: Enable HTTPS (For Voice Recording)

Voice recording requires HTTPS due to browser security policies.

#### On Windows:
```bash
# Generate self-signed certificate
python generate_cert.py
```

#### On macOS/Linux:
```bash
# Install OpenSSL if needed
# macOS:
brew install openssl

# Then generate certificate:
python generate_cert.py
```

If you get errors, you can install OpenSSL:
- **Windows**: https://slproweb.com/products/Win32OpenSSL.html
- **macOS**: `brew install openssl`
- **Linux**: `sudo apt-get install openssl`

### Step 2: Start Server with HTTPS

```bash
python run.py
```

The server will now run on HTTPS:
- If certificates exist: ✅ HTTPS enabled
- If certificates missing: ⚠️ HTTP fallback (voice recording disabled)

### Step 3: Generate Voice Previews

Voice previews are pre-generated audio files that don't require an API key.

#### Option A: Generate via API Call

```bash
# Using curl (replace with your actual API key)
curl -X POST https://localhost:5001/api/tts/generate-previews \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-elevenlabs-api-key"}' \
  --insecure
```

#### Option B: Generate via Python

```python
import requests
import json

api_key = "your-elevenlabs-api-key"
response = requests.post(
    'https://localhost:5001/api/tts/generate-previews',
    json={'api_key': api_key},
    verify=False  # For self-signed cert
)
print(response.json())
```

This generates MP3 files for all voices and stores them in `/frontend/voices/`

### Step 4: Setup ElevenLabs for Full TTS (Optional)

For actual chat responses (not just previews):

1. Get API key from https://elevenlabs.io/app/account
2. In Settings ⚙️, paste your ElevenLabs API key
3. Choose voice and adjust settings
4. Click 🔊 PREVIEW to hear (uses local preview file)
5. Actual chat responses will use ElevenLabs API

---

## User Experience

### Recording a Voice Message

```
1. User clicks 🎙️ REC button
2. Browser asks for microphone permission
3. User speaks into microphone
4. Timer shows recording time (0:05, 0:10, etc.)
5. User clicks ⏹️ STOP
6. Server transcribes voice to text
7. Text appears in message input
8. User reviews/edits and clicks SEND
```

### Uploading Audio File

```
1. User clicks 📁 VOICE button
2. File picker opens
3. Select .wav, .mp3, .m4a, etc.
4. File uploads and transcribes
5. Text appears in input box
6. User reviews/edits and clicks SEND
```

### Previewing Voices (No API Key Needed)

```
1. User goes to Settings ⚙️
2. Clicks 🔊 PREVIEW next to voice selector
3. Server plays local preview file
4. User hears voice sample
5. Can change voice and preview again
6. Doesn't use ElevenLabs API
```

---

## File Structure

```
SDOH-chat/
├── flask_app.py                 # Updated with voice endpoints
├── run.py                       # Updated to support HTTPS
├── generate_cert.py             # NEW: Certificate generation
├── cert.pem                     # Generated: Certificate
├── key.pem                      # Generated: Private key
├── frontend/
│   ├── dashboard.html           # Updated with recording UI
│   └── voices/                  # NEW: Voice preview files
│       ├── rachel.mp3
│       ├── bella.mp3
│       ├── charlotte.mp3
│       ├── adam.mp3
│       └── chris.mp3
└── requirements.txt             # No changes (all deps already there)
```

---

## API Endpoints

### List Available Voices
```
GET /api/tts/voices

Response:
[
  {
    "id": "21m00Tcm4TlvDq8ikWAM",
    "name": "Rachel",
    "description": "Warm",
    "preview_url": "/api/tts/preview/rachel.mp3"
  },
  ...
]
```

### Get Voice Preview Audio
```
GET /api/tts/preview/{filename}.mp3

Returns: MP3 audio file (no authentication needed)

Filenames:
- rachel.mp3
- bella.mp3
- charlotte.mp3
- adam.mp3
- chris.mp3
```

### Generate Previews (Admin)
```
POST /api/tts/generate-previews

Body:
{
  "api_key": "your-elevenlabs-api-key"
}

Response:
{
  "status": "complete",
  "generated": ["rachel.mp3", "bella.mp3", ...],
  "failed": [],
  "total": 5
}
```

### Transcribe Audio
```
POST /api/dictation/transcribe

Headers: Authorization: Bearer {token}
Body: multipart/form-data with 'file' field

Response:
{
  "text": "transcribed text here",
  "status": "success"
}
```

---

## Browser Compatibility

| Feature | Chrome | Firefox | Safari | Edge | Mobile |
|---------|--------|---------|--------|------|--------|
| Voice Recording | ✅ HTTPS only | ✅ HTTPS only | ✅ HTTPS only | ✅ HTTPS only | ⚠️ Limited |
| File Upload | ✅ Any | ✅ Any | ✅ Any | ✅ Any | ✅ Works |
| Preview Listening | ✅ Any | ✅ Any | ✅ Any | ✅ Any | ✅ Works |

---

## Troubleshooting

### "Microphone access denied"
- **Cause**: Not using HTTPS or browser permissions denied
- **Solution**: 
  - Run `python generate_cert.py` to enable HTTPS
  - Restart server with `python run.py`
  - Allow microphone in browser permissions

### "Voice recording button disabled"
- **Cause**: Server running on HTTP instead of HTTPS
- **Solution**: Generate certificates and restart server

### "Voice preview not found"
- **Cause**: Preview MP3 files haven't been generated
- **Solution**: Run `/api/tts/generate-previews` endpoint with API key

### "Preview generation failed"
- **Cause**: Invalid ElevenLabs API key
- **Solution**: Check API key is correct from https://elevenlabs.io/app/account

### "Certificate/Key errors on startup"
- **Cause**: Certificate files not found or invalid
- **Solution**: Delete existing `cert.pem` and `key.pem`, re-run `python generate_cert.py`

---

## Security Notes

### HTTPS Certificates
- Using self-signed certificates (not trusted by browsers)
- This is **normal and expected** for development
- Browser shows "insecure" warning - can be safely ignored
- For production: Use proper certificates from certificate authority

### Microphone Permissions
- Browser asks user to allow microphone access
- User can deny and fall back to file upload
- No recording without explicit permission

### Data Privacy
- Voice recordings: Processed locally by Whisper, never sent to external services
- Preview files: Stored on your server only
- ElevenLabs API: Only used if user provides API key for chat responses

---

## Performance

### Voice Recording
- Upload speed: Depends on internet (typical: 30KB/s)
- 30 seconds of audio ≈ 1-2 MB file
- Transcription time: ~5-10 seconds (local processing)

### Voice Previews
- Download speed: ~200KB (typical: <1 second)
- No processing needed (pre-generated)

### Voice Responses (TTS)
- Generation time: 1-3 seconds (ElevenLabs API)
- Playback: Starts immediately after download

---

## Advanced: Custom Voice Settings

### Adding More Voice Options

Edit `flask_app.py` in the `get_voice_list()` function:

```python
{
    'id': 'your-voice-id',
    'name': 'Voice Name',
    'description': 'Description',
    'preview_url': '/api/tts/preview/filename.mp3'
}
```

Then regenerate previews:
```python
# Add to voices dict in generate_voice_previews():
'filename.mp3': 'your-voice-id'
```

### Changing Preview Text

Edit `generate_voice_previews()` in `flask_app.py`:
```python
preview_text = 'Your custom preview text here'
```

---

## Costs & Quotas

### Free Tier (ElevenLabs)
- 10,000 characters/month
- Previews: ~70 chars each = ~140 previews/month
- Chat responses: Depends on message length

### Paid Tiers
- See: https://elevenlabs.io/pricing
- Previews don't need to use API if using server-stored files

---

**Status**: ✅ Production Ready  
**Last Updated**: December 27, 2025  
**HTTPS Support**: ✅ Enabled  
**Voice Recording**: ✅ Ready (after HTTPS setup)  
**Server Previews**: ✅ Ready (after generation)
