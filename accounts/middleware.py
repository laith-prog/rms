from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse


class AdminAccessMiddleware:
    """
    Middleware to restrict access to admin panels based on user role.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        
        # Clear any login errors when accessing login pages
        if path.endswith('/login/') or 'login' in path:
            if 'login_error' in request.session:
                del request.session['login_error']
            return self.get_response(request)

        # If the request is for the default admin panel, redirect based on role
        if path == '/admin/' and request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('/superadmin/')
            elif request.user.is_staff_member:
                try:
                    role = request.user.staff_profile.role
                    if role == 'manager':
                        return redirect('/manager/')
                    elif role in ['waiter', 'chef']:
                        return redirect('/staff/')
                except:
                    pass
            return self.get_response(request)

        # Check if the request is for an admin panel
        if path.startswith('/superadmin/'):
            if not request.user.is_authenticated:
                return redirect('/admin/login/?next=' + path)
            elif not request.user.is_superuser:
                return HttpResponseForbidden("Access denied. Superadmin privileges required.")
        
        elif path.startswith('/manager/'):
            if not request.user.is_authenticated:
                return redirect('/admin/login/?next=' + path)
            elif not request.user.is_staff_member:
                return HttpResponseForbidden("Access denied. Manager privileges required.")
            else:
                # Verify the user is a manager
                try:
                    if request.user.staff_profile.role != 'manager':
                        return HttpResponseForbidden("Access denied. Manager privileges required.")
                except:
                    return HttpResponseForbidden("Access denied. Manager profile not found.")
        
        elif path.startswith('/staff/'):
            if not request.user.is_authenticated:
                return redirect('/admin/login/?next=' + path)
            elif not request.user.is_staff_member:
                return HttpResponseForbidden("Access denied. Staff privileges required.")
            else:
                # Verify the user is a waiter or chef
                try:
                    role = request.user.staff_profile.role
                    if role not in ['waiter', 'chef']:
                        return HttpResponseForbidden("Access denied. Staff privileges required.")
                except:
                    return HttpResponseForbidden("Access denied. Staff profile not found.")

        response = self.get_response(request)
        return response 