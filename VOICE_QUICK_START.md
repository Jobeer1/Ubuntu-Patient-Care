# Quick Start: Voice & TTS Features

## Installation (2 minutes)

### Step 1: Install Whisper for Voice Input
```bash
pip install openai-whisper
```

### Step 2: Get ElevenLabs API Key
1. Go to https://elevenlabs.io/app/account
2. Copy your API key
3. In SDOH Chat, click ⚙️ → Find "TEXT-TO-SPEECH SETTINGS"
4. Paste API key → Save Changes

### Step 3: Test It
1. Open SDOH Chat
2. Click 🎤 VOICE → select audio file
3. Message appears (transcribed)
4. Agent responds
5. Click 🔊 LISTEN → hear response

---

## What Users Can Do

### Record a Voice Question
```
User: *clicks 🎤 VOICE → uploads audio*
Whisper: "I need help with conflict resolution"
The Forge: "Conflict resolution is deep work..."
User: *clicks 🔊 LISTEN → hears response in Rachel's voice*
```

### Customize Voice Settings
- **Voice**: Rachel, Bella, Charlotte, Adam, Chris
- **Stability**: Control how consistent the voice sounds
- **Clarity**: Make speech more clear or more artistic
- **Speaking Rate**: 0.5x to 2x speed
- **Pitch**: -20 to +20 semitones to adjust tone

All settings saved automatically in Settings ⚙️

---

## Costs

| Feature | Cost | Details |
|---------|------|---------|
| **Voice Input** | FREE | Runs locally, no external API |
| **Text-to-Speech** | FREE (10k chars/month) | [ElevenLabs pricing](https://elevenlabs.io/pricing) |

---

## Architecture

```
User Records Audio
    ↓
Frontend: Upload to /api/dictation/transcribe
    ↓
Backend: Whisper Mini transcribes locally
    ↓
Frontend: Text appears in input box
    ↓
User sends message to Forge
    ↓
Forge responds
    ↓
Frontend: 🔊 LISTEN button appears
    ↓
User clicks → Frontend calls ElevenLabs API
    ↓
ElevenLabs: Returns audio stream
    ↓
Browser: Plays audio with selected voice
```

---

## Troubleshooting

**Voice input not working?**
- Check: `pip list | grep whisper`
- If missing: `pip install openai-whisper`

**TTS not playing?**
- Check: Settings ⚙️ → Do you have ElevenLabs API key?
- If not: Add one from https://elevenlabs.io
- If yes: Check browser console (F12) for errors

**Whisper installation issues?**
- Try: `pip install --upgrade openai-whisper`
- On Mac/Linux: May need to install FFmpeg first
  ```bash
  # macOS
  brew install ffmpeg
  
  # Ubuntu/Debian
  sudo apt-get install ffmpeg
  ```

---

## Files Modified

- ✅ `frontend/dashboard.html` - Added voice/TTS UI
- ✅ `flask_app.py` - Added `/api/dictation/transcribe` endpoint
- ✅ `agent_forge.py` - (No changes, still works)

---

Ready to go! 🚀
