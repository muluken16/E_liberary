#!/usr/bin/env python3
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dl.settings')
django.setup()

from api.models import User
from django.contrib.auth.hashers import make_password

# Create demo user
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

# Show all users
print('All users:')
for user in User.objects.all():
    print(f'  - {user.username} (active: {user.is_active}, role: {user.role})')