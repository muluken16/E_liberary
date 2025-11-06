#!/usr/bin/env python3
"""
Authentication Debug Helper
This script helps debug authentication issues and reset user sessions
"""

import requests
import json
import time

BASE_URL = 'http://127.0.0.1:8000/api'
LOGIN_ENDPOINT = f'{BASE_URL}/login/'
DASHBOARD_ENDPOINT = f'{BASE_URL}/dashboard/'
CURRENT_USER_ENDPOINT = f'{BASE_URL}/current_user/'

def test_all_admin_accounts():
    """Test all available admin accounts"""
    admin_accounts = [
        ('admin', 'admin123', 'Main Admin'),
        ('mule234', 'mule234', 'Admin User'),  # Note: Using username as password based on pattern
    ]
    
    print("Testing all admin accounts...")
    print("=" * 50)
    
    for username, password, description in admin_accounts:
        print(f"\nTesting {description}: {username}")
        print("-" * 30)
        
        try:
            # Try to login
            response = requests.post(LOGIN_ENDPOINT, json={
                'username': username,
                'password': password
            })
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get('access')
                user_info = data.get('user', {})
                
                print(f"✓ Login successful!")
                print(f"  User: {user_info.get('username')} ({user_info.get('email')})")
                print(f"  Role: {user_info.get('role')} (Superuser: {user_info.get('is_superuser')})")
                
                # Test dashboard access
                headers = {'Authorization': f'Bearer {access_token}'}
                dashboard_response = requests.get(DASHBOARD_ENDPOINT, headers=headers)
                
                if dashboard_response.status_code == 200:
                    print(f"✓ Dashboard access: SUCCESS")
                    print(f"  Response: {dashboard_response.status_code}")
                    break
                elif dashboard_response.status_code == 403:
                    print(f"✗ Dashboard access: FORBIDDEN (not admin)")
                else:
                    print(f"✗ Dashboard access: {dashboard_response.status_code}")
                    
            else:
                print(f"✗ Login failed: {response.status_code}")
                print(f"  Response: {response.text}")
                
        except Exception as e:
            print(f"✗ Error: {str(e)}")
        
        print()
        time.sleep(1)

def check_current_backend_users():
    """Show available users in database"""
    print("Available Users in Database:")
    print("=" * 50)
    
    try:
        response = requests.get(f'{BASE_URL.replace("/api", "")}/admin/api/user/')
        if response.status_code == 401:
            print("Admin panel requires authentication")
            
            # Try to login with admin first
            login_response = requests.post(LOGIN_ENDPOINT, json={
                'username': 'admin',
                'password': 'admin123'
            })
            
            if login_response.status_code == 200:
                data = login_response.json()
                token = data.get('access')
                
                # Now try admin endpoint
                headers = {'Authorization': f'Bearer {token}'}
                admin_response = requests.get(f'{BASE_URL.replace("/api", "")}/admin/api/user/', headers=headers)
                
                if admin_response.status_code == 200:
                    users = admin_response.json()
                    for user in users:
                        print(f"ID: {user.get('id')}, Username: {user.get('username')}, "
                              f"Role: {user.get('role')}, Superuser: {user.get('is_superuser')}")
                else:
                    print(f"Admin endpoint error: {admin_response.status_code}")
            else:
                print("Cannot login to check users")
        else:
            print(f"Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"Error checking users: {str(e)}")

def main():
    """Main debug function"""
    print("Authentication Debug Helper")
    print("=" * 50)
    
    # Test backend connection
    try:
        response = requests.get(f'{BASE_URL}/books/', timeout=5)
        if response.status_code in [200, 401]:
            print("✓ Backend is accessible")
        else:
            print(f"✗ Backend error: {response.status_code}")
            return
    except Exception as e:
        print(f"✗ Cannot connect to backend: {str(e)}")
        return
    
    print()
    
    # Test all admin accounts
    test_all_admin_accounts()
    
    print("\n" + "=" * 50)
    print("USER ACTION REQUIRED:")
    print("1. Clear browser storage (localStorage and sessionStorage)")
    print("2. Login with admin credentials in the frontend")
    print("3. Check if dashboard loads without 401 errors")
    print("4. If still having issues, check browser console for errors")
    
    print("\nTo clear browser storage, open browser console and run:")
    print("localStorage.clear(); sessionStorage.clear();")
    
    # Show backend users
    check_current_backend_users()

if __name__ == '__main__':
    main()