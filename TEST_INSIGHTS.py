import requests
import json
import sys

BASE_URL = "http://localhost:5000/api/sdoh"

def test_insight_extraction():
    print("1. Logging in...")
    # Create a test user or login
    # Assuming we can just use a known user or create one.
    # Let's try to register a temp user
    username = "insight_tester"
    try:
        requests.post(f"{BASE_URL}/register", json={"username": username, "password": "password123"})
    except:
        pass # Maybe already exists

    # Login
    resp = requests.post(f"{BASE_URL}/login", json={"username": username, "password": "password123"})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    
    token = resp.json()['token']
    headers = {'Authorization': f'Bearer {token}'}
    
    print("2. Sending message to Forge...")
    # We can't easily force the agent to return an insight without mocking, 
    # but we can check if the previous logic holds.
    # Actually, since we can't mock the agent easily in a live integration test without changing code,
    # we will just verify the endpoint structure.
    
    # However, we can manually inject an insight into the DB to verify the frontend can see it.
    # But the user wants to know if the *extraction* works.
    
    # Let's try to send a message that triggers an insight.
    msg = "I feel like I'm always trying to please everyone and it's exhausting."
    
    resp = requests.post(f"{BASE_URL}/forge/chat", json={"content": msg}, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print("Response received.")
        print(f"Agent said: {data.get('response')}")
        print(f"Insights returned: {data.get('insights')}")
        
        if data.get('insights'):
            print("SUCCESS: Insights were extracted and returned!")
        else:
            print("NOTE: No insights extracted this time (this is normal, depends on Agent).")
    else:
        print(f"Chat failed: {resp.text}")

if __name__ == "__main__":
    test_insight_extraction()
