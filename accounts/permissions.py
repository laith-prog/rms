from rest_framework.permissions import BasePermission

class IsCustomer(BasePermission):
    """
    Permission to only allow customers to access the view.
    """
    message = "You must be a customer to perform this action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_customer


class IsStaffMember(BasePermission):
    """
    Permission to only allow staff members to access the view.
    """
    message = "You must be a staff member to perform this action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff_member


class IsRestaurantStaff(BasePermission):
    """
    Permission to only allow staff members of a specific restaurant to access the view.
    """
    message = "You must be a staff member of this restaurant to perform this action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff_member

    def has_object_permission(self, request, view, obj):
        if not request.user.is_staff_member:
            return False
        
        # Check if the staff member belongs to the restaurant
        try:
            staff_profile = request.user.staff_profile
            return staff_profile.restaurant == obj.restaurant
        except:
            return False

class IsSuperAdmin(BasePermission):
    """
    Permission to only allow superadmins to access the view.
    Superadmins can only manage restaurants, managers and restaurant categories.
    """
    message = "You must be a superadmin to perform this action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser


class IsRestaurantManager(BasePermission):
    """
    Permission to only allow restaurant managers to access the view.
    Managers can manage food items and food categories.
    """
    message = "You must be a restaurant manager to perform this action."

    def has_permission(self, request, view):
        if not (request.user.is_authenticated and request.user.is_staff_member):
            return False
        try:
            return request.user.staff_profile.role == 'manager'
        except:
            return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_staff_member:
            return False
        
        try:
            staff_profile = request.user.staff_profile
            if staff_profile.role != 'manager':
                return False
                
            # Check if the manager belongs to the restaurant
            if hasattr(obj, 'restaurant'):
                return staff_profile.restaurant == obj.restaurant
            elif hasattr(obj, 'menu') and hasattr(obj.menu, 'restaurant'):
                return staff_profile.restaurant == obj.menu.restaurant
            return False
        except:
            return False


class IsWaiterOrChef(BasePermission):
    """
    Permission to only allow waiters or chefs to access the view.
    These roles can manage shifts, orders, reservations, tables, menu item reviews, etc.
    """
    message = "You must be a waiter or chef to perform this action."

    def has_permission(self, request, view):
        if not (request.user.is_authenticated and request.user.is_staff_member):
            return False
        try:
            role = request.user.staff_profile.role
            return role in ['waiter', 'chef']
        except:
            return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_staff_member:
            return False
        
        try:
            staff_profile = request.user.staff_profile
            if staff_profile.role not in ['waiter', 'chef']:
                return False
                
            # Check if the staff member belongs to the restaurant
            if hasattr(obj, 'restaurant'):
                return staff_profile.restaurant == obj.restaurant
            elif hasattr(obj, 'table') and hasattr(obj.table, 'restaurant'):
                return staff_profile.restaurant == obj.table.restaurant
            elif hasattr(obj, 'order') and hasattr(obj.order, 'restaurant'):
                return staff_profile.restaurant == obj.order.restaurant
            return False
        except:
            return False


class IsChef(BasePermission):
    """
    Permission to only allow chefs to access the view.
    """
    message = "You must be a chef to perform this action."

    def has_permission(self, request, view):
        if not (request.user.is_authenticated and request.user.is_staff_member):
            return False
        try:
            return request.user.staff_profile.role == 'chef'
        except:
            return False


class IsWaiter(BasePermission):
    """
    Permission to only allow waiters to access the view.
    """
    message = "You must be a waiter to perform this action."

    def has_permission(self, request, view):
        if not (request.user.is_authenticated and request.user.is_staff_member):
            return False
        try:
            return request.user.staff_profile.role == 'waiter'
        except:
            return False


class IsOnShift(BasePermission):
    """
    Permission to only allow staff members who are currently on shift.
    """
    message = "You must be on shift to perform this action."

    def has_permission(self, request, view):
        if not (request.user.is_authenticated and request.user.is_staff_member):
            return False
        try:
            return request.user.staff_profile.is_on_shift
        except:
            return False 