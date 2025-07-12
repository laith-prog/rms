#!/usr/bin/env python
"""
Direct script to create a superuser with hardcoded values.
Run this script directly from the Railway shell.
"""
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rms.settings')
django.setup()

# Import models after Django is set up
from django.contrib.auth import get_user_model
User = get_user_model()

# Hardcoded credentials
PHONE = '0953241659'
EMAIL = 'admin@example.com'
PASSWORD = 'admin123'

# Check if superuser already exists
if User.objects.filter(is_superuser=True).exists():
    print('Superuser already exists')
else:
    # Check if user with this phone already exists
    existing_user = User.objects.filter(phone=PHONE).first()
    if existing_user:
        print(f'User with phone {PHONE} already exists. Upgrading to superuser...')
        existing_user.is_staff = True
        existing_user.is_superuser = True
        existing_user.is_phone_verified = True
        existing_user.set_password(PASSWORD)
        existing_user.save()
        print(f'Existing user upgraded to superuser: {existing_user.phone}')
    else:
        # Create new superuser
        user = User.objects.create_superuser(
            phone=PHONE,
            email=EMAIL,
            password=PASSWORD,
            first_name='Admin',
            last_name='User',
            is_phone_verified=True
        )
        print(f'Superuser created: {user.phone}') 