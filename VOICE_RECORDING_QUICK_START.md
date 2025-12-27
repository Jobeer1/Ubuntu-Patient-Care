# Voice Recording & HTTPS - Quick Start (5 Minutes)

## Step-by-Step Setup

### 1. Generate HTTPS Certificates (2 minutes)

```bash
cd c:\Users\parkh\OneDrive\Desktop\05i_DEMO_Reinforcement\qubic-hackathon\GOTG_version\RIS-1\SDOH-chat

python generate_cert.py
```

**Expected output:**
```
🔐 Generating self-signed SSL certificate...
✅ Certificate generated: cert.pem
✅ Key generated: key.pem

🔒 HTTPS Enabled:
   URL: https://localhost:5001
   Note: Browser will show 'insecure' - this is normal for self-signed certs
```

### 2. Start Server (Auto-detects HTTPS)

```bash
python run.py
```

**You should see:**
```
[*] Starting HTTPS Server...
[*] URL: https://localhost:5001
[*] Chat: https://localhost:5001/sdoh/index.html
[*] Mode: HTTPS (Microphone enabled)
[✓] HTTPS enabled - microphone access available
```

### 3. Generate Voice Previews (1 minute, Optional)

Users can preview voices without API key, but need previews generated first.

**Option A: Using Python**
```bash
python

from flask import Flask
import requests

# Replace with your actual API key
API_KEY = "your-elevenlabs-api-key"

requests.post(
    'https://localhost:5001/api/tts/generate-previews',
    json={'api_key': API_KEY},
    verify=False
)
```

**Option B: Using curl**
```bash
curl -X POST https://localhost:5001/api/tts/generate-previews \
  -H "Content-Type: application/json" \
  -d "{\"api_key\": \"your-api-key\"}" \
  --insecure
```

### 4. Test in Browser

1. Open: https://localhost:5001/sdoh/index.html
2. Sign up / Login
3. Click "THE FORGE"

You should see TWO voice buttons:
- **🎙️ REC** - Record with microphone
- **📁 VOICE** - Upload audio file

---

## Using Voice Recording

### Record a Message

1. Click **🎙️ REC**
2. Browser asks for microphone permission → Click "Allow"
3. Speak into microphone
4. Timer shows: 🔴 Recording... 0:05
5. Click **⏹️ STOP** when done
6. System transcribes (shows "🎤 TRANSCRI…")
7. Text appears in message input
8. Edit if needed
9. Click **SEND**

### Upload Audio File

1. Click **📁 VOICE**
2. Select audio file (.wav, .mp3, .m4a, etc.)
3. System transcribes automatically
4. Text appears in input
5. Edit and click **SEND**

---

## Using Voice Previews

### Preview Available Voices (No API Key Needed)

1. Click Settings ⚙️
2. Scroll to "TEXT-TO-SPEECH SETTINGS"
3. Select voice from dropdown
4. Click **🔊 PREVIEW**
5. Hear voice sample from server

**Note**: Preview uses pre-generated files stored on server (not ElevenLabs API)

---

## Expected UI

### Chat Input Area
```
┌─────────────────────────────┬───────┬────────┬──────┐
│ Type message...             │ 🎙️REC│📁VOICE│ SEND │
└─────────────────────────────┴───────┴────────┴──────┘

When recording:
🔴 Recording... 0:05
```

### Settings Voice Section
```
Voice:
┌─────────────────────────────┬────────────┐
│ ▼ Rachel (Warm)             │🔊 PREVIEW  │
└─────────────────────────────┴────────────┘
```

---

## Troubleshooting

### "Microphone access denied"
```
Solution:
1. Check browser URL starts with https://
2. Check browser shows 🔒 lock icon
3. If not HTTPS: Run `python generate_cert.py`
4. Restart server: `python run.py`
```

### "Voice recording button is disabled"
```
Solution:
1. Server must be running on HTTPS
2. Certificates must exist (cert.pem, key.pem)
3. Run: python generate_cert.py
4. Then: python run.py
```

### "Voice preview not found"
```
Solution:
1. Need to generate previews first
2. Run: python (opens Python interpreter)
3. Then: (see "Step 3: Generate Voice Previews" above)
```

### Browser shows "Your connection is not private"
```
This is NORMAL for self-signed certificates
- Click "Advanced"
- Click "Proceed to localhost"
- This is safe for local development
```

---

## What Just Happened?

✅ **HTTPS Enabled** - Browser can access microphone  
✅ **Voice Recording** - Users can speak instead of type  
✅ **Automatic Transcription** - Whisper converts speech to text  
✅ **Voice Previews** - Users hear voices before choosing  
✅ **Server Storage** - Previews don't need API keys  

---

## Next Steps (If Desired)

1. **Add ElevenLabs API Key** (for actual chat voice responses)
   - Get key from: https://elevenlabs.io/app/account
   - Enter in Settings ⚙️
   - Choose voice and adjust settings

2. **Test with Actual Conversation**
   - Record message to Forge
   - Get response
   - Click 🔊 LISTEN to hear in voice

3. **Customize Preview Text** (Optional)
   - Edit `flask_app.py`
   - Change `preview_text` in `generate_voice_previews()`
   - Regenerate previews

---

## File Checklist

After setup, you should have:
```
✅ cert.pem          (Created by generate_cert.py)
✅ key.pem           (Created by generate_cert.py)
✅ frontend/voices/
   ✅ rachel.mp3     (Created by preview generation)
   ✅ bella.mp3      (Created by preview generation)
   ✅ charlotte.mp3  (Created by preview generation)
   ✅ adam.mp3       (Created by preview generation)
   ✅ chris.mp3      (Created by preview generation)
```

---

**Done!** 🎉

Your SDOH Chat now has:
- ✅ Microphone voice recording
- ✅ Real-time transcription
- ✅ Voice previews without API keys
- ✅ Full HTTPS support

Users can now speak to the Forge instead of typing!
