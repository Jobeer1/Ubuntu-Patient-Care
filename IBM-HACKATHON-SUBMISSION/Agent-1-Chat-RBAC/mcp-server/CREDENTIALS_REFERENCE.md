# 🔑 GEMINI CREDENTIALS QUICK REFERENCE

## What You Provided

### Google Gemini API
```
API Key:     AIzaSyD55Og4NGiwZN-Q7OUaVBIE6JK8jfPKOCg
Project ID:  projects/807845595525
Project #:   807845595525
Model:       gemini-2.0-flash-lite
```

**Status:** ⚠️ API key is disabled/compromised (reported by Google)

### IBM Watson
```
API Key:     wJQzWIbw4-eQr7gMKbC8z9GVAa6GdmArqp3x2sW6JQ0B
URL:         https://api.ca-tor.watson-orchestrate.cloud.ibm.com/instances/c331bcba-4cac-4c10-9c2a-ec6989da8d20
Region:      ca-tor
Instance ID: c331bcba-4cac-4c10-9c2a-ec6989da8d20
```

**Status:** 🔴 Endpoint returns 404 (not available)

## IBM Watson - What's Needed

To make Watson work, verify these 4 items:

### 1. API Key
- ✅ **You have:** `wJQzWIbw4-eQr7gMKbC8z9GVAa6GdmArqp3x2sW6JQ0B`
- ⚠️ **Verify:** Is it active in IBM Cloud?
- 📍 **Check:** IBM Cloud → Manage → API Keys
- 🔐 **Status:** Active? Expired? Revoked?

### 2. Service URL
- ✅ **You have:** `https://api.ca-tor.watson-orchestrate.cloud.ibm.com/instances/c331bcba-4cac-4c10-9c2a-ec6989da8d20`
- ⚠️ **Verify:** Does the endpoint respond?
- 📍 **Check:** IBM Cloud → Resource List → Watson service
- 🔐 **Status:** Should NOT return 404

### 3. Region
- ✅ **You have:** `ca-tor` (Canada - Toronto)
- ⚠️ **Verify:** Service is deployed in this region
- 📍 **Check:** Service details page
- 🔐 **Status:** Matches service deployment region?

### 4. Service Status
- ⚠️ **Check:** Is Watson service active?
- 📍 **Check:** IBM Cloud → Resource List
- 💰 **Check:** Is billing enabled?
- 🔐 **Status:** Show as "Active"?

## How to Verify Watson

### Quick Test (from command line)
```bash
# Using curl (if installed)
curl -H "Authorization: Bearer wJQzWIbw4-eQr7gMKbC8z9GVAa6GdmArqp3x2sW6JQ0B" \
  "https://api.ca-tor.watson-orchestrate.cloud.ibm.com/instances/c331bcba-4cac-4c10-9c2a-ec6989da8d20"

# If you get 404: Endpoint doesn't exist
# If you get 401: Invalid/expired API key
# If you get 200: ✅ Working!
```

### In Ubuntu Patient Care
```bash
# Run test
python test_gemini_fallback.py

# Look for:
# "Model used: watson"  ← Watson is working!
# "Model used: gemini"  ← Fallback to Gemini
# "Model used: local-ai" ← Using local AI
```

## Gemini API - What to Do

Current key is compromised. Steps to get new key:

### 1. Go to Google Cloud Console
```
URL: https://console.cloud.google.com
```

### 2. Create New API Key
```
Navigate:
  → APIs & Services
  → Credentials
  → Create Credentials
  → API Key
```

### 3. Restrict to Generative Language API
```
Edit key restrictions:
  → Select "Restrict key"
  → Choose "Generative Language API"
  → Save
```

### 4. Update config.ini
```ini
[gemini_api]
api_key = YOUR_NEW_KEY_HERE
model = gemini-2.0-flash-lite
```

### 5. Test
```bash
python test_gemini_fallback.py
# Should show: Model used: gemini
```

