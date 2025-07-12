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
] 