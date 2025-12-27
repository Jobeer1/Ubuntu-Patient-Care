# Voice Preview Feature

## What It Does

The **Voice Preview** button lets users hear a sample of the selected voice **before saving settings**.

This helps users:
- ✅ Choose the right voice personality
- ✅ Hear how stability/clarity settings affect the voice
- ✅ Test different combinations of voice + settings

---

## How to Use

### 1. Open Settings
Click ⚙️ in the top-right corner

### 2. Go to TTS Settings
Scroll down to "TEXT-TO-SPEECH SETTINGS"

### 3. Add API Key (First Time Only)
Paste your ElevenLabs API key (from https://elevenlabs.io/app/account)

### 4. Select a Voice
Choose from:
- Rachel (Warm)
- Bella (Calm)
- Prometheus (Balanced)
- Charlotte (Friendly)
- Adam (Serious)
- Chris (Dynamic)

### 5. Adjust Settings (Optional)
- Stability: How consistent the voice sounds
- Clarity: How clear vs artistic the speech is
- Rate: How fast the voice speaks
- Pitch: How high or low the voice sounds

### 6. Click 🔊 PREVIEW
The button will:
- Show "🔊 LOADING..." while generating
- Show "🔊 PLAYING..." while audio plays
- Return to "🔊 PREVIEW" when done

### 7. Hear the Sample
Audio plays: *"Hello, this is a preview of the selected voice with your current settings."*

### 8. Adjust and Preview Again
Change settings, click PREVIEW again, hear the difference

### 9. Click SAVE CHANGES
When happy with the settings, save them

---

## UI Layout

```
Voice:
┌─────────────────────────────────────┬─────────────┐
│ ▼ Rachel (Warm)                     │ 🔊 PREVIEW  │
└─────────────────────────────────────┴─────────────┘

Stability: 0.5
┌──────────────────────────────────────────────────┐
│ ◄─────●────────────────► [Higher = more consistent]
└──────────────────────────────────────────────────┘

Clarity: 0.75
┌──────────────────────────────────────────────────┐
│ ◄──────────●──────────► [Higher = clearer]
└──────────────────────────────────────────────────┘
```

---

## Button States

| State | Display | Meaning |
|-------|---------|---------|
| Default | 🔊 PREVIEW | Ready to preview |
| Loading | 🔊 LOADING... | Generating audio from ElevenLabs |
| Playing | 🔊 PLAYING... | Audio is playing through speakers |
| Done | 🔊 PREVIEW | Finished, ready to preview again |
| Error | Error message | API key missing or invalid |

---

## Example Workflow

### User wants to find the perfect voice

1. Opens Settings ⚙️
2. Pastes ElevenLabs API key
3. Selects "Rachel" voice
4. Clicks 🔊 PREVIEW
5. Hears: *"Hello, this is a preview of the selected voice with your current settings."* in Rachel's voice
6. Adjusts Stability to 0.8 (more consistent)
7. Clicks 🔊 PREVIEW again
8. Hears Rachel again, but now more consistent
9. Changes to "Charlotte" voice
10. Clicks 🔊 PREVIEW
11. Hears Charlotte's friendly voice
12. Likes Charlotte better, so saves settings
13. Now all agent responses use Charlotte's voice

---

## Technical Details

### Preview Text
```
"Hello, this is a preview of the selected voice with your current settings."
```

This was chosen because:
- ✅ Shows pronunciation of common words
- ✅ Short enough to load quickly
- ✅ Demonstrates clarity and stability settings
- ✅ Lets user judge voice personality

### Settings Used in Preview
The preview uses the EXACT same settings the user has configured:
- ✅ Voice ID (selected in dropdown)
- ✅ Stability (slider value)
- ✅ Clarity (slider value)
- ❌ NOT used: Rate, Pitch (preview uses default)

Why? Because Rate and Pitch are applied at playback time, not generation time.

### API Call
```javascript
POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
Headers:
  Content-Type: application/json
  xi-api-key: {user's API key}

Body:
{
  "text": "Hello, this is a preview...",
  "model_id": "eleven_monolingual_v1",
  "voice_settings": {
    "stability": {stability_slider_value},
    "similarity_boost": {clarity_slider_value}
  }
}
```

---

## Troubleshooting

**Problem: "ElevenLabs API key required to preview voice"**
- Solution: Enter your API key in the text box first

**Problem: "Preview failed: 401"**
- Solution: Your API key is invalid or expired
- Get new one from: https://elevenlabs.io/app/account

**Problem: Audio doesn't play**
- Solution: Check browser speaker/headphone volume
- Solution: Check browser audio permissions
- Solution: Try a different browser

**Problem: Audio sounds wrong**
- Solution: Make sure Stability/Clarity values are set before clicking PREVIEW
- Solution: Try clicking PREVIEW again
- Solution: Try different voice

---

## Costs

✅ **Voice Preview is FREE**
- Uses your ElevenLabs API key
- Each preview counts toward your monthly character limit
- Free tier: 10,000 characters/month
- Preview text: ~70 characters, so ~140 previews per month

---

## Tips

💡 **Try all voices**: Click different voices and hit PREVIEW to hear them all

💡 **Compare settings**: Change stability/clarity, then PREVIEW to hear the difference

💡 **Test before saving**: Make sure you like the voice before clicking SAVE CHANGES

💡 **Different contexts**: Think about how the voice will sound during:
- Greeting messages (warm? professional?)
- Deep questions (calm? engaged?)
- Affirmations (encouraging? confident?)

---

## Browser Compatibility

✅ Chrome/Edge - Full support
✅ Firefox - Full support
✅ Safari - Full support
⚠️ Mobile - Works, but audio may use device speaker

---

**Feature Status**: ✅ Production Ready  
**Added**: December 27, 2025
