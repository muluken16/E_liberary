#!/usr/bin/env python3
"""
Test script to verify the login endpoint and create demo users
"""
import requests
import json
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, 'backend')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dl.settings')
import django
django.setup()

from api.models import User
from django.contrib.auth.hashers import make_password

def create_demo_users():
    """Create demo users for testing"""
    try:
        # Create demo user if it doesn't exist
        try:
            demo_user = User.objects.get(username='demo')
            print('Demo user already exists')
        except User.DoesNotExist:
            demo_user = User.objects.create(
                username='demo',
                email='demo@example.com',
                password=make_password('demo123'),
                first_name='Demo',
                last_name='User',
                role='Student',
                is_active=True
            )
            print('Created demo user')

        # Update admin password
        admin_user = User.objects.get(username='admin')
        admin_user.set_password('admin123')
        admin_user.save()
        print('Updated admin password')

        print('All users:')
        for user in User.objects.all():
            print(f'- {user.username} (active: {user.is_active}, role: {user.role})')
            
    except Exception as e:
        print(f"Error creating users: {e}")

def test_login_endpoint():
    """Test the login endpoint"""
    url = "http://127.0.0.1:8000/api/login/"
    headers = {"Content-Type": "application/json"}
    
    # Test with admin credentials
    data = {"username": "admin", "password": "admin123"}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    print("Creating demo users...")
    create_demo_users()
    print("\nTesting login endpoint...")
    test_login_endpoint()