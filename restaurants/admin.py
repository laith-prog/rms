from django.contrib import admin
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib import messages
from django import forms
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from .models import Category, Restaurant, RestaurantImage, MenuItem, Table, Reservation, Review, ReservationStatusUpdate
from accounts.models import StaffProfile

User = get_user_model()


# Function to ensure users have the necessary permissions
def ensure_user_permissions(user, model_classes):
    """
    Ensure the user has view and change permissions for the given models
    """
    if not user.is_active or not user.is_staff:
        return
        
    for model_class in model_classes:
        content_type = ContentType.objects.get_for_model(model_class)
        view_perm = Permission.objects.get(content_type=content_type, codename=f'view_{model_class._meta.model_name}')
        change_perm = Permission.objects.get(content_type=content_type, codename=f'change_{model_class._meta.model_name}')
        add_perm = Permission.objects.get(content_type=content_type, codename=f'add_{model_class._meta.model_name}')
        delete_perm = Permission.objects.get(content_type=content_type, codename=f'delete_{model_class._meta.model_name}')
        
        user.user_permissions.add(view_perm)
        user.user_permissions.add(change_perm)
        user.user_permissions.add(add_perm)
        user.user_permissions.add(delete_perm)


# Custom Admin Sites for different roles
class SuperAdminSite(AdminSite):
    site_header = 'Restaurant Management System - Super Admin'
    site_title = 'RMS Super Admin'
    index_title = 'Restaurant Management Administration'
    
    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser


class ManagerAdminSite(AdminSite):
    site_header = 'Restaurant Management System - Manager'
    site_title = 'RMS Manager'
    index_title = 'Restaurant Manager Dashboard'
    
    def has_permission(self, request):
        # First check if the user is authenticated and active
        if not request.user.is_authenticated or not request.user.is_active:
            return False
            
        # Check if user is a staff member
        if not hasattr(request.user, 'is_staff_member') or not request.user.is_staff_member:
            return False
            
        # Check if user has a staff profile with manager role
        try:
            is_manager = request.user.staff_profile.role == 'manager'
            if is_manager:
                # Import here to avoid circular import
                from orders.models import Order, OrderItem, OrderStatusUpdate
                # Ensure the manager has permissions for all relevant models
                ensure_user_permissions(
                    request.user, 
                    [
                        MenuItem, Category, Table, Reservation, Order, Review, 
                        RestaurantImage, ReservationStatusUpdate, OrderItem, OrderStatusUpdate
                    ]
                )
            return is_manager
        except:
            return False


class StaffAdminSite(AdminSite):
    site_header = 'Restaurant Management System - Staff'
    site_title = 'RMS Staff'
    index_title = 'Staff Dashboard'
    
    def has_permission(self, request):
        # First check if the user is authenticated and active
        if not request.user.is_authenticated or not request.user.is_active:
            return False
            
        # Check if user is a staff member
        if not hasattr(request.user, 'is_staff_member') or not request.user.is_staff_member:
            return False
            
        # Check if user has a staff profile with waiter or chef role
        try:
            role = request.user.staff_profile.role
            is_valid_staff = role in ['waiter', 'chef']
            if is_valid_staff:
                # Ensure the staff member has permissions for Table, Reservation, Order, and Review
                from orders.models import Order
                ensure_user_permissions(request.user, [Table, Reservation, Order, Review])
            return is_valid_staff
        except:
            return False


# Create instances of each admin site
superadmin_site = SuperAdminSite(name='superadmin')
manager_site = ManagerAdminSite(name='manager')
staff_site = StaffAdminSite(name='staff')


class RestaurantImageInline(admin.TabularInline):
    model = RestaurantImage
    extra = 3


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1


class TableInline(admin.TabularInline):
    model = Table
    extra = 1


class RestaurantManagerForm(forms.ModelForm):
    """Form for creating a restaurant with a manager"""
    manager_phone = forms.CharField(max_length=15, required=False, help_text="Phone number for the restaurant manager")
    manager_password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Password for the manager account")
    manager_first_name = forms.CharField(max_length=30, required=False, help_text="Manager's first name")
    manager_last_name = forms.CharField(max_length=30, required=False, help_text="Manager's last name")
    
    class Meta:
        model = Restaurant
        fields = '__all__'


