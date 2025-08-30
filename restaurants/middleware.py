"""
Middleware for restaurant admin access control
"""
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class AdminAccessControlMiddleware:
    """
    Middleware to control access to different admin panels based on user roles
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check admin access before processing the request
        if self.should_check_admin_access(request):
            access_result = self.check_admin_access(request)
            if access_result is not None:
                return access_result

        response = self.get_response(request)
        return response

    def should_check_admin_access(self, request):
        """Determine if we should check admin access for this request"""
        path = request.path
        
        # Check if this is an admin URL
        admin_paths = ['/manager/', '/staff/', '/superadmin/']
        return any(path.startswith(admin_path) for admin_path in admin_paths)

    def check_admin_access(self, request):
        """Check if user has access to the requested admin panel"""
        path = request.path
        user = request.user
        
        # Skip check for login pages
        if 'login' in path:
            return None
            
        # Skip check for static files and API endpoints
        if any(path.startswith(prefix) for prefix in ['/static/', '/media/', '/api/']):
            return None
        
        # Check if user is authenticated
        if not user.is_authenticated:
            return None  # Let Django's auth handle this
        
        # Manager admin access
        if path.startswith('/manager/'):
            if not self.can_access_manager_admin(user):
                messages.error(request, 'Access denied. Manager privileges required.')
                return redirect('/')
        
        # Staff admin access
        elif path.startswith('/staff/'):
            if not self.can_access_staff_admin(user):
                messages.error(request, 'Access denied. Staff privileges required.')
                return redirect('/')
        
        # Super admin access
        elif path.startswith('/superadmin/'):
            if not user.is_superuser:
                messages.error(request, 'Access denied. Superuser privileges required.')
                return redirect('/')
        
        return None

    def can_access_manager_admin(self, user):
        """Check if user can access manager admin"""
        if user.is_superuser:
            return True
            
        if user.is_staff_member:
            try:
                staff_profile = user.staff_profile
                return staff_profile.role == 'manager'
            except:
                pass
        
        return False

    def can_access_staff_admin(self, user):
        """Check if user can access staff admin"""
        if user.is_superuser:
            return True
            
        return user.is_staff_member