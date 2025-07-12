from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Phone verification
    path('send-verification-code/', views.send_verification_code, name='send_verification_code'),
    path('verify-phone/', views.verify_phone, name='verify_phone'),
    
    # User authentication endpoints
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    
    # Password reset
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-code/', views.verify_reset_code, name='verify_reset_code'),
    path('reset-password/', views.reset_password, name='reset_password'),
    
    # Profile management
    path('profile/', views.user_profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/upload-image/', views.upload_profile_image, name='upload_profile_image'),
    
    # Admin direct login (for troubleshooting)
    path('direct-admin-login/', views.direct_admin_login, name='direct_admin_login'),
] 