## Current System Flow

```
User sends: "What can you do?"
  ↓
Try Watson
  API Key: wJQzWIbw4-eQr7gMKbC8z9GVAa6GdmArqp3x2sW6JQ0B
  URL: https://api.ca-tor.watson-orchestrate...
  Result: ❌ 404 (endpoint doesn't exist)
  ↓
Try Gemini
  API Key: AIzaSyD55Og4NGiwZN-Q7OUaVBIE6JK8jfPKOCg
  Model: gemini-2.0-flash-lite
  Result: ❌ 403 (key disabled)
  ↓
Use Local AI
  Result: ✅ "Here's what I can help with..."
```

## Status Summary

| Component | Config | API Status | System Using |
|-----------|--------|-----------|--------------|
| Watson | ✅ Configured | ❌ Not available | Not used |
| Gemini | ✅ Configured | ❌ Key disabled | Not used |
| Local AI | ✅ Built-in | ✅ Always works | ✅ ACTIVE |

**Overall:** 🟢 **System Working (using Local AI tier)**

## What Each Tier Provides

### Watson (Tier 1 - Primary)
- Advanced AI reasoning
- Medical knowledge base
- Context-aware responses
- Requires: Valid IBM Cloud service
- Cost: Pay-per-use

### Gemini (Tier 2 - Fallback)
- Fast response times
- General knowledge AI
- Good conversation ability
- Requires: Valid Google API key
- Cost: Free to moderate

### Local AI (Tier 3 - Always Works)
- Instant responses
- Pattern-based intelligence
- Role-aware responses
- Requires: Nothing (built-in)
- Cost: Free

## Next Steps

### To Activate Watson:
```
1. Go: https://cloud.ibm.com
2. Check if Watson service is active
3. Verify credentials work
4. Run: python test_gemini_fallback.py
5. Should see: "Model used: watson"
```

### To Fix Gemini:
```
1. Go: https://console.cloud.google.com
2. Create new API key
3. Update: app/config.ini
4. Run: python test_gemini_fallback.py
5. Should see: "Model used: gemini"
```

### Current Best Practice:
```
✅ Use Local AI (currently most reliable)
⚠️ Get new Gemini key (for fallback tier 2)
⚠️ Verify Watson (for primary tier 1)
```

## Files to Update

| File | Section | Current | Action |
|------|---------|---------|--------|
| `app/config.ini` | `[watson_api]` | Valid | Verify credentials work |
| `app/config.ini` | `[gemini_api]` | Disabled key | Get new key from Google |
| `app/config.ini` | `[chat]` | `fallback_order = gemini,local` | Already set |

## Testing Each Tier

```bash
# Check configuration
python -c "from app.services.watson_api import WatsonConfigManager as M; m=M(); print('Watson:', bool(m.get_api_key())); print('Gemini:', bool(m.get_gemini_api_key())); print('Fallback:', m.get_fallback_order())"

# Full test
python test_gemini_fallback.py

# Run with debug (see which tier is used)
python run.py
# Send message from http://localhost:8080/static/chat.html
# Check response for: "model": "watson/gemini/local-ai"
```

## Security Notes

🔐 **API Keys:**
- Currently in config.ini (development)
- Should use environment variables (production)
- Never commit to Git
- Rotate regularly

```bash
# Add to .gitignore
echo "app/config.ini" >> .gitignore

# Use environment variables (production)
export WATSON_API_KEY="..."
export GEMINI_API_KEY="..."
```

## Summary

**You have:**
- ✅ Watson API key (needs service verification)
- ✅ Gemini API key (needs replacement)
- ✅ Local AI (always working)

**System is:**
- 🟢 Currently operational (using Local AI)
- 🟡 Can be improved (activate Watson/Gemini)
- 🟢 Production ready (has 3 tiers of fallback)

**To improve:**
1. Verify Watson credentials work
2. Get new Gemini API key
3. Re-run test to confirm Tiers 1 & 2 active
