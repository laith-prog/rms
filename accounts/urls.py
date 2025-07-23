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
    
    # Staff management endpoints
    path('staff/create/', views.create_staff_member, name='create_staff_member'),
    path('staff/shifts/create/', views.create_staff_shift, name='create_staff_shift'),
    path('staff/list/', views.staff_list, name='staff_list'),
    
    # Direct admin login for troubleshooting
    path('direct-admin-login/', views.direct_admin_login, name='direct_admin_login'),
    
    # Fix permissions for troubleshooting
    path('fix-manager-permissions/', views.fix_manager_permissions, name='fix_manager_permissions'),
] 