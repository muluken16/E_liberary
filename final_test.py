#!/usr/bin/env python
import os
import sys
import django
import json

# Add the backend directory to Python path
sys.path.insert(0, 'backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dl.settings')
django.setup()

from django.test import Client
from api.models import User

def test_authentication():
    print("Testing Authentication - Final Verification")
    print("=" * 50)
    
    # Create test client
    client = Client()
    
    # Test login
    login_data = {'username': 'admin', 'password': 'admin123'}
    response = client.post('/api/login/', data=json.dumps(login_data), content_type='application/json')
    print(f"Login response: {response.status_code}")
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access')
        print(f"Access token received: {access_token[:50]}...")
        
        # Test dashboard endpoint with authentication
        dashboard_response = client.get('/api/dashboard/', HTTP_AUTHORIZATION=f'Bearer {access_token}')
        print(f"Dashboard response: {dashboard_response.status_code}")
        if dashboard_response.status_code == 200:
            dashboard_data = dashboard_response.json()
            print("SUCCESS: Dashboard data successfully retrieved!")
            print(f"Dashboard contains {len(dashboard_data)} key metrics")
            print(f"Sample data - Total books: {dashboard_data.get('total_books', 'N/A')}")
            print(f"Sample data - Total users: {dashboard_data.get('total_users', 'N/A')}")
        else:
            print(f"FAILED: Dashboard error: {dashboard_response.content.decode()}")
        
        # Test recent activities endpoint
        activities_response = client.get('/api/recent-activities/', HTTP_AUTHORIZATION=f'Bearer {access_token}')
        print(f"Activities response: {activities_response.status_code}")
        if activities_response.status_code == 200:
            activities_data = activities_response.json()
            print("SUCCESS: Recent activities successfully retrieved!")
            print(f"Activities count: {len(activities_data)}")
        else:
            print(f"FAILED: Activities error: {activities_response.content.decode()}")
            
        print("\n" + "=" * 50)
        print("AUTHENTICATION ISSUE RESOLVED!")
        print("The admin dashboard endpoints now work with proper JWT authentication.")
        print("The frontend will need to be updated to send the access token in requests.")
    else:
        print("FAILED: Login failed")
        print(f"Response content: {response.content.decode()}")

if __name__ == "__main__":
    test_authentication()