from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model, authenticate
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Test login with admin credentials'

    def handle(self, *args, **options):
        # Get credentials from environment or use defaults
        admin_phone = os.environ.get('DJANGO_ADMIN_PHONE', '0953241659')
        admin_password = os.environ.get('DJANGO_ADMIN_PASSWORD', 'admin123')
        
        self.stdout.write(self.style.SUCCESS(f'Testing login with phone: {admin_phone}'))
        
        # Check if user exists
        try:
            user = User.objects.get(phone=admin_phone)
            self.stdout.write(self.style.SUCCESS(f'User exists with phone: {admin_phone}'))
            self.stdout.write(self.style.SUCCESS(f'User details:'))
            self.stdout.write(self.style.SUCCESS(f'- Superuser: {user.is_superuser}'))
            self.stdout.write(self.style.SUCCESS(f'- Staff: {user.is_staff}'))
            self.stdout.write(self.style.SUCCESS(f'- Active: {user.is_active}'))
            
            # Test authentication
            auth_user = authenticate(phone=admin_phone, password=admin_password)
            if auth_user:
                self.stdout.write(self.style.SUCCESS(f'Authentication SUCCESSFUL with phone: {admin_phone}'))
            else:
                self.stdout.write(self.style.ERROR(f'Authentication FAILED with phone: {admin_phone}'))
                
                # Try to fix the password
                self.stdout.write(self.style.WARNING(f'Attempting to reset password...'))
                user.set_password(admin_password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Password has been reset to: {admin_password}'))
                
                # Test authentication again
                auth_user = authenticate(phone=admin_phone, password=admin_password)
                if auth_user:
                    self.stdout.write(self.style.SUCCESS(f'Authentication now SUCCESSFUL with phone: {admin_phone}'))
                else:
                    self.stdout.write(self.style.ERROR(f'Authentication still FAILED after password reset'))
                    
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with phone {admin_phone} does not exist!')) 