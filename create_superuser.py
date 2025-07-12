#!/usr/bin/env python
"""
Standalone script to create a superuser.
Run this script directly with: python create_superuser.py
"""
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rms.settings')
django.setup()

# Import models after Django is set up
from django.contrib.auth import get_user_model
User = get_user_model()

def create_superuser():
    try:
        # Check if superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            print('Superuser already exists')
            return
        
        # Get credentials from environment or use defaults
        phone = os.environ.get('DJANGO_SUPERUSER_PHONE', '0953241659')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
        first_name = os.environ.get('DJANGO_SUPERUSER_FIRST_NAME', 'Admin')
        last_name = os.environ.get('DJANGO_SUPERUSER_LAST_NAME', 'User')
        
        print(f'Attempting to create superuser with phone: {phone}')
        
        # Check if user with this phone already exists but is not a superuser
        existing_user = User.objects.filter(phone=phone).first()
        if existing_user:
            print(f'User with phone {phone} already exists. Upgrading to superuser...')
            existing_user.is_staff = True
            existing_user.is_superuser = True
            existing_user.is_phone_verified = True
            existing_user.save()
            print(f'Existing user upgraded to superuser: {existing_user.phone}')
            return
        
        # Create new superuser
        superuser = User.objects.create_superuser(
            phone=phone,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_phone_verified=True
        )
        
        print(f'Superuser created successfully: {superuser.phone}')
    
    except Exception as e:
        print(f'Error creating superuser: {str(e)}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    create_superuser() 