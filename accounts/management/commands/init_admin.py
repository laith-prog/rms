from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Initialize admin user'

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS('Super user already exists'))
            return

        admin_phone = os.environ.get('DJANGO_ADMIN_PHONE', '0953241659')
        admin_password = os.environ.get('DJANGO_ADMIN_PASSWORD', 'admin123')
        
        try:
            superuser = User.objects.create_superuser(
                phone=admin_phone,
                password=admin_password,
                first_name='Admin',
                last_name='User',
                email='admin@example.com',
            )
            
            self.stdout.write(self.style.SUCCESS(f'Super user created with phone: {admin_phone}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create super user: {str(e)}')) 