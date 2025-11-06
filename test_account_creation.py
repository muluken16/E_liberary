#!/usr/bin/env python3
"""
Test script to verify account creation fixes for both buyer and seller accounts
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8001/api"

def test_buyer_account_creation():
    """Test buyer account creation with optional phone number"""
    print("Testing BUYER account creation...")
    
    buyer_data = {
        "first_name": "John",
        "last_name": "Doe", 
        "email": "john.buyer@example.com",
        "username": "johnbuyer",
        "password": "SecurePass123",
        "user_type": "buyer",
        "phone_number": "912345678",  # Optional phone number
        "subscription_plan": "monthly"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/register/", json=buyer_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            print("✅ Buyer account creation SUCCESSFUL")
            return True
        else:
            print("❌ Buyer account creation FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Error testing buyer account: {e}")
        return False

def test_buyer_account_creation_no_phone():
    """Test buyer account creation without phone number"""
    print("\nTesting BUYER account creation WITHOUT phone number...")
    
    buyer_data = {
        "first_name": "Jane",
        "last_name": "Smith", 
        "email": "jane.buyer@example.com",
        "username": "janebuyer",
        "password": "SecurePass123",
        "user_type": "buyer",
        "subscription_plan": "monthly"
        # No phone_number field
    }
    
    try:
        response = requests.post(f"{BASE_URL}/register/", json=buyer_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            print("✅ Buyer account creation (no phone) SUCCESSFUL")
            return True
        else:
            print("❌ Buyer account creation (no phone) FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Error testing buyer account (no phone): {e}")
        return False

def test_seller_account_creation():
    """Test seller account creation with required phone number"""
    print("\nTesting SELLER account creation...")
    
    seller_data = {
        "first_name": "Bob",
        "last_name": "Johnson", 
        "email": "bob.seller@example.com",
        "username": "bobseller",
        "password": "SecurePass123",
        "user_type": "seller",
        "phone_number": "912345678",  # Required for sellers
        "business_name": "Bob's Book Store",
        "business_type": "bookstore",
        "address": "123 Main Street, Addis Ababa",
        "subscription_plan": "yearly"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/register/", json=seller_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            print("✅ Seller account creation SUCCESSFUL")
            return True
        else:
            print("❌ Seller account creation FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Error testing seller account: {e}")
        return False

def test_seller_account_creation_no_phone():
    """Test seller account creation without phone number (should fail)"""
    print("\nTesting SELLER account creation WITHOUT phone number (should fail)...")
    
    seller_data = {
        "first_name": "Alice",
        "last_name": "Brown", 
        "email": "alice.seller@example.com",
        "username": "aliceseller",
        "password": "SecurePass123",
        "user_type": "seller",
        "business_name": "Alice's Books",
        "business_type": "individual",
        "address": "456 Oak Street, Addis Ababa",
        "subscription_plan": "monthly"
        # No phone_number field - should fail
    }
    
    try:
        response = requests.post(f"{BASE_URL}/register/", json=seller_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 400:
            print("✅ Seller account creation correctly REJECTED (no phone)")
            return True
        else:
            print("❌ Seller account creation should have failed but didn't")
            return False
            
    except Exception as e:
        print(f"❌ Error testing seller account (no phone): {e}")
        return False

def main():
    """Run all tests"""
    print("=== ACCOUNT CREATION TEST SUITE ===\n")
    
    tests = [
        test_buyer_account_creation,
        test_buyer_account_creation_no_phone,
        test_seller_account_creation,
        test_seller_account_creation_no_phone
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n=== TEST RESULTS ===")
    print(f"Tests Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 ALL TESTS PASSED! Account creation is working correctly.")
    else:
        print("❌ Some tests failed. Check the issues above.")

if __name__ == "__main__":
    main()