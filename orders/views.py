from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Order, OrderItem, OrderStatusUpdate
from restaurants.models import MenuItem, Restaurant
from accounts.permissions import IsCustomer, IsStaffMember


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCustomer])
def order_list(request):
    """Get list of orders for the authenticated customer."""
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    
    orders_data = []
    for order in orders:
        orders_data.append({
            'id': order.id,
            'restaurant': order.restaurant.name,
            'status': order.status,
            'order_type': order.order_type,
            'total': str(order.total),
            'created_at': order.created_at.isoformat(),
            'estimated_preparation_time': order.estimated_preparation_time,
        })
    
    return Response({'orders': orders_data})


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsCustomer])
def create_order(request):
    """Create a new order."""
    data = request.data
    
    # Validate required fields
    if not data.get('restaurant_id'):
        return Response({
            'detail': 'restaurant_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    items_data = data.get('items', [])
    if not items_data:
        return Response({
            'detail': 'At least one item is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate each item
    for i, item_data in enumerate(items_data):
        # Accept both 'menu_item_id' and 'item_id' for flexibility
        menu_item_id = item_data.get('menu_item_id') or item_data.get('item_id')
        if not menu_item_id:
            return Response({
                'detail': f'menu_item_id (or item_id) is required for item {i + 1}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not item_data.get('quantity') or item_data.get('quantity') <= 0:
            return Response({
                'detail': f'quantity must be greater than 0 for item {i + 1}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            # Get restaurant
            restaurant = get_object_or_404(Restaurant, id=data.get('restaurant_id'), is_active=True)
            
            # Create order
            order = Order.objects.create(
                customer=request.user,
                restaurant=restaurant,
                order_type=data.get('order_type', 'dine_in'),
                special_instructions=data.get('special_instructions', ''),
                delivery_address=data.get('delivery_address', ''),
                subtotal=0,
                tax=0,
                total=0,
                payment_method=data.get('payment_method', 'cash')
            )
            
            # Add order items
            for item_data in items_data:
                # Accept both 'menu_item_id' and 'item_id' for flexibility
                menu_item_id = item_data.get('menu_item_id') or item_data.get('item_id')
                menu_item = get_object_or_404(MenuItem, id=menu_item_id, is_active=True)
                
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=item_data['quantity'],
                    item_price=menu_item.price,
                    special_instructions=item_data.get('special_instructions', '')
                )
            
            # Calculate totals
            order.calculate_total()
            order.calculate_preparation_time()
            order.save()
            
            # Create initial status update
            OrderStatusUpdate.objects.create(
                order=order,
                status='pending',
                notes='Order created',
                updated_by=request.user
            )
            
            return Response({
                'id': order.id,
                'status': order.status,
                'total': str(order.total),
                'estimated_preparation_time': order.estimated_preparation_time,
                'message': 'Order created successfully'
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        return Response({
            'detail': f'Error creating order: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCustomer])
def order_detail(request, order_id):
    """Get detailed information about a specific order."""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    # Get order items
    items = []
    for item in order.items.all():
        items.append({
            'menu_item': item.menu_item.name,
            'quantity': item.quantity,
            'item_price': str(item.item_price),
            'item_total': str(item.item_total),
            'special_instructions': item.special_instructions
        })
    
    # Get status updates
    status_updates = []
    for update in order.status_updates.all().order_by('-created_at'):
        status_updates.append({
            'status': update.status,
            'notes': update.notes,
            'created_at': update.created_at.isoformat(),
            'updated_by': update.updated_by.get_full_name() if update.updated_by else None
        })
    
    order_data = {
        'id': order.id,
        'restaurant': {
            'name': order.restaurant.name,
            'address': order.restaurant.address,
            'phone': order.restaurant.phone
        },
        'status': order.status,
        'order_type': order.order_type,
        'special_instructions': order.special_instructions,
        'subtotal': str(order.subtotal),
        'tax': str(order.tax),
        'delivery_fee': str(order.delivery_fee),
        'total': str(order.total),
        'payment_status': order.payment_status,
        'payment_method': order.payment_method,
        'delivery_address': order.delivery_address,
        'estimated_preparation_time': order.estimated_preparation_time,
        'created_at': order.created_at.isoformat(),
        'items': items,
        'status_updates': status_updates
    }
    
    return Response(order_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsCustomer])
def cancel_order(request, order_id):
    """Cancel an order (only if it's still pending)."""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    if order.status not in ['pending', 'approved']:
        return Response({
            'detail': 'Order cannot be cancelled at this stage'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    order.status = 'cancelled'
    order.save()
    
    # Create status update
    OrderStatusUpdate.objects.create(
        order=order,
        status='cancelled',
        notes='Order cancelled by customer',
        updated_by=request.user
    )
    
    return Response({
        'message': 'Order cancelled successfully',
        'status': order.status
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCustomer])
def track_order(request, order_id):
    """Track order status and estimated time."""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    # Calculate remaining time (simplified)
    remaining_time = None
    if order.status in ['approved', 'preparing'] and order.estimated_preparation_time:
        from django.utils import timezone
        elapsed_minutes = (timezone.now() - order.created_at).total_seconds() / 60
        remaining_time = max(0, order.estimated_preparation_time - elapsed_minutes)
    
    return Response({
        'id': order.id,
        'status': order.status,
        'estimated_preparation_time': order.estimated_preparation_time,
        'remaining_time': remaining_time,
        'last_update': order.updated_at.isoformat()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffMember])
def staff_order_list(request):
    """Get list of orders for staff management."""
    # Filter by restaurant if staff is associated with specific restaurant
    orders = Order.objects.all().order_by('-created_at')
    
    # You might want to filter by restaurant based on staff permissions
    # orders = orders.filter(restaurant=request.user.staff_profile.restaurant)
    
    orders_data = []
    for order in orders:
        orders_data.append({
            'id': order.id,
            'customer': order.customer.get_full_name(),
            'restaurant': order.restaurant.name,
            'status': order.status,
            'order_type': order.order_type,
            'total': str(order.total),
            'created_at': order.created_at.isoformat(),
            'estimated_preparation_time': order.estimated_preparation_time,
        })
    
    return Response({'orders': orders_data})


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStaffMember])
def staff_update_order(request, order_id):
    """Update order status (staff only)."""
    order = get_object_or_404(Order, id=order_id)
    new_status = request.data.get('status')
    notes = request.data.get('notes', '')
    
    if new_status not in dict(Order.STATUS_CHOICES):
        return Response({
            'detail': 'Invalid status'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    order.status = new_status
    order.save()
    
    # Create status update
    OrderStatusUpdate.objects.create(
        order=order,
        status=new_status,
        notes=notes,
        updated_by=request.user
    )
    
    return Response({
        'message': 'Order status updated successfully',
        'status': order.status
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffMember])
def chef_orders(request):
    """Get orders assigned to chef or pending preparation."""
    orders = Order.objects.filter(
        status__in=['approved', 'preparing']
    ).order_by('created_at')
    
    orders_data = []
    for order in orders:
        items = []
        for item in order.items.all():
            items.append({
                'name': item.menu_item.name,
                'quantity': item.quantity,
                'special_instructions': item.special_instructions
            })
        
        orders_data.append({
            'id': order.id,
            'customer': order.customer.get_full_name(),
            'order_type': order.order_type,
            'status': order.status,
            'items': items,
            'special_instructions': order.special_instructions,
            'created_at': order.created_at.isoformat(),
            'estimated_preparation_time': order.estimated_preparation_time,
        })
    
    return Response({'orders': orders_data})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffMember])
def waiter_orders(request):
    """Get orders ready for serving or delivery."""
    orders = Order.objects.filter(
        status__in=['ready', 'completed']
    ).order_by('created_at')
    
    orders_data = []
    for order in orders:
        orders_data.append({
            'id': order.id,
            'customer': order.customer.get_full_name(),
            'order_type': order.order_type,
            'status': order.status,
            'total': str(order.total),
            'delivery_address': order.delivery_address,
            'created_at': order.created_at.isoformat(),
        })
    
    return Response({'orders': orders_data})