# Admin classes for superadmin site
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


class RestaurantAdmin(admin.ModelAdmin):
    form = RestaurantManagerForm
    list_display = ('name', 'phone', 'average_rating', 'is_active', 'offers_dine_in', 'offers_takeaway', 'offers_delivery', 'manager_link')
    list_filter = ('is_active', 'offers_dine_in', 'offers_takeaway', 'offers_delivery', 'categories')
    search_fields = ('name', 'address', 'phone', 'email')
    filter_horizontal = ('categories',)
    inlines = [RestaurantImageInline, MenuItemInline, TableInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'address', 'phone', 'email', 'description', 'categories')
        }),
        ('Images', {
            'fields': ('logo', 'cover_image'),
            'classes': ('collapse',),
        }),
        ('Business Hours', {
            'fields': ('opening_time', 'closing_time'),
        }),
        ('Services', {
            'fields': ('offers_dine_in', 'offers_takeaway', 'offers_delivery', 'is_active'),
        }),
        ('Manager Information', {
            'fields': ('manager_phone', 'manager_password', 'manager_first_name', 'manager_last_name'),
            'description': 'Create a manager user for this restaurant',
        }),
    )
    
    def manager_link(self, obj):
        """Display link to manager if exists"""
        # Check if restaurant has a manager
        manager = StaffProfile.objects.filter(restaurant=obj, role='manager').first()
        if manager:
            return format_html(
                '<a href="{}">{} ({})</a>',
                reverse('admin:accounts_user_change', args=[manager.user.id]), 
                f"{manager.user.first_name} {manager.user.last_name}",
                manager.user.phone
            )
        else:
            return "No manager assigned"
    
    manager_link.short_description = 'Manager'
    
    def save_model(self, request, obj, form, change):
        """Save the restaurant and create a manager if manager details are provided"""
        super().save_model(request, obj, form, change)
        
        # Check if manager details are provided
        manager_phone = form.cleaned_data.get('manager_phone')
        manager_password = form.cleaned_data.get('manager_password')
        manager_first_name = form.cleaned_data.get('manager_first_name')
        manager_last_name = form.cleaned_data.get('manager_last_name')
        
        # Only create manager if all fields are filled and we don't already have a manager
        if all([manager_phone, manager_password, manager_first_name, manager_last_name]):
            # Check if a manager already exists for this restaurant
            if StaffProfile.objects.filter(restaurant=obj, role='manager').exists():
                messages.warning(request, 'This restaurant already has a manager assigned.')
                return
            
            # Check if user with this phone already exists
            if User.objects.filter(phone=manager_phone).exists():
                messages.error(request, f'User with phone {manager_phone} already exists. Manager not created.')
                return
            
            # Create the manager user
            try:
                manager_user = User.objects.create_user(
                    phone=manager_phone,
                    password=manager_password,
                    first_name=manager_first_name,
                    last_name=manager_last_name,
                    is_staff_member=True,
                    is_phone_verified=True
                )
                
                # Create the manager profile
                StaffProfile.objects.create(
                    user=manager_user,
                    role='manager',
                    restaurant=obj
                )
                
                messages.success(request, f'Manager {manager_first_name} {manager_last_name} created successfully.')
            except Exception as e:
                messages.error(request, f'Error creating manager: {str(e)}')


# Admin classes for manager site
class ManagerMenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'food_category', 'price', 'is_active', 'is_vegetarian', 'is_vegan')
    list_filter = ('is_active', 'food_category', 'is_vegetarian', 'is_vegan', 'is_gluten_free', 'contains_nuts', 'contains_dairy', 'is_spicy')
    search_fields = ('name', 'description')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show menu items for the manager's restaurant
        if request.user.is_staff_member:
            try:
                staff_profile = request.user.staff_profile
                if staff_profile.role == 'manager':
                    return qs.filter(restaurant=staff_profile.restaurant)
            except:
                pass
        # For superusers, show all items
        if request.user.is_superuser:
            return qs
        return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit restaurant choices to the manager's restaurant
        if db_field.name == "restaurant" and request.user.is_staff_member:
            try:
                staff_profile = request.user.staff_profile
                if staff_profile.role == 'manager':
                    kwargs["queryset"] = Restaurant.objects.filter(id=staff_profile.restaurant.id)
            except:
                kwargs["queryset"] = Restaurant.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def has_view_permission(self, request, obj=None):
        # Superusers can view anything
        if request.user.is_superuser:
            return True
        # Managers can view their restaurant's items
        if request.user.is_staff_member:
            try:
                return request.user.staff_profile.role == 'manager'
            except:
                pass
        return False
    
    def has_change_permission(self, request, obj=None):
        # Similar to view permission
        return self.has_view_permission(request, obj)
    
    def has_add_permission(self, request):
        # Similar to view permission
        return self.has_view_permission(request, None)
    
    def has_delete_permission(self, request, obj=None):
        # Similar to view permission
        return self.has_view_permission(request, obj)


class ManagerCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    
    def has_add_permission(self, request):
        # Managers cannot create new categories, only use existing ones
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Managers cannot delete categories
        return False
    
    def has_change_permission(self, request, obj=None):
        # Managers cannot edit categories
        return False
    
    def has_view_permission(self, request, obj=None):
        # Superusers can view anything
        if request.user.is_superuser:
            return True
        # Managers can view categories
        if request.user.is_staff_member:
            try:
                return request.user.staff_profile.role == 'manager'
            except:
                pass
        return False


# Admin classes for manager site
class ManagerTableAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'table_number', 'capacity', 'is_active', 'is_reserved')
    list_filter = ('is_active', 'is_reserved')
    search_fields = ('table_number',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show tables for the manager's restaurant
        if request.user.is_staff_member:
            try:
                staff_profile = request.user.staff_profile
                if staff_profile.role == 'manager':
                    return qs.filter(restaurant=staff_profile.restaurant)
            except:
                pass
        # For superusers, show all tables
        if request.user.is_superuser:
            return qs
        return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit restaurant choices to the manager's restaurant
        if db_field.name == "restaurant" and request.user.is_staff_member:
            try:
                staff_profile = request.user.staff_profile
                if staff_profile.role == 'manager':
                    kwargs["queryset"] = Restaurant.objects.filter(id=staff_profile.restaurant.id)
            except:
                kwargs["queryset"] = Restaurant.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ManagerReservationAdmin(admin.ModelAdmin):
    list_display = ('customer', 'restaurant', 'table', 'party_size', 'reservation_date', 'reservation_time', 'status')
    list_filter = ('status', 'reservation_date')
    search_fields = ('customer__phone', 'special_requests')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show reservations for the manager's restaurant
        if request.user.is_staff_member:
            try:
                staff_profile = request.user.staff_profile
                if staff_profile.role == 'manager':
                    return qs.filter(restaurant=staff_profile.restaurant)
            except:
                pass
        # For superusers, show all reservations
        if request.user.is_superuser:
            return qs
        return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit restaurant and table choices to the manager's restaurant
        if request.user.is_staff_member:
            try:
                staff_profile = request.user.staff_profile
                if staff_profile.role == 'manager':
                    if db_field.name == "restaurant":
                        kwargs["queryset"] = Restaurant.objects.filter(id=staff_profile.restaurant.id)
                    elif db_field.name == "table":
                        kwargs["queryset"] = Table.objects.filter(restaurant=staff_profile.restaurant)
            except:
                if db_field.name in ["restaurant", "table"]:
                    kwargs["queryset"] = db_field.related_model.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ManagerOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'restaurant', 'order_type', 'status', 'created_at')
    list_filter = ('status', 'order_type')
    search_fields = ('customer__phone', 'special_instructions')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show orders for the manager's restaurant
        if request.user.is_staff_member:
            try:
                staff_profile = request.user.staff_profile
                if staff_profile.role == 'manager':
                    return qs.filter(restaurant=staff_profile.restaurant)
            except:
                pass
        # For superusers, show all orders
        if request.user.is_superuser:
            return qs
        return qs.none()


class ManagerRestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone', 'average_rating', 'is_active')
    readonly_fields = ('name', 'address', 'phone', 'email', 'description', 'opening_time', 'closing_time', 
                      'categories', 'is_active', 'average_rating', 'offers_dine_in', 'offers_takeaway', 'offers_delivery',
                      'logo', 'cover_image', 'created_at', 'updated_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show the manager's restaurant
        if request.user.is_staff_member:
            try:
                staff_profile = request.user.staff_profile
                if staff_profile.role == 'manager':
                    return qs.filter(id=staff_profile.restaurant.id)
            except:
                pass
        return qs.none()


class StaffTableAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'table_number', 'capacity', 'is_active', 'is_reserved')
    list_filter = ('is_active', 'is_reserved')
    search_fields = ('table_number',)
    readonly_fields = ('restaurant', 'table_number', 'capacity', 'is_active', 'is_reserved')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show tables for the staff member's restaurant
        if request.user.is_staff_member:
            try:
                staff_profile = request.user.staff_profile
                return qs.filter(restaurant=staff_profile.restaurant)
            except:
                pass
        return qs.none()


class StaffReservationAdmin(admin.ModelAdmin):
    list_display = ('customer', 'restaurant', 'table', 'party_size', 'reservation_date', 'reservation_time', 'status')
    list_filter = ('status', 'reservation_date')
    search_fields = ('customer__phone', 'special_requests')
    readonly_fields = ('customer', 'restaurant', 'table', 'party_size', 'reservation_date', 'reservation_time', 'special_requests')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show reservations for the staff member's restaurant
        if request.user.is_staff_member:
            try:
                staff_profile = request.user.staff_profile
                return qs.filter(restaurant=staff_profile.restaurant)
            except:
                pass
        return qs.none()


class StaffOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'restaurant', 'order_type', 'status', 'created_at')
    list_filter = ('status', 'order_type')
    search_fields = ('customer__phone', 'special_instructions')
    readonly_fields = ('customer', 'restaurant', 'order_type', 'subtotal', 'tax', 'delivery_fee', 'total', 'special_instructions')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show orders for the staff member's restaurant
        if request.user.is_staff_member:
            try:
                staff_profile = request.user.staff_profile
                return qs.filter(restaurant=staff_profile.restaurant)
            except:
                pass
        return qs.none()


class StaffReviewAdmin(admin.ModelAdmin):
    list_display = ('customer', 'restaurant', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('comment',)
    readonly_fields = ('customer', 'restaurant', 'rating', 'comment', 'created_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show reviews for the staff member's restaurant
        if request.user.is_staff_member:
            try:
                staff_profile = request.user.staff_profile
                return qs.filter(restaurant=staff_profile.restaurant)
            except:
                pass
        return qs.none()


# Register models with the superadmin site
superadmin_site.register(Category, CategoryAdmin)
superadmin_site.register(Restaurant, RestaurantAdmin)

# Register models with the manager site
manager_site.register(MenuItem, ManagerMenuItemAdmin)
manager_site.register(Category, ManagerCategoryAdmin)
manager_site.register(Table, ManagerTableAdmin)
manager_site.register(Reservation, ManagerReservationAdmin)
from orders.models import Order
manager_site.register(Order, ManagerOrderAdmin)
manager_site.register(Review, StaffReviewAdmin)
manager_site.register(ReservationStatusUpdate)
manager_site.register(Restaurant, ManagerRestaurantAdmin) # Register the read-only restaurant admin

# Make sure manager site has proper login configuration
manager_site.login_template = 'admin/login.html'
manager_site.site_url = None  # Disable "View Site" link

# Register models with the staff site
staff_site.register(Table, StaffTableAdmin)
staff_site.register(Reservation, StaffReservationAdmin)
from orders.models import Order
staff_site.register(Order, StaffOrderAdmin)
staff_site.register(Review, StaffReviewAdmin)

# Make sure staff site has proper login configuration
staff_site.login_template = 'admin/login.html'
staff_site.site_url = None  # Disable "View Site" link

# Keep the default admin site for backward compatibility
admin.site.register(Category, CategoryAdmin)
admin.site.register(Restaurant, RestaurantAdmin)
admin.site.register(MenuItem, ManagerMenuItemAdmin)
admin.site.register(Table, StaffTableAdmin)
admin.site.register(Reservation, StaffReservationAdmin)
admin.site.register(Review, StaffReviewAdmin)
