#!/usr/bin/env python3
"""
Test script for Medical Training UI functionality
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import create_app
import requests
import json

def test_training_ui():
    """Test the training UI functionality"""
    
    app = create_app()
    
    with app.test_client() as client:
        print("🧪 Testing Medical Training UI Components...")
        
        # Test 1: Get training categories
        print("\n1. Testing training categories endpoint...")
        response = client.get('/api/voice/training/categories?user_id=test_user')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"Categories available: {list(data.get('categories', {}).keys())}")
        else:
            print(f"Error: {response.get_data(as_text=True)}")
        
        # Test 2: Start training session
        print("\n2. Testing training session start...")
        response = client.post('/api/voice/training/session/start', 
                             json={'user_id': 'test_user', 'category': 'anatomy'})
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"Session started: {data.get('success')}")
            print(f"Total terms: {data.get('total_terms')}")
            print(f"Current term: {data.get('current_term', {}).get('term')}")
            session_id = data.get('session_id')
        else:
            print(f"Error: {response.get_data(as_text=True)}")
            session_id = None
        
        # Test 3: Get training progress
        print("\n3. Testing training progress...")
        response = client.get('/api/voice/training/progress?user_id=test_user')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"Progress loaded: {data.get('success')}")
        else:
            print(f"Error: {response.get_data(as_text=True)}")
        
        # Test 4: Get shortcuts list
        print("\n4. Testing shortcuts list...")
        response = client.get('/api/voice/shortcuts/list?user_id=test_user')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"Shortcuts loaded: {data.get('success')}")
            print(f"Number of shortcuts: {len(data.get('shortcuts', []))}")
        else:
            print(f"Error: {response.get_data(as_text=True)}")
        
        # Test 5: Complete session if we have one
        if session_id:
            print(f"\n5. Testing session completion...")
            response = client.post('/api/voice/training/session/complete',
                                 json={'session_id': session_id, 'user_id': 'test_user'})
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"Session completed: {data.get('success')}")
                stats = data.get('stats', {})
                print(f"Session stats: {stats}")
            else:
                print(f"Error: {response.get_data(as_text=True)}")
        
        print("\n✅ Training UI tests completed!")

if __name__ == "__main__":
    test_training_ui()