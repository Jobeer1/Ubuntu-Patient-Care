#!/usr/bin/env python
"""Test MCP server routes"""
import requests
import json

# Test GET endpoint
print("Testing GET /api/mcp-server-status...")
response = requests.get('http://localhost:8080/api/mcp-server-status')
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test POST endpoint
print("\nTesting POST /api/mcp-server-start...")
response = requests.post('http://localhost:8080/api/mcp-server-start')
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
