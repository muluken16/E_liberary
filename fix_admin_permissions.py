#!/usr/bin/env python3
import os
import sys
import django

# Add the backend directory to Python path so we can import Django modules
sys.path.insert(0, 'backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dl.settings')

try:
    django.setup()
    from api.models import User
    
    print("=== Checking User Permissions ===")
    
    # Check admin user
    try:
        admin_user = User.objects.get(username='admin')
        print(f"\nAdmin User Found:")
        print(f"  Username: {admin_user.username}")
        print(f"  Email: {admin_user.email}")
        print(f"  Is active: {admin_user.is_active}")
        print(f"  Is superuser: {admin_user.is_superuser}")
        print(f"  Role: {getattr(admin_user, 'role', 'NOT_SET')}")
        
        # Fix admin permissions if needed
        if not admin_user.is_superuser:
            admin_user.is_superuser = True
            print("  ⚠️  Fixed: Made user superuser")
        
        if not admin_user.role == 'Admin':
            admin_user.role = 'Admin'
            print("  ⚠️  Fixed: Set role to 'Admin'")
            
        if not admin_user.is_active:
            admin_user.is_active = True
            print("  ⚠️  Fixed: Activated user")
            
        admin_user.save()
        
    except User.DoesNotExist:
        print("❌ Admin user not found!")
        
    # Create demo user if missing
    try:
        demo_user = User.objects.get(username='demo')
        print(f"\nDemo User Found:")
        print(f"  Username: {demo_user.username}")
        print(f"  Role: {getattr(demo_user, 'role', 'NOT_SET')}")
    except User.DoesNotExist:
        from django.contrib.auth.hashers import make_password
        demo_user = User.objects.create(
            username='demo',
            email='demo@example.com',
            password=make_password('demo123'),
            first_name='Demo',
            last_name='User',
            role='Student',
            is_active=True
        )
        print(f"\n✅ Created Demo User:")
        print(f"  Username: demo")
        print(f"  Password: demo123")
        print(f"  Role: Student")
        
    # List all users
    print(f"\n=== All Users ===")
    for user in User.objects.all():
        print(f"  - {user.username} (active: {user.is_active}, superuser: {user.is_superuser}, role: {getattr(user, 'role', 'NOT_SET')})")
        
    print(f"\n=== Summary ===")
    print(f"✅ Admin login should now work with: admin / admin123")
    print(f"✅ Demo login should now work with: demo / demo123")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()