from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from decimal import Decimal

from .models import Order, OrderItem, OrderStatusUpdate
from restaurants.models import Restaurant, MenuItem
from accounts.models import StaffProfile


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_list(request):
    """Get all orders for the current user (customer)"""
    user = request.user
    
    if not user.is_customer:
        return Response({'error': 'Only customers can view their orders'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    orders = Order.objects.filter(customer=user).order_by('-created_at')
    
    data = []
    for order in orders:
        data.append({
            'id': order.id,
            'restaurant': {
                'id': order.restaurant.id,
                'name': order.restaurant.name,
                'logo': order.restaurant.logo.url if order.restaurant.logo else None,
                'cover_image': order.restaurant.cover_image.url if order.restaurant.cover_image else None,
            },
            'order_type': order.get_order_type_display(),
            'status': order.get_status_display(),
            'total': order.total,
            'created_at': order.created_at,
            'estimated_preparation_time': order.estimated_preparation_time,
        })
    
    return Response(data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['restaurant_id', 'order_type', 'items'],
        properties={
            'restaurant_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the restaurant'),
            'order_type': openapi.Schema(type=openapi.TYPE_STRING, description='Order type: dine_in, pickup, or delivery', enum=['dine_in', 'pickup', 'delivery']),
            'reservation_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the reservation (for dine_in orders)', nullable=True),
            'delivery_address': openapi.Schema(type=openapi.TYPE_STRING, description='Delivery address (for delivery orders)', nullable=True),
            'payment_method': openapi.Schema(type=openapi.TYPE_STRING, description='Payment method', enum=['cash', 'credit_card', 'digital_wallet']),
            'special_instructions': openapi.Schema(type=openapi.TYPE_STRING, description='Special instructions for the order', nullable=True),
            'items': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    required=['item_id', 'quantity'],
                    properties={
                        'item_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the menu item'),
                        'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Quantity of the item'),
                        'special_instructions': openapi.Schema(type=openapi.TYPE_STRING, description='Special instructions for this item', nullable=True),
                    }
                )
            ),
        },
    ),
    responses={
        201: openapi.Response(
            description="Order created successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_STRING),
                    'order_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'total': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'estimated_preparation_time': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        ),
        400: 'Bad request - invalid input',
        403: 'Forbidden - only customers, waiters, and managers can create orders',
    },
    operation_description="Create a new food order (not available for chefs)"
)
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
    user = request.user
    
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
        except:
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
    subtotal = Decimal('0.00')
    items_to_create = []
    
    for item_data in items_data:
        # Accept both 'item_id' and 'menu_item_id' for flexibility
        item_id = item_data.get('item_id') or item_data.get('menu_item_id')
        quantity = item_data.get('quantity', 1)
        special_instructions = item_data.get('special_instructions', '')
        
        if not item_id:
            return Response({'error': 'Item ID (item_id or menu_item_id) is required for each order item'}, 
                             status=status.HTTP_400_BAD_REQUEST)
        
        if quantity <= 0:
            return Response({'error': 'Quantity must be greater than 0'}, 
                             status=status.HTTP_400_BAD_REQUEST)
        
        try:
            menu_item = MenuItem.objects.get(id=item_id, restaurant=restaurant, is_active=True)
            item_price = menu_item.price
            item_total = item_price * Decimal(str(quantity))
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
    tax = subtotal * Decimal('0.10')  # Assuming 10% tax
    delivery_fee = Decimal('5.00') if order_type == 'delivery' else Decimal('0.00')  # Assuming $5 delivery fee
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, order_id):
    """Get detailed information about an order"""
    user = request.user
    
    # Determine access rights
    if user.is_customer:
        # Customer can only view their own orders
        order = get_object_or_404(Order, id=order_id, customer=user)
    elif user.is_staff_member:
        # Staff can view orders in their restaurant
        try:
            staff_profile = user.staff_profile
            order = get_object_or_404(Order, id=order_id, restaurant=staff_profile.restaurant)
        except:
            return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    else:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get order items
    items = []
    for item in order.items.all():
        items.append({
            'id': item.id,
            'name': item.menu_item.name,
            'quantity': item.quantity,
            'price': item.item_price,
            'total': item.item_total,
            'special_instructions': item.special_instructions,
            'image': item.menu_item.image.url if item.menu_item.image else None,
        })
    
    # Get status updates
    status_updates = []
    for update in order.status_updates.all().order_by('-created_at'):
        status_updates.append({
            'status': update.get_status_display(),
            'notes': update.notes,
            'timestamp': update.created_at,
            'updated_by': update.updated_by.phone if update.updated_by else 'System',
        })
    
    data = {
        'id': order.id,
        'customer': {
            'phone': order.customer.phone,
        },
        'restaurant': {
            'id': order.restaurant.id,
            'name': order.restaurant.name,
            'address': order.restaurant.address,
            'phone': order.restaurant.phone,
            'logo': order.restaurant.logo.url if order.restaurant.logo else None,
            'cover_image': order.restaurant.cover_image.url if order.restaurant.cover_image else None,
        },
        'order_type': order.get_order_type_display(),
        'status': order.get_status_display(),
        'items': items,
        'payment': {
            'subtotal': order.subtotal,
            'tax': order.tax,
            'delivery_fee': order.delivery_fee,
            'total': order.total,
            'payment_status': order.get_payment_status_display(),
            'payment_method': order.get_payment_method_display(),
        },
        'timing': {
            'created_at': order.created_at,
            'estimated_preparation_time': order.estimated_preparation_time,
        },
        'special_instructions': order.special_instructions,
        'delivery_address': order.delivery_address,
        'status_updates': status_updates,
    }
    
    # Add reservation info if it exists
    if order.reservation:
        data['reservation'] = {
            'id': order.reservation.id,
            'table': order.reservation.table.table_number,
            'date': order.reservation.reservation_date,
            'time': order.reservation.reservation_time,
        }
    
    # Add assigned staff if applicable
    if order.assigned_chef:
        data['assigned_chef'] = order.assigned_chef.phone
    if order.assigned_waiter:
        data['assigned_waiter'] = order.assigned_waiter.phone
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """Cancel an order"""
    user = request.user
    
    if not user.is_customer:
        return Response({'error': 'Only customers can cancel their orders'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    order = get_object_or_404(Order, id=order_id, customer=user)
    
    # Check if order can be cancelled
    if order.status in ['completed', 'cancelled']:
        return Response({'error': f'Cannot cancel an order that is already {order.status}'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Prevent cancellation if food preparation has started
    if order.status in ['approved', 'preparing', 'ready']:
        return Response({'error': 'Cannot cancel order once food preparation has started'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Update order status
    order.status = 'cancelled'
    order.save()
    
    # Create status update
    OrderStatusUpdate.objects.create(
        order=order,
        status='cancelled',
        notes='Order cancelled by customer',
        updated_by=user
    )
    
    return Response({'success': 'Order cancelled successfully'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def track_order(request, order_id):
    """Track the status of an order"""
    user = request.user
    
    if not user.is_customer:
        return Response({'error': 'Only customers can track their orders'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    order = get_object_or_404(Order, id=order_id, customer=user)
    
    data = {
        'id': order.id,
        'status': order.get_status_display(),
        'estimated_preparation_time': order.estimated_preparation_time,
        'created_at': order.created_at,
    }
    
    # Include status updates
    status_history = []
    for update in order.status_updates.all().order_by('created_at'):
        status_history.append({
            'status': update.get_status_display(),
            'timestamp': update.created_at,
            'notes': update.notes
        })
    
    data['status_history'] = status_history
    
    return Response(data, status=status.HTTP_200_OK)


# Staff views

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def staff_order_list(request):
    """Get all orders for a staff member's restaurant"""
    user = request.user
    
    if not user.is_staff_member:
        return Response({'error': 'Only staff members can access this endpoint'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    try:
        staff_profile = user.staff_profile
        restaurant = staff_profile.restaurant
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Filter orders
    status_filter = request.GET.get('status')
    if status_filter:
        orders = Order.objects.filter(restaurant=restaurant, status=status_filter)
    else:
        orders = Order.objects.filter(restaurant=restaurant)
    
    # Sort by most recent first
    orders = orders.order_by('-created_at')
    
    data = []
    for order in orders:
        data.append({
            'id': order.id,
            'customer': order.customer.phone,
            'order_type': order.get_order_type_display(),
            'status': order.get_status_display(),
            'total': order.total,
            'created_at': order.created_at,
            'items_count': order.items.count(),
        })
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def staff_update_order(request, order_id):
    """Update order status by staff"""
    user = request.user
    
    if not user.is_staff_member:
        return Response({'error': 'Only staff members can update orders'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    try:
        staff_profile = user.staff_profile
        restaurant = staff_profile.restaurant
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)
    
    # Get the new status
    new_status = request.data.get('status')
    notes = request.data.get('notes', '')
    
    if not new_status or new_status not in [s[0] for s in Order.STATUS_CHOICES]:
        return Response({'error': 'Valid status is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check permissions based on staff role
    role = staff_profile.role
    
    if role == 'chef':
        # Chef can only approve/reject/preparing/ready
        if new_status not in ['approved', 'rejected', 'preparing', 'ready']:
            return Response({'error': 'Chefs can only approve, reject, mark as preparing, or ready'}, 
                             status=status.HTTP_403_FORBIDDEN)
        
        # Auto-assign chef if approving
        if new_status == 'approved':
            order.assigned_chef = user
    
    elif role == 'waiter':
        # Waiter can only mark as completed
        if new_status not in ['completed']:
            return Response({'error': 'Waiters can only mark orders as completed'}, 
                             status=status.HTTP_403_FORBIDDEN)
        
        # Auto-assign waiter if completing
        order.assigned_waiter = user
    
    elif role == 'manager':
        # Managers can update to any status
        # If approving, assign a chef if none is assigned
        if new_status == 'approved' and not order.assigned_chef:
            # Find an available on-shift chef
            from accounts.models import StaffProfile
            chefs = StaffProfile.objects.filter(
                restaurant=restaurant,
                role='chef',
                is_on_shift=True
            )
            
            if chefs.exists():
                order.assigned_chef = chefs.first().user
            else:
                # If no on-shift chefs, look for any chef
                chefs = StaffProfile.objects.filter(restaurant=restaurant, role='chef')
                if chefs.exists():
                    order.assigned_chef = chefs.first().user
                    return Response({
                        'warning': 'No chefs are currently on shift. Assigned to an off-shift chef.',
                        'chef': order.assigned_chef.phone
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'warning': 'No chefs available for this restaurant.',
                    }, status=status.HTTP_200_OK)
    
    else:
        return Response({'error': f'Unknown staff role: {role}'}, status=status.HTTP_403_FORBIDDEN)
    
    # Update order status
    old_status = order.status
    order.status = new_status
    order.save()
    
    # Create status update for notification
    status_update = OrderStatusUpdate.objects.create(
        order=order,
        status=new_status,
        notes=notes,
        updated_by=user
    )
    
    # Send notification to customer (in a real app, this would trigger a push notification or email)
    # For now, we'll just mark it as a notification that needs to be sent
    status_update.notification_message = f"Your order status has been updated from {old_status} to {new_status}."
    status_update.save()
    
    return Response({
        'success': f'Order status updated to {order.get_status_display()}',
        'notification_sent': True
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chef_orders(request):
    """Get orders relevant to chef (pending, approved, preparing)"""
    user = request.user
    
    if not user.is_staff_member:
        return Response({'error': 'Only staff members can access this endpoint'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    try:
        staff_profile = user.staff_profile
        restaurant = staff_profile.restaurant
        
        if staff_profile.role != 'chef' and staff_profile.role != 'manager':
            return Response({'error': 'Only chefs and managers can access this endpoint'}, 
                             status=status.HTTP_403_FORBIDDEN)
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get orders that need chef attention
    orders = Order.objects.filter(
        restaurant=restaurant,
        status__in=['pending', 'approved', 'preparing']
    ).order_by('created_at')  # Oldest first for FIFO
    
    data = []
    for order in orders:
        # Get order items
        items = []
        for item in order.items.all():
            items.append({
                'name': item.menu_item.name,
                'quantity': item.quantity,
                'special_instructions': item.special_instructions,
                'image': item.menu_item.image.url if item.menu_item.image else None,
            })
        
        data.append({
            'id': order.id,
            'status': order.get_status_display(),
            'order_type': order.get_order_type_display(),
            'created_at': order.created_at,
            'items': items,
            'special_instructions': order.special_instructions,
            'assigned_chef': order.assigned_chef.phone if order.assigned_chef else None,
        })
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def waiter_orders(request):
    """Get orders relevant to waiters (ready orders)"""
    user = request.user
    
    if not user.is_staff_member:
        return Response({'error': 'Only staff members can access this endpoint'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    try:
        staff_profile = user.staff_profile
        restaurant = staff_profile.restaurant
        
        if staff_profile.role != 'waiter' and staff_profile.role != 'manager':
            return Response({'error': 'Only waiters and managers can access this endpoint'}, 
                             status=status.HTTP_403_FORBIDDEN)
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get orders that are ready for delivery/pickup
    orders = Order.objects.filter(
        restaurant=restaurant,
        status='ready'
    ).order_by('created_at')  # Oldest first for FIFO
    
    data = []
    for order in orders:
        data.append({
            'id': order.id,
            'customer': order.customer.phone,
            'order_type': order.get_order_type_display(),
            'created_at': order.created_at,
            'items_count': order.items.count(),
            'table': order.reservation.table.table_number if order.reservation else None,
            'delivery_address': order.delivery_address if order.order_type == 'delivery' else None,
        })
    
    return Response(data, status=status.HTTP_200_OK)
