from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints
    path('send-verification-code/', views.send_verification_code, name='send_verification_code'),
    path('verify-phone/', views.verify_phone, name='verify_phone'),
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    
    # Password reset endpoints
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-code/', views.verify_reset_code, name='verify_reset_code'),
    path('reset-password/', views.reset_password, name='reset_password'),
    
    # Profile endpoints
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/upload-image/', views.upload_profile_image, name='upload_profile_image'),
    
    # Staff authentication endpoints
    path('staff/login/', views.staff_login, name='staff_login'),
    path('staff/profile/', views.staff_profile, name='staff_profile'),
    path('staff/profile/update/', views.update_staff_profile, name='update_staff_profile'),
    path('staff/shifts/', views.staff_shifts, name='staff_shifts'),
    path('staff/clock-toggle/', views.staff_clock_toggle, name='staff_clock_toggle'),
    
    # Staff management endpoints (for managers)
    path('staff/create/', views.create_staff_member, name='create_staff_member'),
    path('staff/create-waiter/', views.create_waiter, name='create_waiter'),
    path('staff/create-chef/', views.create_chef, name='create_chef'),
    path('staff/shifts/create/', views.create_staff_shift, name='create_staff_shift'),
    path('staff/list/', views.staff_list, name='staff_list'),
    
    # Direct admin login for troubleshooting
    path('direct-admin-login/', views.direct_admin_login, name='direct_admin_login'),
    
    # Fix permissions for troubleshooting
    path('fix-manager-permissions/', views.fix_manager_permissions, name='fix_manager_permissions'),
    
    # Debug endpoint (development only)
    path('debug-token/', views.debug_token, name='debug_token'),
] 