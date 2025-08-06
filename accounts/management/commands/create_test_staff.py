from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import StaffProfile
from restaurants.models import Restaurant
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Create test staff members (chef and waiter) for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--restaurant-id',
            type=int,
            help='Restaurant ID to assign staff to (required)',
            required=True
        )

    def handle(self, *args, **options):
        restaurant_id = options['restaurant_id']
        
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
        except Restaurant.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Restaurant with ID {restaurant_id} does not exist')
            )
            return

        # Create test chef
        chef_phone = "1234567890"
        if not User.objects.filter(phone=chef_phone).exists():
            chef_user = User.objects.create_user(
                phone=chef_phone,
                password="testpass123",
                first_name="John",
                last_name="Chef",
                is_staff_member=True,
                is_phone_verified=True
            )
            
            chef_profile = StaffProfile.objects.create(
                user=chef_user,
                role='chef',
                restaurant=restaurant
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Created chef: {chef_user.first_name} {chef_user.last_name} (Phone: {chef_phone})')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Chef with phone {chef_phone} already exists')
            )

        # Create test waiter
        waiter_phone = "0987654321"
        if not User.objects.filter(phone=waiter_phone).exists():
            waiter_user = User.objects.create_user(
                phone=waiter_phone,
                password="testpass123",
                first_name="Jane",
                last_name="Waiter",
                is_staff_member=True,
                is_phone_verified=True
            )
            
            waiter_profile = StaffProfile.objects.create(
                user=waiter_user,
                role='waiter',
                restaurant=restaurant
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Created waiter: {waiter_user.first_name} {waiter_user.last_name} (Phone: {waiter_phone})')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Waiter with phone {waiter_phone} already exists')
            )

        self.stdout.write(
            self.style.SUCCESS(f'\nTest staff created for restaurant: {restaurant.name}')
        )
        self.stdout.write('Login credentials:')
        self.stdout.write(f'Chef - Phone: {chef_phone}, Password: testpass123')
        self.stdout.write(f'Waiter - Phone: {waiter_phone}, Password: testpass123')
        self.stdout.write('\nUse the staff login endpoint: /api/accounts/staff/login/')