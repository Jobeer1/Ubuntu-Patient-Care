#!/usr/bin/env python3
"""Test Gemini API connectivity"""
import configparser
import google.generativeai as genai

config = configparser.ConfigParser()
config.read('config.ini')
api_key = config.get('GEMINI', 'api_key', fallback=None)
model = config.get('GEMINI', 'model', fallback='gemini-2.5-flash-lite')

if not api_key:
    print("[ERROR] No API key found in config.ini")
    exit(1)

print(f"[*] API Key: {api_key[:20]}...")
print(f"[*] Model: {model}")

try:
    genai.configure(api_key=api_key)
    test_model = genai.GenerativeModel(model)
    response = test_model.generate_content("Say 'Hello from Gemini'")
    print(f"[OK] Gemini API works!")
    print(f"Response: {response.text[:100]}")
except Exception as e:
    print(f"[ERROR] Gemini API failed: {e}")
    exit(1)
