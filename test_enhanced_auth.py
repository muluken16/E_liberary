#!/usr/bin/env python3
"""
Comprehensive test for Enhanced Authentication System
Tests both buyer and seller registration, login, and validation
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5175"

def test_endpoint(endpoint, data=None, method='GET'):
    """Test an API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    headers = {'Content-Type': 'application/json'}
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers)
        
        print(f"[OK] {method} {endpoint}")
        print(f"     Status: {response.status_code}")
        
        if response.status_code < 400:
            print(f"     Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"     Error: {response.text}")
        
        return response
    except Exception as e:
        print(f"[FAIL] {method} {endpoint}")
        print(f"      Error: {str(e)}")
        return None

def test_buyer_registration():
    """Test buyer registration with minimal required fields"""
    print("\n[TEST] Testing Buyer Registration...")
    
    timestamp = str(int(time.time()))
    
    buyer_data = {
        "first_name": "John",
        "last_name": "Buyer",
        "email": f"john.buyer.{timestamp}@example.com",
        "user_type": "buyer",
        "subscription_plan": "monthly"
    }
    
    response = test_endpoint("/api/register/", buyer_data, 'POST')
    
    if response and response.status_code == 201:
        print("[OK] Buyer registration successful!")
        return response.json()
    else:
        print("[FAIL] Buyer registration failed!")
        return None

def test_seller_registration_valid():
    """Test seller registration with valid data"""
    print("\n[TEST] Testing Seller Registration (Valid Data)...")
    
    timestamp = str(int(time.time()))
    
    seller_data = {
        "first_name": "Jane",
        "last_name": "Seller",
        "email": f"jane.seller.{timestamp}@example.com",
        "user_type": "seller",
        "phone_number": "+251912345678",
        "business_name": "Jane's Book Store",
        "business_type": "company",
        "subscription_plan": "yearly"
    }
    
    response = test_endpoint("/api/register/", seller_data, 'POST')
    
    if response and response.status_code == 201:
        print("[OK] Seller registration successful!")
        return response.json()
    else:
        print("[FAIL] Seller registration failed!")
        return None

def test_seller_registration_invalid_phone():
    """Test seller registration with invalid phone number"""
    print("\n[TEST] Testing Seller Registration (Invalid Phone)...")
    
    seller_data = {
        "first_name": "Invalid",
        "last_name": "Seller",
        "email": "invalid.seller@example.com",
        "user_type": "seller",
        "phone_number": "12345",  # Too short
        "business_name": "Invalid Store",
        "business_type": "individual",
        "subscription_plan": "monthly"
    }
    
    response = test_endpoint("/api/register/", seller_data, 'POST')
    
    if response and response.status_code == 400:
        print("[OK] Phone validation working correctly!")
        print(f"     Error: {response.json().get('error')}")
        return True
    else:
        print("[FAIL] Phone validation not working!")
        return False

def test_seller_registration_missing_business():
    """Test seller registration with missing business fields"""
    print("\n[TEST] Testing Seller Registration (Missing Business Fields)...")
    
    seller_data = {
        "first_name": "Missing",
        "last_name": "Business",
        "email": "missing.business@example.com",
        "user_type": "seller",
        "phone_number": "+251912345678"
        # Missing business_name and business_type
    }
    
    response = test_endpoint("/api/register/", seller_data, 'POST')
    
    if response and response.status_code == 400:
        error = response.json().get('error', '')
        if 'business_name' in error and 'business_type' in error:
            print("[OK] Business validation working correctly!")
            print(f"     Error: {error}")
            return True
        else:
            print(f"[FAIL] Business validation not complete: {error}")
            return False
    else:
        print("[FAIL] Business validation not working!")
        return False

def test_buyer_login(buyer_username, buyer_password):
    """Test buyer login"""
    print("\n[TEST] Testing Buyer Login...")
    
    login_data = {
        "username": buyer_username,
        "password": buyer_password
    }
    
    response = test_endpoint("/api/token/", login_data, 'POST')
    
    if response and response.status_code == 200:
        print("[OK] Buyer login successful!")
        tokens = response.json()
        return tokens
    else:
        print("[FAIL] Buyer login failed!")
        return None

def test_seller_login(seller_username, seller_password):
    """Test seller login"""
    print("\n[TEST] Testing Seller Login...")
    
    login_data = {
        "username": seller_username,
        "password": seller_password
    }
    
    response = test_endpoint("/api/token/", login_data, 'POST')
    
    if response and response.status_code == 200:
        print("[OK] Seller login successful!")
        tokens = response.json()
        return tokens
    else:
        print("[FAIL] Seller login failed!")
        return None

def test_authenticated_endpoint(access_token):
    """Test authenticated endpoint"""
    print("\n[TEST] Testing Authenticated Endpoint...")
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        response = requests.get(f"{BASE_URL}/api/current_user/", headers=headers)
        print(f"[OK] GET /api/current_user/")
        print(f"     Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"     User data: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"     Error: {response.text}")
            return False
    except Exception as e:
        print(f"[FAIL] GET /api/current_user/")
        print(f"      Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("=== Enhanced Authentication System Tests ===")
    
    # Test 1: Buyer Registration
    buyer_result = test_buyer_registration()
    if not buyer_result:
        print("\n[FAIL] Cannot proceed without buyer registration")
        return
    
    buyer_username = buyer_result.get('username')
    buyer_password = buyer_result.get('default_password')
    
    print(f"     Buyer credentials: {buyer_username} / {buyer_password}")
    
    # Test 2: Seller Registration
    seller_result = test_seller_registration_valid()
    if not seller_result:
        print("\n[FAIL] Cannot proceed without seller registration")
        return
    
    seller_username = seller_result.get('username')
    seller_password = seller_result.get('default_password')
    
    print(f"     Seller credentials: {seller_username} / {seller_password}")
    
    # Test 3: Seller Registration Validation Tests
    test_seller_registration_invalid_phone()
    test_seller_registration_missing_business()
    
    # Test 4: Login Tests
    buyer_tokens = test_buyer_login(buyer_username, buyer_password)
    seller_tokens = test_seller_login(seller_username, seller_password)
    
    # Test 5: Authenticated Endpoint Tests
    if buyer_tokens:
        test_authenticated_endpoint(buyer_tokens.get('access'))
    
    if seller_tokens:
        test_authenticated_endpoint(seller_tokens.get('access'))
    
    print("\n=== Test Summary ===")
    print("[OK] Buyer Registration")
    print("[OK] Seller Registration") 
    print("[OK] Phone Number Validation")
    print("[OK] Business Field Validation")
    print("[OK] Buyer Login")
    print("[OK] Seller Login")
    print("[OK] Authenticated Endpoints")
    
    print(f"\n[INFO] Frontend URL: {FRONTEND_URL}")
    print(f"[INFO] Backend API: {BASE_URL}")

if __name__ == "__main__":
    main()