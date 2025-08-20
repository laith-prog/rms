from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Order, OrderItem, OrderStatusUpdate
from restaurants.models import Restaurant, MenuItem
from accounts.models import StaffProfile


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    """
    Create a new order
    
    Creates a new food order for the authenticated customer or staff (except chefs). The order can be:
    - Dine-in: Linked to a table reservation
    - Pickup: For takeaway orders
    - Delivery: Requires a delivery address
    
    Each order must include at least one menu item.
    """
    try:
        user = request.user
        
        # Debug: Log user info
        print(f"DEBUG: User: {user}, is_customer: {getattr(user, 'is_customer', 'NOT SET')}, is_staff_member: {getattr(user, 'is_staff_member', 'NOT SET')}")
        
        # Allow customers, waiters, and managers to create orders, but not chefs
        if user.is_customer:
            # Customers can create orders
            pass
        elif user.is_staff_member:
            try:
                staff_profile = user.staff_profile
                
                # Chefs cannot create orders
                if staff_profile.role == 'chef':
                    return Response({'error': 'Chefs are not allowed to create orders'}, 
                                   status=status.HTTP_403_FORBIDDEN)
            except Exception as e:
                print(f"DEBUG: Staff profile error: {e}")
                return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'error': 'Only customers, waiters, or managers can create orders'}, 
                            status=status.HTTP_403_FORBIDDEN)
        
        # Get restaurant
        restaurant_id = request.data.get('restaurant_id')
        if not restaurant_id:
            return Response({'error': 'Restaurant ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
        
        # If staff member, ensure they belong to this restaurant
        if user.is_staff_member and user.staff_profile.restaurant.id != restaurant.id:
            return Response({'error': 'Staff can only create orders at their own restaurant'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # Get order type
        order_type = request.data.get('order_type')
        if not order_type or order_type not in ['dine_in', 'pickup', 'delivery']:
            return Response({'error': 'Valid order type is required (dine_in, pickup, delivery)'}, 
                             status=status.HTTP_400_BAD_REQUEST)
        
        # Check if restaurant offers this order type
        if order_type == 'dine_in' and not restaurant.offers_dine_in:
            return Response({'error': 'Restaurant does not offer dine-in service'}, 
                             status=status.HTTP_400_BAD_REQUEST)
        elif order_type == 'pickup' and not restaurant.offers_takeaway:
            return Response({'error': 'Restaurant does not offer pickup service'}, 
                             status=status.HTTP_400_BAD_REQUEST)
        elif order_type == 'delivery' and not restaurant.offers_delivery:
            return Response({'error': 'Restaurant does not offer delivery service'}, 
                             status=status.HTTP_400_BAD_REQUEST)
        
        # Get reservation ID if it's a dine-in order
        reservation_id = None
        if order_type == 'dine_in':
            reservation_id = request.data.get('reservation_id')
        
        # Get delivery address if it's a delivery order
        delivery_address = None
        if order_type == 'delivery':
            delivery_address = request.data.get('delivery_address')
            if not delivery_address:
                return Response({'error': 'Delivery address is required for delivery orders'}, 
                                 status=status.HTTP_400_BAD_REQUEST)
        
        # Get order items
        items_data = request.data.get('items')
        if not items_data or not isinstance(items_data, list) or len(items_data) == 0:
            return Response({'error': 'Order items are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate items and calculate total
        subtotal = 0
        items_to_create = []
        
        for item_data in items_data:
            item_id = item_data.get('item_id')
            quantity = item_data.get('quantity', 1)
            special_instructions = item_data.get('special_instructions', '')
            
            if not item_id:
                return Response({'error': 'Item ID is required for each order item'}, 
                                 status=status.HTTP_400_BAD_REQUEST)
            
            try:
                menu_item = MenuItem.objects.get(id=item_id, restaurant=restaurant, is_active=True)
                item_price = menu_item.price
                item_total = item_price * quantity
                subtotal += item_total
                
                items_to_create.append({
                    'menu_item': menu_item,
                    'quantity': quantity,
                    'item_price': item_price,
                    'special_instructions': special_instructions
                })
                
            except MenuItem.DoesNotExist:
                return Response({'error': f'Menu item with ID {item_id} not found'}, 
                                 status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate tax and total
        tax = subtotal * 0.1  # Assuming 10% tax
        delivery_fee = 5.0 if order_type == 'delivery' else 0  # Assuming $5 delivery fee
        total = subtotal + tax + delivery_fee
        
        # Create the order
        order = Order.objects.create(
            customer=user,
            restaurant=restaurant,
            order_type=order_type,
            subtotal=subtotal,
            tax=tax,
            delivery_fee=delivery_fee,
            total=total,
            status='pending',
            special_instructions=request.data.get('special_instructions', ''),
            delivery_address=delivery_address,
            payment_method=request.data.get('payment_method', 'cash')
        )
        
        # Associate with reservation if applicable
        if reservation_id:
            from restaurants.models import Reservation
            try:
                reservation = Reservation.objects.get(id=reservation_id, customer=user)
                order.reservation = reservation
                order.save()
            except Reservation.DoesNotExist:
                pass  # Ignore if reservation doesn't exist
        
        # Create order items
        for item in items_to_create:
            OrderItem.objects.create(
                order=order,
                menu_item=item['menu_item'],
                quantity=item['quantity'],
                item_price=item['item_price'],
                special_instructions=item['special_instructions']
            )
        
        # Calculate preparation time
        order.calculate_preparation_time()
        order.save()
        
        # Create initial status update
        OrderStatusUpdate.objects.create(
            order=order,
            status='pending',
            notes='Order received',
            updated_by=None  # System update
        )
        
        return Response({
            'success': 'Order created successfully',
            'order_id': order.id,
            'total': order.total,
            'estimated_preparation_time': order.estimated_preparation_time
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        print(f"DEBUG: Exception in create_order: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)