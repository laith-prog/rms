from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser if none exists'

    def handle(self, *args, **options):
        if not User.objects.filter(is_superuser=True).exists():
            phone = os.environ.get('DJANGO_SUPERUSER_PHONE', '0953241659')
            email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
            first_name = os.environ.get('DJANGO_SUPERUSER_FIRST_NAME', 'Admin')
            last_name = os.environ.get('DJANGO_SUPERUSER_LAST_NAME', 'User')
            
            self.stdout.write(f'Creating superuser with phone: {phone}')
            
            superuser = User.objects.create_superuser(
                phone=phone,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_phone_verified=True  # Set phone as verified for superuser
            )
            
            self.stdout.write(self.style.SUCCESS(f'Superuser created: {superuser.phone}'))
        else:
            self.stdout.write(self.style.SUCCESS('Superuser already exists')) 