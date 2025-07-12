from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Check admin user details'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Checking admin users...'))

        # Get all superusers
        superusers = User.objects.filter(is_superuser=True)

        if not superusers.exists():
            self.stdout.write(self.style.WARNING('No superusers found in the database'))
            return

        self.stdout.write(self.style.SUCCESS(f'Found {superusers.count()} superuser(s):'))

        for user in superusers:
            self.stdout.write(self.style.SUCCESS(f'- Phone: {user.phone}'))
            self.stdout.write(self.style.SUCCESS(f'- password: {user.password}'))
            self.stdout.write(self.style.SUCCESS(f'  First name: {user.first_name}'))
            self.stdout.write(self.style.SUCCESS(f'  Last name: {user.last_name}'))
            self.stdout.write(self.style.SUCCESS(f'  Email: {user.email}'))
            self.stdout.write(self.style.SUCCESS(f'  Is active: {user.is_active}'))
            self.stdout.write(self.style.SUCCESS(f'  Is staff: {user.is_staff}'))
            self.stdout.write(self.style.SUCCESS(f'  Is superuser: {user.is_superuser}'))
            self.stdout.write(self.style.SUCCESS('---'))
