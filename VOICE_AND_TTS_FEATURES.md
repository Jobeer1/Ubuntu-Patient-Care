# Voice & Text-to-Speech Features Guide

## Overview

SDOH Chat now supports:
1. **Voice Input** - Record or upload audio messages that are transcribed using Whisper Mini
2. **Text-to-Speech (TTS)** - Listen to agent responses using ElevenLabs with customizable voice settings

---

## Features

### 1. Voice Input (Speech-to-Text)

**How it works:**
- User clicks the **"🎤 VOICE"** button in the chat input area
- Uploads an audio file (WAV, MP3, M4A, etc.)
- Audio is transcribed using OpenAI's Whisper Mini model
- Transcribed text appears in the message input box
- User can edit and send the message

**Supported formats:**
- WAV, MP3, M4A, OGG, FLAC, WebM

**Setup:**
```bash
pip install openai-whisper
```

**Backend endpoint:**
```
POST /api/dictation/transcribe
- Requires: JWT token in Authorization header
- Body: multipart/form-data with 'file' field
- Returns: { text: "transcribed text", status: "success" }
```

---

### 2. Text-to-Speech (TTS) with ElevenLabs

**How it works:**
- Next to each agent message, a **"🔊 LISTEN"** button appears
- Click to hear the agent's response in a natural human voice
- Customize voice, stability, clarity, speaking rate, and pitch in Settings

**Available Voices:**
- **Rachel** (Warm, friendly) - Default
- **Bella** (Calm, soothing)
- **Prometheus** (Balanced, professional)
- **Charlotte** (Friendly, energetic)
- **Adam** (Serious, authoritative)
- **Chris** (Dynamic, expressive)

**Settings:**

| Setting | Range | Default | Meaning |
|---------|-------|---------|---------|
| **Stability** | 0-1 | 0.5 | Higher = more consistent voice, Lower = more variation |
| **Clarity** | 0-1 | 0.75 | Higher = clearer speech, Lower = more artistic |
| **Speaking Rate** | 0.5x-2x | 1.0x | Speed of speech (1x = normal speed) |
| **Pitch** | -20 to +20 semitones | 0 | Shifts voice up/down musically |

**Setup:**
1. Get ElevenLabs API key from https://elevenlabs.io/app/account
2. Go to Settings ⚙️ in SDOH Chat
3. Enter your ElevenLabs API key in "TEXT-TO-SPEECH SETTINGS"
4. Choose voice, adjust stability/clarity/rate/pitch
5. Click "SAVE CHANGES"

**Backend integration:**
```javascript
// TTS is handled entirely on the frontend
// Uses ElevenLabs API directly: https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
// Settings stored in browser localStorage for persistence
```

---

## Installation & Requirements

### Requirements
```bash
# For Voice Input (Whisper):
pip install openai-whisper

# For Text-to-Speech (already included):
# - Uses ElevenLabs API (no local installation needed)
# - Just need an API key from https://elevenlabs.io
```

### Backend Setup
1. Install Whisper:
   ```bash
   pip install openai-whisper
   ```

2. The Flask app will auto-detect Whisper availability
   - If available: ✅ Voice transcription enabled
   - If unavailable: ⚠️ Voice input disabled, warning in logs

### Frontend Setup
1. All voice/TTS UI is already in `frontend/dashboard.html`
2. Settings are stored in browser localStorage
3. No additional JavaScript libraries needed

---

## User Experience

### Sending a Voice Message

1. Click **🎤 VOICE** button
2. Select audio file from device
3. Wait for transcription (shows "🎤 TRANSCRIBING...")
4. Transcribed text appears in input box
5. Edit if needed (e.g., capitalize, correct)
6. Click **SEND**

### Listening to Agent Response

1. Agent sends response
2. **🔊 LISTEN** button appears below message
3. Click to hear the response
4. Button shows "🔊 PLAYING..." while audio plays
5. Can adjust voice settings anytime in Settings

---

