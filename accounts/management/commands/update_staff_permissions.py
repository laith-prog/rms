from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import User, StaffProfile
from restaurants.models import MenuItem, Category, Table, Reservation, Review
from orders.models import Order


class Command(BaseCommand):
    help = 'Update permissions for all staff members based on their roles'

    def handle(self, *args, **options):
        self.stdout.write('Updating staff permissions...')
        
        # Get all staff members
        staff_members = User.objects.filter(is_staff_member=True)
        self.stdout.write(f'Found {staff_members.count()} staff members')
        
        # Update permissions for each staff member
        for user in staff_members:
            try:
                profile = user.staff_profile
                role = profile.role
                
                # Make sure user has is_staff=True
                if not user.is_staff:
                    user.is_staff = True
                    user.save()
                
                # Update permissions based on role
                if role == 'manager':
                    self._ensure_permissions(user, [MenuItem, Category])
                    self.stdout.write(f'Updated permissions for manager: {user.phone}')
                elif role in ['waiter', 'chef']:
                    self._ensure_permissions(user, [Table, Reservation, Order, Review])
                    self.stdout.write(f'Updated permissions for {role}: {user.phone}')
            except StaffProfile.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'User {user.phone} has no staff profile'))
        
        self.stdout.write(self.style.SUCCESS('Successfully updated staff permissions'))
    
    def _ensure_permissions(self, user, model_classes):
        """Ensure the user has view and change permissions for the given models"""
        for model_class in model_classes:
            content_type = ContentType.objects.get_for_model(model_class)
            for action in ['view', 'change', 'add', 'delete']:
                perm = Permission.objects.get(
                    content_type=content_type, 
                    codename=f'{action}_{model_class._meta.model_name}'
                )
                user.user_permissions.add(perm) 