"""
Test script to verify server CORS and authentication are working.
Run this while the server is running.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("Server CORS and Authentication Test")
print("=" * 70)

# Test 1: Health check (no auth required)
print("\n[1] Testing health endpoint...")
try:
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   CORS Headers: {dict(response.headers)}")
    if "Access-Control-Allow-Origin" in response.headers:
        print(f"   [OK] CORS headers present: {response.headers['Access-Control-Allow-Origin']}")
    else:
        print(f"   [ERROR] CORS headers missing!")
except Exception as e:
    print(f"   [ERROR] Error: {e}")

# Test 2: Test CORS endpoint
print("\n[2] Testing CORS test endpoint...")
try:
    response = requests.get(
        f"{BASE_URL}/api/v1/chat/test-cors",
        headers={"Origin": "http://localhost:3000"}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    if "Access-Control-Allow-Origin" in response.headers:
        print(f"   [OK] CORS headers present: {response.headers['Access-Control-Allow-Origin']}")
    else:
        print(f"   [ERROR] CORS headers missing!")
except Exception as e:
    print(f"   [ERROR] Error: {e}")

# Test 3: Test chat stream endpoint (should work in dev mode without token)
print("\n[3] Testing chat stream endpoint (dev mode, no token)...")
try:
    response = requests.post(
        f"{BASE_URL}/api/v1/chat/stream",
        headers={
            "Origin": "http://localhost:3000",
            "Content-Type": "application/json"
        },
        json={
            "message": "test",
            "history": [],
            "active_source_ids": []
        },
        timeout=5  # Short timeout since we expect an error
    )
    print(f"   Status: {response.status_code}")
    if "Access-Control-Allow-Origin" in response.headers:
        print(f"   [OK] CORS headers present: {response.headers['Access-Control-Allow-Origin']}")
    else:
        print(f"   [ERROR] CORS headers missing!")
    print(f"   Response: {response.text[:200]}")
except requests.exceptions.Timeout:
    print("   ⚠ Request timed out (might be streaming)")
except requests.exceptions.RequestException as e:
    print(f"   Error: {type(e).__name__}: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"   Status: {e.response.status_code}")
        if "Access-Control-Allow-Origin" in e.response.headers:
            print(f"   ✓ CORS headers present in error: {e.response.headers['Access-Control-Allow-Origin']}")
        else:
            print(f"   ✗ CORS headers missing in error response!")

print("\n" + "=" * 70)
print("Test complete!")
print("=" * 70)
print("\nIf CORS headers are missing, the server needs to be restarted.")
print("If you see 500 errors, check the server console for details.")
