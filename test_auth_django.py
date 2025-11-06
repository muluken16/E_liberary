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
    print("Testing Authentication with Django Test Client...")
    
    # Create test client
    client = Client()
    
    # Test login
    login_data = {'username': 'admin', 'password': 'admin123'}
    response = client.post('/api/login/', data=json.dumps(login_data), content_type='application/json')
    print(f"Login response: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access')
        print(f"Access token received: {access_token[:50] + '...' if access_token else 'None'}")
        
        # Test dashboard endpoint with authentication
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        dashboard_response = client.get('/api/dashboard/')
        print(f"Dashboard response: {dashboard_response.status_code}")
        if dashboard_response.status_code == 200:
            print(f"Dashboard data: {dashboard_response.json()}")
        else:
            print(f"Dashboard error: {dashboard_response.content.decode()}")
        
        # Test recent activities endpoint
        activities_response = client.get('/api/recent-activities/')
        print(f"Activities response: {activities_response.status_code}")
        if activities_response.status_code == 200:
            print(f"Activities data: {activities_response.json()}")
        else:
            print(f"Activities error: {activities_response.content.decode()}")
    else:
        print("Login failed")
        
    # Check if user exists and is properly configured
    try:
        admin_user = User.objects.get(username='admin')
        print(f"Admin user found: {admin_user.username}")
        print(f"  - Role: {admin_user.role}")
        print(f"  - Is superuser: {admin_user.is_superuser}")
        print(f"  - Is active: {admin_user.is_active}")
        print(f"  - Has password: {admin_user.has_usable_password()}")
    except User.DoesNotExist:
        print("Admin user not found!")

if __name__ == "__main__":
    test_authentication()