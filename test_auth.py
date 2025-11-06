#!/usr/bin/env python
import requests
import json

def test_authentication():
    print("Testing Authentication...")
    
    # Test login
    login_data = {'username': 'admin', 'password': 'admin123'}
    try:
        response = requests.post('http://localhost:8000/api/login/', json=login_data, timeout=10)
        print(f"Login response: {response.status_code}")
        print(f"Response text: {response.text}")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access')
            print(f"Access token received: {access_token[:50] + '...' if access_token else 'None'}")
            
            # Test dashboard endpoint
            headers = {'Authorization': f'Bearer {access_token}'}
            dashboard_response = requests.get('http://localhost:8000/api/dashboard/', headers=headers, timeout=10)
            print(f"Dashboard response: {dashboard_response.status_code}")
            if dashboard_response.status_code == 200:
                print(f"Dashboard data: {dashboard_response.json()}")
            
            # Test recent activities endpoint
            activities_response = requests.get('http://localhost:8000/api/recent-activities/', headers=headers, timeout=10)
            print(f"Activities response: {activities_response.status_code}")
            if activities_response.status_code == 200:
                print(f"Activities data: {activities_response.json()}")
        else:
            print("Login failed")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_authentication()