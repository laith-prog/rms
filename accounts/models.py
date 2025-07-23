from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
import random
import datetime
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    """
    Custom user manager where phone is the unique identifier
    for authentication instead of username.
    """
    def create_user(self, phone, password=None, **extra_fields):
        """
        Create and save a User with the given phone and password.
        """
        if not phone:
            raise ValueError(_('The Phone number must be set'))
        
        # Ensure staff members have is_staff=True for Django admin
        if extra_fields.get('is_staff_member', False):
            extra_fields['is_staff'] = True
            
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given phone and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(phone, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model that uses phone number instead of username
    """
    username = None  # Remove username field
    phone = models.CharField(_('phone number'), max_length=15, unique=True)
    email = models.EmailField(_('email address'), blank=True)
    
    # Custom fields for the two types of users
    is_customer = models.BooleanField(default=False)
    is_staff_member = models.BooleanField(default=False)
    
    # Phone verification
    is_phone_verified = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()
    
    def save(self, *args, **kwargs):
        # Ensure staff members have is_staff=True for Django admin
        if self.is_staff_member and not self.is_staff:
            self.is_staff = True
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.phone})"
        return self.phone


class PhoneVerification(models.Model):
    """
    Store verification codes for phone verification
    """
    phone = models.CharField(max_length=15)
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    @classmethod
    def generate_code(cls, phone):
        """Generate a 4-digit verification code"""
        # Delete any existing unused codes for this phone
        cls.objects.filter(phone=phone, is_used=False).delete()
        
        # Generate a new code
        code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        verification = cls.objects.create(phone=phone, code=code)
        return verification
    
    @classmethod
    def verify_code(cls, phone, code):
        """Verify the code for a phone number"""
        # Check if code exists and is not expired (valid for 10 minutes)
        time_threshold = timezone.now() - datetime.timedelta(minutes=10)
        try:
            verification = cls.objects.get(
                phone=phone,
                code=code,
                is_used=False,
                created_at__gt=time_threshold
            )
            verification.is_used = True
            verification.save()
            return True
        except cls.DoesNotExist:
            return False
    
    def __str__(self):
        return f"Verification code for {self.phone}"


class CustomerProfile(models.Model):
    """
    Profile for customer users with additional information
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    dietary_preferences = models.TextField(blank=True, null=True)
    default_address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile for {self.user.phone}"


class StaffProfile(models.Model):
    """
    Profile for staff users with roles and permissions
    """
    ROLE_CHOICES = (
        ('waiter', 'Waiter'),
        ('chef', 'Chef'),
        ('manager', 'Manager'),
        ('employee', 'Employee'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    profile_image = models.ImageField(upload_to='staff_images/', blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.CASCADE, related_name='staff')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_on_shift = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.role} - {self.user.phone}"


class StaffShift(models.Model):
    """
    Staff shift schedule and tracking
    """
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='shifts')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_shifts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.staff} - {self.start_time.strftime('%Y-%m-%d %H:%M')} to {self.end_time.strftime('%H:%M')}"
    
    def save(self, *args, **kwargs):
        """Update staff on_shift status when saving a shift"""
        super().save(*args, **kwargs)
        
        # Check if this is a current shift
        now = timezone.now()
        if self.is_active and self.start_time <= now <= self.end_time:
            self.staff.is_on_shift = True
            self.staff.save()
        elif self.staff.is_on_shift:
            # Check if the staff member has any other active shifts
            current_shifts = StaffShift.objects.filter(
                staff=self.staff,
                is_active=True,
                start_time__lte=now,
                end_time__gte=now
            ).exclude(id=self.id)
            
            if not current_shifts.exists():
                self.staff.is_on_shift = False
                self.staff.save()


class PasswordReset(models.Model):
    """
    Store password reset codes
    """
    phone = models.CharField(max_length=15)
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    @classmethod
    def generate_code(cls, phone):
        """Generate a 4-digit password reset code"""
        # Delete any existing unused codes for this phone
        cls.objects.filter(phone=phone, is_used=False).delete()
        
        # Generate a new code
        code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        reset = cls.objects.create(phone=phone, code=code)
        return reset
    
    @classmethod
    def verify_code(cls, phone, code):
        """Verify the password reset code"""
        # Check if code exists and is not expired (valid for 10 minutes)
        time_threshold = timezone.now() - datetime.timedelta(minutes=10)
        try:
            reset = cls.objects.get(
                phone=phone,
                code=code,
                is_used=False,
                created_at__gt=time_threshold
            )
            reset.is_used = True
            reset.save()
            return True
        except cls.DoesNotExist:
            return False
    
    def __str__(self):
        return f"Password reset code for {self.phone}"


class TokenVersion(models.Model):
    """
    Store token version for each user to invalidate tokens after logout
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='token_version')
    version = models.IntegerField(default=0)
    last_logout = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Token version for {self.user.phone}: {self.version}"
    
    @classmethod
    def get_version(cls, user):
        """Get the current token version for a user"""
        token_version, created = cls.objects.get_or_create(user=user)
        return token_version.version
    
    @classmethod
    def increment_version(cls, user):
        """Increment the token version for a user, invalidating all existing tokens"""
        token_version, created = cls.objects.get_or_create(user=user)
        token_version.version += 1
        token_version.save()
        return token_version.version
