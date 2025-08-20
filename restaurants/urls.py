from django.urls import path
from . import views

app_name = 'restaurants'

urlpatterns = [
    # Restaurant endpoints
    path('', views.restaurant_list, name='restaurant_list'),
    path('categories/', views.category_list, name='category_list'),
    path('<int:restaurant_id>/', views.restaurant_detail, name='restaurant_detail'),
    path('<int:restaurant_id>/menu/', views.restaurant_menu, name='restaurant_menu'),
    path('<int:restaurant_id>/reviews/', views.restaurant_reviews, name='restaurant_reviews'),
    
    # Reservation endpoints
    path('<int:restaurant_id>/tables/', views.available_tables, name='available_tables'),
    path('<int:restaurant_id>/reserve/', views.create_reservation, name='create_reservation'),
    path('reservations/', views.user_reservations, name='user_reservations'),
    path('reservations/<int:reservation_id>/', views.reservation_detail, name='reservation_detail'),
    path('reservations/<int:reservation_id>/cancel/', views.cancel_reservation, name='cancel_reservation'),
    path('reservations/<int:reservation_id>/update-status/', views.update_reservation_status, name='update_reservation_status'),
    
    # New reservation system endpoints
    path('<int:restaurant_id>/available-dates/', views.available_dates, name='available_dates'),
    path('<int:restaurant_id>/available-times/', views.available_times, name='available_times'),
    path('<int:restaurant_id>/available-durations/', views.available_durations, name='available_durations'),
    
    # Manager dashboard endpoints
    path('dashboard/', views.restaurant_dashboard, name='restaurant_dashboard'),
    
    # Admin endpoints (superuser only)
    path('create-with-manager/', views.create_restaurant_with_manager, name='create_restaurant_with_manager'),
    path('categories/create/', views.create_restaurant_category, name='create_restaurant_category'),
    
    # Manager endpoints
    path('menu-items/create/', views.create_menu_item, name='create_menu_item'),
    path('categories/add/', views.add_category_to_restaurant, name='add_category_to_restaurant'),
    
    # Staff endpoints (waiters and chefs)
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/shifts/', views.staff_shifts, name='staff_shifts'),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('staff/analytics/', views.analytics_dashboard, name='analytics_dashboard'),
] 