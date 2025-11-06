#!/usr/bin/env python3
import requests
import json

# Test registration with duplicate phone number
BASE_URL = "http://localhost:8000"

def test_registration():
    print("Testing user registration endpoint...")
    
    # First, create a user with a specific phone number
    user1_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe.test@example.com",
        "user_type": "seller",
        "phone_number": "+251911234567",
        "business_name": "Test Business",
        "business_type": "individual"
    }
    
    print("\n1. Creating first user...")
    response1 = requests.post(f"{BASE_URL}/api/register/", json=user1_data)
    print(f"Status: {response1.status_code}")
    try:
        print(f"Response: {response1.json()}")
    except:
        print(f"Raw response: {response1.text}")
    
    # Now try to create another user with the same phone number
    user2_data = {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith.test@example.com",
        "user_type": "seller",
        "phone_number": "+251911234567",  # Same phone number
        "business_name": "Another Business",
        "business_type": "company"
    }
    
    print("\n2. Creating second user with same phone number...")
    response2 = requests.post(f"{BASE_URL}/api/register/", json=user2_data)
    print(f"Status: {response2.status_code}")
    try:
        print(f"Response: {response2.json()}")
    except:
        print(f"Raw response: {response2.text}")
    
    # Test regular buyer registration with phone number (should also be checked)
    buyer_data = {
        "first_name": "Buyer",
        "last_name": "Test",
        "email": "buyer.test@example.com",
        "user_type": "buyer"
    }
    
    print("\n3. Testing buyer registration...")
    response3 = requests.post(f"{BASE_URL}/api/register/", json=buyer_data)
    print(f"Status: {response3.status_code}")
    try:
        print(f"Response: {response3.json()}")
    except:
        print(f"Raw response: {response3.text}")
    
    # Verify the fix
    if response2.status_code == 400:
        print("\n✅ SUCCESS: Duplicate phone number correctly returns 400 Bad Request")
        return True
    elif response2.status_code == 500:
        print("\n❌ FAILED: Duplicate phone number still returns 500 Internal Server Error")
        return False
    else:
        print(f"\n⚠️  UNEXPECTED: Status code {response2.status_code}")
        return False

if __name__ == "__main__":
    test_registration()