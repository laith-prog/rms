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