# TTS Settings - How to Use

## Quick Start (3 minutes)

### 1. Get Your ElevenLabs API Key
- Go to https://elevenlabs.io/app/account
- Scroll down to "API Key"
- Click "Copy" to copy your API key

### 2. Add API Key to Settings
- Click **⚙️ Settings** button (bottom right)
- Find **"TEXT-TO-SPEECH SETTINGS (ElevenLabs):"**
- Paste your API key in the **"ElevenLabs API Key:"** field
- Click **"SAVE CHANGES"** button

### 3. Test a Voice
- After saving, find the **"Voice:"** dropdown
- Select a voice (e.g., "Rachel (Warm)")
- Click **"🔊 PREVIEW"** button
- You should hear a sample of the voice

### 4. Customize Voice Settings
Adjust these sliders before saving:
- **Stability**: Lower = more variation, Higher = more consistent
- **Clarity**: Lower = more artistic, Higher = clearer speech
- **Speaking Rate**: 0.5x to 2x speed
- **Pitch**: -20 to +20 semitones (adjust tone)

## How It Works

### When You Click "🔊 PREVIEW"
```
1. App checks if server has pre-stored preview files
   (Free, instant, no API calls)
   ↓
2. If not available, uses YOUR ElevenLabs API key
   (Costs ~0.01 credit per preview)
   ↓
3. Plays the audio so you can hear the voice
```

### When You Send a Message with TTS
The app:
1. Gets your settings from localStorage
2. Uses your ElevenLabs API key
3. Sends text to ElevenLabs API
4. Receives audio response
5. Plays it in the chat

## Voice IDs Available

| Voice | Personality | ID |
|-------|------------|-----|
| Rachel | Warm, engaging | 21m00Tcm4TlvDq8ikWAM |
| Bella | Calm, peaceful | EXAVITQu4vr4xnSDxMaL |
| Charlotte | Friendly, approachable | LZpK5UVVF2fYTu67umBV |
| Adam | Serious, professional | pNInz6obpgDQGcFmaJgB |
| Chris | Dynamic, energetic | iP95p4xoKVk53GoZ5RcFm |

## Troubleshooting

### "Preview failed: API key not set"
→ You haven't entered your ElevenLabs API key yet  
→ Get it from https://elevenlabs.io/app/account  
→ Click SAVE CHANGES after entering it

### "Preview failed: ElevenLabs API error: 401"
→ Your API key is incorrect or expired  
→ Check you copied it correctly from https://elevenlabs.io/app/account  
→ Try generating a new API key

### "Preview failed: ElevenLabs API error: 429"
→ You've hit the rate limit (too many requests)  
→ Wait a few seconds and try again

### "Preview failed: ElevenLabs API error: 500"
→ ElevenLabs service is having issues  
→ Try again in a few moments

## Free Credits

ElevenLabs gives you:
- **10,000 free characters/month** on the free tier
- Each preview = ~25 characters = ~0.001 credit
- Each full response = costs more

**Tip**: Use the preview feature first to test voices, then decide which one you like.

## Settings Saved Where?

✅ **ElevenLabs API Key**: Saved in browser localStorage (local only)  
✅ **Voice Choice**: Saved in browser localStorage  
✅ **Stability/Clarity/Rate/Pitch**: Saved in browser localStorage  

All TTS settings are **private to your browser** - not sent to server

## Privacy & Security

✅ Your API key is stored **locally in your browser**  
✅ Never sent to our server  
✅ Only sent to ElevenLabs API for voice generation  
✅ You can delete it anytime by clearing localStorage

## Cost Calculation

| Activity | Cost |
|----------|------|
| Preview voice | ~0.001 credits |
| 1 minute of audio | ~150 credits |
| ElevenLabs free tier | 10,000 characters/month |
| ElevenLabs paid tier | Starts at $5/month |

**Note**: Previews are very cheap; main costs come from TTS for actual messages.
