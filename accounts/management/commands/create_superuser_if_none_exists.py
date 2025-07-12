from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
import os
import sys
import traceback

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser if none exists'

    def handle(self, *args, **options):
        try:
            # Check if superuser already exists
            if User.objects.filter(is_superuser=True).exists():
                self.stdout.write(self.style.SUCCESS('Superuser already exists'))
                return
            
            # Get credentials from environment variables
            phone = os.environ.get('DJANGO_SUPERUSER_PHONE', '0953241659')
            email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
            first_name = os.environ.get('DJANGO_SUPERUSER_FIRST_NAME', 'Admin')
            last_name = os.environ.get('DJANGO_SUPERUSER_LAST_NAME', 'User')
            
            self.stdout.write(f'Attempting to create superuser with phone: {phone}')
            
            # Check if user with this phone already exists but is not a superuser
            existing_user = User.objects.filter(phone=phone).first()
            if existing_user:
                self.stdout.write(f'User with phone {phone} already exists. Upgrading to superuser...')
                existing_user.is_staff = True
                existing_user.is_superuser = True
                existing_user.is_phone_verified = True
                existing_user.save()
                self.stdout.write(self.style.SUCCESS(f'Existing user upgraded to superuser: {existing_user.phone}'))
                return
            
            # Create new superuser
            superuser = User.objects.create_superuser(
                phone=phone,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_phone_verified=True  # Set phone as verified for superuser
            )
            
            self.stdout.write(self.style.SUCCESS(f'Superuser created successfully: {superuser.phone}'))
        
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error creating superuser: {str(e)}'))
            self.stderr.write(self.style.ERROR(traceback.format_exc()))
            # Don't fail the deployment because of superuser creation issues
            # But make it clear in the logs what happened
            self.stderr.write(self.style.WARNING('Continuing deployment despite superuser creation failure')) 