#!/usr/bin/env python3
"""
Test Voice Shortcuts Management Interface
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.app_factory import create_app
import tempfile
import json

def test_shortcuts_ui():
    """Test the voice shortcuts management interface"""
    
    app = create_app()
    
    with app.app_context():
        
        print("🧪 Testing Voice Shortcuts Management Interface")
        
        # Test 1: Check if shortcuts list endpoint works
        with app.test_client() as client:
            print("\n1. Testing shortcuts list endpoint...")
            response = client.get('/api/voice/shortcuts/list?user_id=test_user')
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Response: {data}")
                print("   ✅ Shortcuts list endpoint working")
            else:
                print(f"   ❌ Shortcuts list endpoint failed: {response.data}")
        
        # Test 2: Create a test shortcut
        print("\n2. Testing shortcut creation...")
        
        # Create a dummy audio file for testing
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            # Write minimal WAV header for testing
            wav_header = b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
            temp_audio.write(wav_header)
            temp_audio_path = temp_audio.name
        
        try:
            with app.test_client() as client:
                with open(temp_audio_path, 'rb') as audio_file:
                    response = client.post('/api/voice/shortcuts/create', 
                        data={
                            'user_id': 'test_user',
                            'shortcut_name': 'Test Chest X-ray',
                            'template_id': 'chest-xray',
                            'audio': (audio_file, 'test_shortcut.wav')
                        },
                        content_type='multipart/form-data'
                    )
                
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.get_json()
                    print(f"   Response: {data}")
                    if data.get('success'):
                        print("   ✅ Shortcut creation working")
                        shortcut_id = data.get('shortcut_id')
                        
                        # Test 3: List shortcuts again to see the new one
                        print("\n3. Testing shortcuts list with new shortcut...")
                        response = client.get('/api/voice/shortcuts/list?user_id=test_user')
                        if response.status_code == 200:
                            data = response.get_json()
                            shortcuts = data.get('shortcuts', [])
                            print(f"   Found {len(shortcuts)} shortcuts")
                            if shortcuts:
                                print(f"   First shortcut: {shortcuts[0]}")
                                print("   ✅ Shortcuts listing with data working")
                            
                            # Test 4: Update shortcut
                            if shortcut_id:
                                print(f"\n4. Testing shortcut update (ID: {shortcut_id})...")
                                response = client.put(f'/api/voice/shortcuts/{shortcut_id}',
                                    json={
                                        'user_id': 'test_user',
                                        'name': 'Updated Test Shortcut',
                                        'template_id': 'consultation'
                                    }
                                )
                                print(f"   Status: {response.status_code}")
                                if response.status_code == 200:
                                    print("   ✅ Shortcut update working")
                                
                                # Test 5: Delete shortcut
                                print(f"\n5. Testing shortcut deletion (ID: {shortcut_id})...")
                                response = client.delete(f'/api/voice/shortcuts/{shortcut_id}?user_id=test_user')
                                print(f"   Status: {response.status_code}")
                                if response.status_code == 200:
                                    print("   ✅ Shortcut deletion working")
                        
                    else:
                        print(f"   ❌ Shortcut creation failed: {data}")
                else:
                    print(f"   ❌ Shortcut creation failed: {response.data}")
        
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_audio_path)
            except:
                pass
        
        print("\n🎯 Voice Shortcuts Management Interface Test Complete!")
        print("\nTo test the UI:")
        print("1. Start the app: python app.py")
        print("2. Open: http://localhost:5000/enhanced-voice-demo")
        print("3. Click the 'Shortcuts' tab")
        print("4. Try creating, testing, and managing shortcuts")

if __name__ == "__main__":
    test_shortcuts_ui()