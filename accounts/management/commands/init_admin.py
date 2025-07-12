from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os
import sys

User = get_user_model()

class Command(BaseCommand):
    help = 'Initialize admin user'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting admin user creation process...'))
        
        # Check if a superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS('Super user already exists'))
            superusers = User.objects.filter(is_superuser=True)
            for user in superusers:
                self.stdout.write(self.style.SUCCESS(f'Existing superuser: {user.phone}'))
            return

        # Get credentials from environment or use defaults
        admin_phone = os.environ.get('DJANGO_ADMIN_PHONE', '0953241659')
        admin_password = os.environ.get('DJANGO_ADMIN_PASSWORD', 'admin123')
        
        self.stdout.write(self.style.SUCCESS(f'Creating superuser with phone: {admin_phone}'))
        
        try:
            # Check if user with this phone already exists
            if User.objects.filter(phone=admin_phone).exists():
                user = User.objects.get(phone=admin_phone)
                self.stdout.write(self.style.WARNING(f'User with phone {admin_phone} already exists. Updating to superuser...'))
                
                # Update user to superuser
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.set_password(admin_password)
                user.save()
                
                self.stdout.write(self.style.SUCCESS(f'Updated existing user to superuser with phone: {admin_phone}'))
            else:
                # Create new superuser
                superuser = User.objects.create_superuser(
                    phone=admin_phone,
                    password=admin_password,
                    first_name='Admin',
                    last_name='User',
                    email='admin@example.com',
                )
                
                self.stdout.write(self.style.SUCCESS(f'Super user created with phone: {admin_phone}'))
            
            # Verify the user was created
            try:
                user = User.objects.get(phone=admin_phone)
                self.stdout.write(self.style.SUCCESS(f'Verification: User exists with phone: {admin_phone}'))
                self.stdout.write(self.style.SUCCESS(f'Superuser status: {user.is_superuser}'))
                self.stdout.write(self.style.SUCCESS(f'Staff status: {user.is_staff}'))
                self.stdout.write(self.style.SUCCESS(f'Active status: {user.is_active}'))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'ERROR: User with phone {admin_phone} does not exist after creation!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create super user: {str(e)}'))
            # Print more detailed error information
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc())) 