## Settings Management

**Access Settings:**
- Click **⚙️** in top-right corner
- Scroll to "TEXT-TO-SPEECH SETTINGS"

**Settings Persist:**
- All TTS settings saved to browser localStorage
- Automatically restored when user returns
- Not uploaded to server (stays private)

**Clearing Settings:**
- Clear browser cache/localStorage to reset
- Or manually change values in Settings modal

---

## API Reference

### Frontend API Calls

**Voice Transcription:**
```javascript
POST /api/dictation/transcribe
Content-Type: multipart/form-data
Authorization: Bearer {token}

Body: { file: Audio File }

Response:
{
    "text": "transcribed text here",
    "status": "success",
    "confidence": "en"
}
```

**Agent Messages with TTS:**
- TTS button automatically added to each agent message
- Clicking button calls `speakMessage()` JavaScript function
- Connects to ElevenLabs API (frontend-to-ElevenLabs, not through backend)

---

## Troubleshooting

### Voice Input Not Working

**Issue:** "🎤 VOICE" button doesn't work
- **Solution:** Install Whisper: `pip install openai-whisper`
- **Check logs:** Flask will show warning if Whisper unavailable

**Issue:** "Transcription failed"
- **Solution:** Check file format (WAV, MP3, etc.)
- **Solution:** Ensure file is under 25MB
- **Solution:** Check server logs for detailed error

### Text-to-Speech Not Working

**Issue:** "🔊 LISTEN" button doesn't produce audio
- **Solution:** Add ElevenLabs API key in Settings
- **Solution:** Check internet connection
- **Solution:** Verify API key is valid (from elevenlabs.io)

**Issue:** Audio quality is poor
- **Solution:** Adjust **Clarity** setting (higher = clearer)
- **Solution:** Try different **Voice** option
- **Solution:** Check ElevenLabs account (may have rate limits)

**Issue:** Audio sounds wrong pitch/speed
- **Solution:** Adjust **Pitch** and **Speaking Rate** in Settings
- **Solution:** Adjust **Stability** for more consistent voice

---

## Technical Details

### Whisper Model
- **Model:** `base` (677MB, good accuracy-speed tradeoff)
- **Language:** English (can change in code)
- **Local Processing:** Audio never sent to external server
- **Speed:** ~30 seconds of audio = ~5-10 seconds transcription time

### ElevenLabs Integration
- **API:** https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
- **Method:** Frontend calls API directly (CORS enabled)
- **Audio Format:** MP3 (48kHz)
- **Streaming:** Audio streamed directly to browser audio player
- **Rate Limit:** Default 10,000 characters/month on free tier

---

## Cost & Privacy

### Voice Input (Whisper)
- **Cost:** FREE (OpenAI open-source model, runs locally)
- **Privacy:** Audio processed locally, never leaves your server

### Text-to-Speech (ElevenLabs)
- **Cost:** FREE tier = 10,000 characters/month
- **Pricing Tiers:** https://elevenlabs.io/pricing
- **Privacy:** API key must be user-provided (in Settings)
- **Note:** Each character of agent response counts toward limit

---

## Future Enhancements

Potential additions:
- [ ] Language selection (not just English)
- [ ] Custom voice cloning (upload voice sample)
- [ ] Streaming TTS (start playing while generating)
- [ ] Voice activity detection (auto-stop recording)
- [ ] Multi-language support for transcription
- [ ] Voice authentication (verify user by voice)
- [ ] Backend rate limiting for TTS usage

---

## Support

For issues or questions:
1. Check logs: Flask console for backend errors
2. Check browser console: F12 → Console tab for frontend errors
3. Test endpoint: `curl -X POST http://localhost:5001/api/dictation/transcribe -F "file=@audio.wav" -H "Authorization: Bearer {token}"`
4. Verify API keys: Check ElevenLabs dashboard for key validity

---

**Version:** 1.0  
**Last Updated:** December 27, 2025  
**Status:** Production Ready ✅
