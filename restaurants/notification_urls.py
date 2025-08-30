"""
URL patterns for custom notification views
"""
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('custom-notification/', views.custom_notification_view, name='custom_notification'),
    path('get-customer-info/', views.get_customer_info, name='get_customer_info'),
    path('notification-templates/', views.notification_templates, name='notification_templates'),
]