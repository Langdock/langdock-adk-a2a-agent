#!/usr/bin/env python3
"""
Test script to verify bearer token authentication for the A2A agent.
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:8001"
BEARER_TOKEN = os.getenv("A2A_BEARER_TOKEN", "your-secure-bearer-token-here")


def test_public_endpoint():
    """Test that the public agent card endpoint is accessible without auth."""
    print("\n1. Testing public endpoint (/.well-known/agent.json)...")
    response = requests.get(f"{BASE_URL}/.well-known/agent.json")
    print(f"   Status Code: {response.status_code}")

    if response.status_code == 200:
        print("   ✓ Public endpoint accessible without authentication")
        agent_card = response.json()
        print(f"   Agent: {agent_card.get('name')}")

        # Check if security schemes are present
        if "securitySchemes" in agent_card:
            print(f"   ✓ Security schemes defined: {list(agent_card['securitySchemes'].keys())}")
        if "security" in agent_card:
            print(f"   ✓ Security requirements: {agent_card['security']}")
    else:
        print(f"   ✗ Failed: {response.text}")

    return response.status_code == 200


def test_without_auth():
    """Test that protected endpoints reject requests without authentication."""
    print("\n2. Testing protected endpoint without authentication...")
    response = requests.post(
        f"{BASE_URL}/jsonrpc",
        json={
            "jsonrpc": "2.0",
            "method": "agent.executeTask",
            "params": {"task": "test"},
            "id": 1
        }
    )
    print(f"   Status Code: {response.status_code}")

    if response.status_code == 401:
        print("   ✓ Request rejected without authentication")
        error = response.json()
        print(f"   Error: {error.get('message')}")
        print(f"   WWW-Authenticate header: {response.headers.get('WWW-Authenticate')}")
    else:
        print(f"   ✗ Expected 401, got {response.status_code}")

    return response.status_code == 401


def test_with_invalid_token():
    """Test that protected endpoints reject requests with invalid tokens."""
    print("\n3. Testing protected endpoint with invalid token...")
    response = requests.post(
        f"{BASE_URL}/jsonrpc",
        headers={"Authorization": "Bearer invalid-token-12345"},
        json={
            "jsonrpc": "2.0",
            "method": "agent.executeTask",
            "params": {"task": "test"},
            "id": 1
        }
    )
    print(f"   Status Code: {response.status_code}")

    if response.status_code == 401:
        print("   ✓ Request rejected with invalid token")
        error = response.json()
        print(f"   Error: {error.get('message')}")
    else:
        print(f"   ✗ Expected 401, got {response.status_code}")

    return response.status_code == 401


def test_with_valid_token():
    """Test that protected endpoints accept requests with valid tokens."""
    print("\n4. Testing protected endpoint with valid token...")
    response = requests.post(
        f"{BASE_URL}/jsonrpc",
        headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        json={
            "jsonrpc": "2.0",
            "method": "agent.executeTask",
            "params": {"task": "Hello"},
            "id": 1
        }
    )
    print(f"   Status Code: {response.status_code}")

    if response.status_code in [200, 400, 404]:  # Accept various success/method errors
        print("   ✓ Request authenticated successfully")
        if response.status_code == 200:
            print(f"   Response: {json.dumps(response.json(), indent=2)[:200]}...")
    else:
        print(f"   ✗ Unexpected status code: {response.status_code}")
        print(f"   Response: {response.text[:200]}")

    return response.status_code in [200, 400, 404]


def test_with_malformed_header():
    """Test that requests with malformed Authorization headers are rejected."""
    print("\n5. Testing with malformed Authorization header...")
    response = requests.post(
        f"{BASE_URL}/jsonrpc",
        headers={"Authorization": "InvalidFormat token123"},
        json={
            "jsonrpc": "2.0",
            "method": "agent.executeTask",
            "params": {"task": "test"},
            "id": 1
        }
    )
    print(f"   Status Code: {response.status_code}")

    if response.status_code == 401:
        print("   ✓ Request rejected with malformed header")
        error = response.json()
        print(f"   Error: {error.get('message')}")
    else:
        print(f"   ✗ Expected 401, got {response.status_code}")

    return response.status_code == 401


def main():
    """Run all authentication tests."""
    print("=" * 70)
    print("Bearer Token Authentication Tests for A2A Agent")
    print("=" * 70)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Bearer Token: {BEARER_TOKEN[:10]}..." if len(BEARER_TOKEN) > 10 else BEARER_TOKEN)

    try:
        results = {
            "Public endpoint": test_public_endpoint(),
            "No authentication": test_without_auth(),
            "Invalid token": test_with_invalid_token(),
            "Valid token": test_with_valid_token(),
            "Malformed header": test_with_malformed_header(),
        }

        print("\n" + "=" * 70)
        print("Test Results Summary")
        print("=" * 70)

        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status:8} | {test_name}")

        all_passed = all(results.values())
        print("\n" + "=" * 70)
        if all_passed:
            print("✓ All tests passed! Bearer authentication is working correctly.")
        else:
            print("✗ Some tests failed. Please check the implementation.")
        print("=" * 70)

        return 0 if all_passed else 1

    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to the server.")
        print("   Make sure the A2A agent is running on http://localhost:8001")
        print("   Run: python a2a_rootagent.py")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
