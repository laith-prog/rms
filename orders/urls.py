from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Order endpoints for customers
    path('', views.order_list, name='order_list'),
    path('create/', views.create_order, name='create_order'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    path('<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('<int:order_id>/track/', views.track_order, name='track_order'),
    
    # Order endpoints for staff
    path('staff/', views.staff_order_list, name='staff_order_list'),
    path('staff/<int:order_id>/update/', views.staff_update_order, name='staff_update_order'),
    path('chef/orders/', views.chef_orders, name='chef_orders'),
    path('waiter/orders/', views.waiter_orders, name='waiter_orders'),
] 