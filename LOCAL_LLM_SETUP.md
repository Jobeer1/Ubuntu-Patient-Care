# Local Micro-Agent Setup (Gemma 2B)

To enable the "Micro Gemma" fallback model when the cloud API is unavailable, follow these steps. This allows the "Forge" agent to run locally on your computer with high-quality reasoning.

## 1. Install Ollama
Ollama is a lightweight tool to run LLMs locally.
1. Download Ollama from [https://ollama.com/download/windows](https://ollama.com/download/windows).
2. Install it.

## 2. Pull the Gemma 2B Model
Open a command prompt (cmd) or PowerShell and run:

```bash
ollama pull gemma:2b
```

This downloads the "Micro Gemma" model (about 1.5GB).

## 3. Verify It's Running
Run this command to test it:
```bash
ollama run gemma:2b "Hello, are you ready to be the Forge?"
```
If it replies, you are ready!

## 4. How It Works
The `agent_forge.py` script has been updated to automatically detect if Ollama is running.
- **Priority 1:** Cloud Gemini API (Best quality)
- **Priority 2:** Local Gemma 2B (Good quality, offline capable)
- **Priority 3:** Rule-Based Logic (Basic fallback if both above fail)

You don't need to change any config files. Just having Ollama running in the background is enough.
