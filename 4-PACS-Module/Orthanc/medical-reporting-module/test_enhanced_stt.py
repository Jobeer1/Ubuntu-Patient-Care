#!/usr/bin/env python3
"""
Test script for Enhanced Medical STT functionality
Tests training engine, voice shortcuts, and API endpoints
"""

import sys
import os
import requests
import json
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_api_endpoints():
    """Test the enhanced STT API endpoints"""
    base_url = "http://localhost:5000/api/voice"
    
    print("🧪 Testing Enhanced Medical STT API Endpoints")
    print("=" * 50)
    
    # Test 1: Get training categories
    print("\n1. Testing training categories endpoint...")
    try:
        response = requests.get(f"{base_url}/training/categories?user_id=test_user")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                categories = data.get('categories', {})
                print(f"   ✅ Found {len(categories)} training categories")
                for category, terms in categories.items():
                    print(f"      - {category}: {len(terms)} terms")
            else:
                print(f"   ❌ API returned error: {data}")
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
    
    # Test 2: Get training progress
    print("\n2. Testing training progress endpoint...")
    try:
        response = requests.get(f"{base_url}/training/progress?user_id=test_user")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                progress = data.get('progress', {})
                print(f"   ✅ Training progress retrieved")
                print(f"      - Total sessions: {progress.get('total_sessions', 0)}")
                print(f"      - Accuracy improvement: {progress.get('accuracy_improvement', 0):.1%}")
            else:
                print(f"   ❌ API returned error: {data}")
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
    
    # Test 3: Get voice shortcuts
    print("\n3. Testing voice shortcuts endpoint...")
    try:
        response = requests.get(f"{base_url}/shortcuts?user_id=test_user")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                shortcuts = data.get('shortcuts', [])
                print(f"   ✅ Found {len(shortcuts)} voice shortcuts")
                for shortcut in shortcuts[:3]:  # Show first 3
                    print(f"      - {shortcut.get('name')}: used {shortcut.get('usage_count', 0)} times")
            else:
                print(f"   ❌ API returned error: {data}")
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
    
    # Test 4: Start training session
    print("\n4. Testing training session start...")
    try:
        payload = {
            "user_id": "test_user",
            "category": "anatomy"
        }
        response = requests.post(f"{base_url}/training/session/start", 
                               json=payload,
                               headers={'Content-Type': 'application/json'})
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"   ✅ Training session started")
                print(f"      - Session ID: {data.get('session_id')}")
                print(f"      - Category: {data.get('category')}")
                print(f"      - Total terms: {data.get('total_terms')}")
                print(f"      - Current term: {data.get('current_term')}")
            else:
                print(f"   ❌ API returned error: {data}")
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Request failed: {e}")

def test_database_models():
    """Test database models and functionality"""
    print("\n🗄️ Testing Database Models")
    print("=" * 30)
    
    try:
        # Import models
        from models.training_data import TrainingDataStore, MedicalTerm
        from models.voice_shortcuts import VoiceShortcutStore
        from models.database import db
        
        print("   ✅ Models imported successfully")
        
        # Test training data store
        training_store = TrainingDataStore("test_user")
        print("   ✅ TrainingDataStore created")
        
        # Test voice shortcut store
        shortcut_store = VoiceShortcutStore("test_user")
        print("   ✅ VoiceShortcutStore created")
        
        # Test getting user progress (should work even with no data)
        progress = training_store.get_user_training_progress()
        print(f"   ✅ User progress retrieved: {progress['total_sessions']} sessions")
        
        # Test getting user shortcuts
        shortcuts = shortcut_store.get_user_shortcuts()
        print(f"   ✅ User shortcuts retrieved: {len(shortcuts)} shortcuts")
        
    except Exception as e:
        print(f"   ❌ Database model test failed: {e}")
        import traceback
        traceback.print_exc()

def test_training_engine():
    """Test the medical training engine"""
    print("\n🎓 Testing Medical Training Engine")
    print("=" * 35)
    
    try:
        from core.training_engine import MedicalTrainingEngine
        
        # Mock whisper model for testing
        class MockWhisperModel:
            def transcribe(self, audio, language="en"):
                return {"text": "cardiovascular system"}
        
        mock_model = MockWhisperModel()
        engine = MedicalTrainingEngine(mock_model, "test_user")
        
        print("   ✅ MedicalTrainingEngine created")
        
        # Test getting categories
        categories = engine.get_training_categories()
        print(f"   ✅ Categories retrieved: {len(categories)} categories")
        
        # Test getting terms for a category
        anatomy_terms = engine.get_terms_for_category("anatomy")
        print(f"   ✅ Anatomy terms: {len(anatomy_terms)} terms")
        
        # Test recommended terms
        recommended = engine.get_recommended_terms(5)
        print(f"   ✅ Recommended terms: {len(recommended)} terms")
        
    except Exception as e:
        print(f"   ❌ Training engine test failed: {e}")
        import traceback
        traceback.print_exc()

def test_voice_matcher():
    """Test the voice pattern matcher"""
    print("\n🎤 Testing Voice Pattern Matcher")
    print("=" * 35)
    
    try:
        from core.voice_matcher import VoicePatternMatcher
        import numpy as np
        
        matcher = VoicePatternMatcher("test_user")
        print("   ✅ VoicePatternMatcher created")
        
        # Test registering a shortcut with mock audio
        mock_audio = np.random.random(1000).astype(np.float32)
        result = matcher.register_voice_shortcut(
            audio_data=mock_audio,
            shortcut_name="Test Shortcut",
            template_content="This is a test template"
        )
        
        if result.get('success'):
            print("   ✅ Voice shortcut registered successfully")
            shortcut_id = result.get('shortcut_id')
            
            # Test matching against the shortcut
            match_result = matcher.match_voice_command(mock_audio, confidence_threshold=0.1)
            if match_result.get('success'):
                if match_result.get('match_found'):
                    print("   ✅ Voice shortcut matched successfully")
                else:
                    print("   ⚠️ Voice shortcut not matched (expected with random audio)")
            else:
                print(f"   ❌ Voice matching failed: {match_result}")
        else:
            print(f"   ❌ Shortcut registration failed: {result}")
        
    except Exception as e:
        print(f"   ❌ Voice matcher test failed: {e}")
        import traceback
        traceback.print_exc()

def check_server_status():
    """Check if the Flask server is running"""
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Flask server is running")
            return True
        else:
            print(f"❌ Flask server returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Flask server not accessible: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Enhanced Medical STT Test Suite")
    print("=" * 50)
    
    # Check server status first
    server_running = check_server_status()
    
    # Run database and model tests (these don't need the server)
    test_database_models()
    test_training_engine()
    test_voice_matcher()
    
    # Run API tests only if server is running
    if server_running:
        test_api_endpoints()
    else:
        print("\n⚠️ Skipping API tests - Flask server not running")
        print("   Start the server with: python app.py")
    
    print("\n🎉 Test suite completed!")
    print("\n📋 Next steps:")
    print("   1. Start the Flask server: python app.py")
    print("   2. Visit: http://localhost:5000/enhanced-voice-demo")
    print("   3. Test the training and shortcuts functionality")

if __name__ == "__main__":
    main()