from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, CustomerProfile, StaffProfile, PhoneVerification, PasswordReset


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False
    verbose_name_plural = 'Customer Profile'


class StaffProfileInline(admin.StackedInline):
    model = StaffProfile
    can_delete = False
    verbose_name_plural = 'Staff Profile'


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('phone', 'email', 'first_name', 'last_name', 'is_staff', 'is_customer', 'is_staff_member', 'is_phone_verified')
    list_filter = ('is_staff', 'is_customer', 'is_staff_member', 'is_phone_verified')
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_customer', 'is_staff_member', 'is_phone_verified')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'password1', 'password2', 'is_customer', 'is_staff_member'),
        }),
    )
    search_fields = ('phone', 'email', 'first_name', 'last_name')
    ordering = ('phone',)
    
    def get_inlines(self, request, obj=None):
        if obj:
            if obj.is_customer:
                return [CustomerProfileInline]
            elif obj.is_staff_member:
                return [StaffProfileInline]
        return []


class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ('phone', 'code', 'is_used', 'created_at')
    search_fields = ('phone',)
    list_filter = ('is_used',)
    readonly_fields = ('created_at',)


class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ('phone', 'code', 'is_used', 'created_at')
    search_fields = ('phone',)
    list_filter = ('is_used',)
    readonly_fields = ('created_at',)


admin.site.register(User, CustomUserAdmin)
admin.site.register(PhoneVerification, PhoneVerificationAdmin)
admin.site.register(PasswordReset, PasswordResetAdmin)
