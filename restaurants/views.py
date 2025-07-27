from django.shortcuts import render, get_object_or_404
from django.db.models import Avg
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Restaurant, Category, MenuItem, Table, Reservation, Review
from accounts.models import User, StaffProfile
from accounts.permissions import IsSuperAdmin, IsRestaurantManager, IsWaiterOrChef, IsCustomer, IsStaffMember, IsRestaurantStaff
from orders.models import Order, OrderItem, OrderStatusUpdate


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('category_id', openapi.IN_QUERY, description="Filter by category ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('min_rating', openapi.IN_QUERY, description="Filter by minimum rating", type=openapi.TYPE_NUMBER),
        openapi.Parameter('search', openapi.IN_QUERY, description="Search by restaurant name", type=openapi.TYPE_STRING),
    ],
    responses={
        200: openapi.Response(
            description="List of restaurants",
            schema=openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'name': openapi.Schema(type=openapi.TYPE_STRING),
                        'logo': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                        'average_rating': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'category': openapi.Schema(type=openapi.TYPE_STRING),
                        'address': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        )
    },
    operation_description="List all restaurants with optional filtering"
)
@api_view(['GET'])
@permission_classes([AllowAny])
def restaurant_list(request):
    """
    List all restaurants, can be filtered by category, rating, etc.
    
    Returns a list of restaurants with basic information. The list can be filtered by:
    - category_id: Filter by specific food category
    - min_rating: Filter by minimum rating (1-5)
    - search: Search by restaurant name
    """
    restaurants = Restaurant.objects.filter(is_active=True)
    
    # Filter by category if provided
    category_id = request.GET.get('category_id')
    if category_id:
        restaurants = restaurants.filter(categories__id=category_id)
    
    # Filter by minimum rating if provided
    min_rating = request.GET.get('min_rating')
    if min_rating:
        restaurants = restaurants.filter(average_rating__gte=float(min_rating))
    
    # Search by name if provided
    search = request.GET.get('search')
    if search:
        restaurants = restaurants.filter(name__icontains=search)
    
    # Basic restaurant information for listing
    data = []
    for restaurant in restaurants:
        # Get primary category as string
        primary_category = restaurant.categories.first().name if restaurant.categories.exists() else ""
        
        data.append({
            'id': restaurant.id,
            'name': restaurant.name,
            'logo': request.build_absolute_uri(restaurant.logo.url) if restaurant.logo else None,
            'average_rating': restaurant.average_rating,
            'category': primary_category,
            'address': restaurant.address,
        })
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def category_list(request):
    """List all food categories"""
    categories = Category.objects.filter(is_active=True)
    
    data = []
    for category in categories:
        data.append({
            'id': category.id,
            'name': category.name,
            'image': request.build_absolute_uri(category.image.url) if category.image else None,
            'description': category.description,
        })
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def restaurant_detail(request, restaurant_id):
    """Get detailed information about a restaurant"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    
    # Get restaurant images
    images = []
    for img in restaurant.images.filter(is_active=True):
        images.append({
            'id': img.id,
            'image': request.build_absolute_uri(img.image.url),
            'caption': img.caption
        })
    
    # Get primary category as string
    primary_category = restaurant.categories.first().name if restaurant.categories.exists() else ""
    
    data = {
        'id': restaurant.id,
        'name': restaurant.name,
        'address': restaurant.address,
        'phone': restaurant.phone,
        'email': restaurant.email,
        'logo': request.build_absolute_uri(restaurant.logo.url) if restaurant.logo else None,
        'cover_image': request.build_absolute_uri(restaurant.cover_image.url) if restaurant.cover_image else None,
        'description': restaurant.description,
        'opening_time': restaurant.opening_time,
        'closing_time': restaurant.closing_time,
        'average_rating': restaurant.average_rating,
        'category': primary_category,  # Return primary category as string
        'images': images,
        'services': {
            'dine_in': restaurant.offers_dine_in,
            'takeaway': restaurant.offers_takeaway,
            'delivery': restaurant.offers_delivery,
        }
    }
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def restaurant_menu(request, restaurant_id):
    """Get menu items for a restaurant"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    menu_items = MenuItem.objects.filter(restaurant=restaurant, is_active=True)
    
    data = []
    for item in menu_items:
        data.append({
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'price': item.price,
            'image': request.build_absolute_uri(item.image.url) if item.image else None,
            'dietary_info': {
                'vegetarian': item.is_vegetarian,
                'vegan': item.is_vegan,
                'gluten_free': item.is_gluten_free,
                'contains_nuts': item.contains_nuts,
                'contains_dairy': item.contains_dairy,
                'spicy': item.is_spicy,
            },
            'preparation_time': item.preparation_time,
        })
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def restaurant_reviews(request, restaurant_id):
    """Get reviews for a restaurant"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    reviews = Review.objects.filter(restaurant=restaurant).order_by('-created_at')
    
    data = []
    for review in reviews:
        data.append({
            'id': review.id,
            'customer': review.customer.phone,  # Just showing the phone for privacy
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.created_at,
        })
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def available_tables(request, restaurant_id):
    """Get available tables for a restaurant on a specific date and time"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    
    # Get date from query parameters (default to today)
    date_str = request.GET.get('date', None)
    if date_str:
        try:
            reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format, use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        reservation_date = timezone.now().date()
    
    # Get time from query parameters (default to now)
    time_str = request.GET.get('time', None)
    if time_str:
        try:
            reservation_time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            return Response({'error': 'Invalid time format, use HH:MM'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        reservation_time = timezone.now().time()
    
    # Get party size (default to 2)
    party_size = int(request.GET.get('party_size', 2))
    
    # Find tables that are big enough and not reserved at the requested time
    tables = Table.objects.filter(
        restaurant=restaurant,
        is_active=True,
        capacity__gte=party_size
    )
    
    # Exclude tables that are already reserved at this time
    reserved_table_ids = Reservation.objects.filter(
        restaurant=restaurant,
        reservation_date=reservation_date,
        status__in=['pending', 'confirmed'],
        table__in=tables
    ).values_list('table_id', flat=True)
    
    available_tables = tables.exclude(id__in=reserved_table_ids)
    
    data = []
    for table in available_tables:
        data.append({
            'id': table.id,
            'table_number': table.table_number,
            'capacity': table.capacity,
        })
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_reservation(request, restaurant_id):
    """Create a new reservation"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    user = request.user
    
    # Allow customers, waiters, and managers to make reservations, but not chefs
    if user.is_customer:
        # Customers can make reservations
        pass
    elif user.is_staff_member:
        try:
            staff_profile = user.staff_profile
            # Ensure staff belongs to this restaurant
            if staff_profile.restaurant.id != restaurant.id:
                return Response({'error': 'Staff can only make reservations at their own restaurant'}, 
                               status=status.HTTP_403_FORBIDDEN)
            
            # Chefs cannot make reservations
            if staff_profile.role == 'chef':
                return Response({'error': 'Chefs are not allowed to make reservations'}, 
                               status=status.HTTP_403_FORBIDDEN)
        except:
            return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    else:
        return Response({'error': 'Only customers, waiters, or managers can make reservations'}, 
                        status=status.HTTP_403_FORBIDDEN)
    
    # Get reservation details
    table_id = request.data.get('table_id')
    if not table_id:
        return Response({'error': 'Table ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    
    party_size = request.data.get('party_size')
    if not party_size:
        return Response({'error': 'Party size is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if table capacity is sufficient
    if int(party_size) > table.capacity:
        return Response({'error': 'Table capacity is not sufficient for your party size'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Get date and time
    date_str = request.data.get('date')
    time_str = request.data.get('time')
    
    try:
        reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        reservation_time = datetime.strptime(time_str, '%H:%M').time()
    except (ValueError, TypeError):
        return Response({'error': 'Invalid date or time format'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if date is in the past
    if reservation_date < timezone.now().date():
        return Response({'error': 'Cannot make reservation for past date'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if table is already reserved
    if Reservation.objects.filter(
            table=table,
            reservation_date=reservation_date,
            status__in=['pending', 'confirmed']).exists():
        return Response({'error': 'This table is already reserved for the selected time'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Create the reservation
    reservation = Reservation.objects.create(
        customer=user,
        restaurant=restaurant,
        table=table,
        party_size=party_size,
        reservation_date=reservation_date,
        reservation_time=reservation_time,
        status='pending',
        special_requests=request.data.get('special_requests', '')
    )
    
    # Auto-approve if the user is a manager
    if user.is_staff_member and user.staff_profile.role == 'manager':
        reservation.status = 'confirmed'
        reservation.save()
        
        # Create notification for auto-approval
        ReservationStatusUpdate.objects.create(
            reservation=reservation,
            status='confirmed',
            notes='Auto-approved by manager',
            updated_by=user
        )
    
    return Response({
        'success': 'Reservation created successfully',
        'reservation_id': reservation.id,
        'status': reservation.status
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_reservations(request):
    """Get all reservations for the current user"""
    user = request.user
    
    if not user.is_customer:
        return Response({'error': 'Only customers can view their reservations'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    reservations = Reservation.objects.filter(customer=user).order_by('-reservation_date', '-reservation_time')
    
    data = []
    for reservation in reservations:
        data.append({
            'id': reservation.id,
            'restaurant': {
                'id': reservation.restaurant.id,
                'name': reservation.restaurant.name,
                'address': reservation.restaurant.address,
            },
            'table': reservation.table.table_number,
            'party_size': reservation.party_size,
            'date': reservation.reservation_date,
            'time': reservation.reservation_time,
            'status': reservation.status,
            'created_at': reservation.created_at,
        })
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reservation_detail(request, reservation_id):
    """Get details of a specific reservation"""
    user = request.user
    
    if user.is_customer:
        # Customers can only view their own reservations
        reservation = get_object_or_404(Reservation, id=reservation_id, customer=user)
    elif user.is_staff_member:
        # Staff can view any reservation in their restaurant
        try:
            staff_profile = user.staff_profile
            reservation = get_object_or_404(
                Reservation, 
                id=reservation_id,
                restaurant=staff_profile.restaurant
            )
        except:
            return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    else:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    data = {
        'id': reservation.id,
        'restaurant': {
            'id': reservation.restaurant.id,
            'name': reservation.restaurant.name,
            'address': reservation.restaurant.address,
            'phone': reservation.restaurant.phone,
        },
        'customer': {
            'phone': reservation.customer.phone,
        },
        'table': {
            'id': reservation.table.id,
            'table_number': reservation.table.table_number,
            'capacity': reservation.table.capacity,
        },
        'party_size': reservation.party_size,
        'date': reservation.reservation_date,
        'time': reservation.reservation_time,
        'status': reservation.status,
        'special_requests': reservation.special_requests,
        'created_at': reservation.created_at,
        'updated_at': reservation.updated_at,
    }
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_reservation(request, reservation_id):
    """Cancel a reservation"""
    user = request.user
    
    if not user.is_customer:
        return Response({'error': 'Only customers can cancel their reservations'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    reservation = get_object_or_404(Reservation, id=reservation_id, customer=user)
    
    # Check if reservation can be cancelled (not in the past, not already cancelled)
    if reservation.reservation_date < timezone.now().date():
        return Response({'error': 'Cannot cancel past reservations'}, status=status.HTTP_400_BAD_REQUEST)
    
    if reservation.status == 'cancelled':
        return Response({'error': 'Reservation is already cancelled'}, status=status.HTTP_400_BAD_REQUEST)
    
    if reservation.status == 'completed':
        return Response({'error': 'Cannot cancel completed reservations'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Cancel the reservation
    reservation.status = 'cancelled'
    reservation.save()
    
    return Response({'success': 'Reservation cancelled successfully'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_reservation_status(request, reservation_id):
    """Update reservation status (for managers)"""
    user = request.user
    
    if not user.is_staff_member:
        return Response({'error': 'Only staff members can update reservations'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    try:
        staff_profile = user.staff_profile
        role = staff_profile.role
        restaurant = staff_profile.restaurant
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Only managers can confirm/reject reservations
    if role != 'manager':
        return Response({'error': 'Only managers can update reservation status'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    # Get the reservation
    reservation = get_object_or_404(Reservation, id=reservation_id, restaurant=restaurant)
    
    # Get the new status
    new_status = request.data.get('status')
    notes = request.data.get('notes', '')
    
    if not new_status or new_status not in [s[0] for s in Reservation.STATUS_CHOICES]:
        return Response({'error': 'Valid status is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Update reservation status
    reservation.status = new_status
    reservation.save()
    
    # Create status update for notification
    ReservationStatusUpdate.objects.create(
        reservation=reservation,
        status=new_status,
        notes=notes,
        updated_by=user
    )
    
    return Response({
        'success': f'Reservation status updated to {reservation.get_status_display()}',
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def restaurant_dashboard(request):
    """Get restaurant dashboard data for managers"""
    user = request.user
    
    if not user.is_staff_member:
        return Response({'error': 'Only staff members can access the dashboard'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    try:
        staff_profile = user.staff_profile
        role = staff_profile.role
        restaurant = staff_profile.restaurant
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Only managers can access the full dashboard
    if role != 'manager' and not user.is_superuser:
        return Response({'error': 'Only managers can access the full dashboard'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    # Get pending reservations
    pending_reservations = Reservation.objects.filter(
        restaurant=restaurant,
        status='pending'
    ).order_by('reservation_date', 'reservation_time')
    
    pending_reservations_data = []
    for reservation in pending_reservations:
        pending_reservations_data.append({
            'id': reservation.id,
            'customer': reservation.customer.phone,
            'table': reservation.table.table_number,
            'party_size': reservation.party_size,
            'date': reservation.reservation_date,
            'time': reservation.reservation_time,
            'special_requests': reservation.special_requests,
        })
    
    # Get pending orders
    from orders.models import Order
    pending_orders = Order.objects.filter(
        restaurant=restaurant,
        status='pending'
    ).order_by('created_at')
    
    pending_orders_data = []
    for order in pending_orders:
        pending_orders_data.append({
            'id': order.id,
            'customer': order.customer.phone,
            'order_type': order.get_order_type_display(),
            'created_at': order.created_at,
            'items_count': order.items.count(),
        })
    
    # Get restaurant stats
    today = timezone.now().date()
    today_reservations_count = Reservation.objects.filter(
        restaurant=restaurant,
        reservation_date=today,
        status__in=['confirmed', 'completed']
    ).count()
    
    today_orders_count = Order.objects.filter(
        restaurant=restaurant,
        created_at__date=today,
        status__in=['approved', 'preparing', 'ready', 'completed']
    ).count()
    
    # Get staff information
    staff = staff_profile.restaurant.staff.all()
    staff_data = []
    for staff_member in staff:
        staff_data.append({
            'id': staff_member.user.id,
            'name': f"{staff_member.user.first_name} {staff_member.user.last_name}",
            'phone': staff_member.user.phone,
            'role': staff_member.get_role_display(),
        })
    
    # Get restaurant information
    restaurant_data = {
        'id': restaurant.id,
        'name': restaurant.name,
        'address': restaurant.address,
        'phone': restaurant.phone,
        'cuisine': restaurant.cuisine.name if restaurant.cuisine else None,
        'opening_time': restaurant.opening_time,
        'closing_time': restaurant.closing_time,
        'is_active': restaurant.is_active,
    }
    
    # Get recent notifications (status updates)
    recent_reservation_updates = ReservationStatusUpdate.objects.filter(
        reservation__restaurant=restaurant
    ).order_by('-created_at')[:10]
    
    reservation_notifications = []
    for update in recent_reservation_updates:
        reservation_notifications.append({
            'id': update.id,
            'reservation_id': update.reservation.id,
            'status': update.get_status_display(),
            'notes': update.notes,
            'updated_by': update.updated_by.phone if update.updated_by else 'System',
            'created_at': update.created_at,
        })
    
    from orders.models import OrderStatusUpdate
    recent_order_updates = OrderStatusUpdate.objects.filter(
        order__restaurant=restaurant
    ).order_by('-created_at')[:10]
    
    order_notifications = []
    for update in recent_order_updates:
        order_notifications.append({
            'id': update.id,
            'order_id': update.order.id,
            'status': update.get_status_display(),
            'notes': update.notes,
            'updated_by': update.updated_by.phone if update.updated_by else 'System',
            'created_at': update.created_at,
        })
    
    return Response({
        'restaurant': restaurant_data,
        'stats': {
            'today_reservations': today_reservations_count,
            'today_orders': today_orders_count,
            'pending_reservations': pending_reservations.count(),
            'pending_orders': pending_orders.count(),
        },
        'pending_reservations': pending_reservations_data,
        'pending_orders': pending_orders_data,
        'staff': staff_data,
        'notifications': {
            'reservation_updates': reservation_notifications,
            'order_updates': order_notifications,
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_restaurant_with_manager(request):
    """Create a new restaurant with a manager (superuser only)"""
    user = request.user
    
    # Only superusers can create restaurants
    if not user.is_superuser:
        return Response({'error': 'Only superusers can create restaurants'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    # Get restaurant details
    restaurant_data = {
        'name': request.data.get('name'),
        'address': request.data.get('address'),
        'phone': request.data.get('phone'),
        'email': request.data.get('email'),
        'description': request.data.get('description'),
        'opening_time': request.data.get('opening_time'),
        'closing_time': request.data.get('closing_time'),
    }
    
    # Validate required fields
    required_fields = ['name', 'address', 'phone', 'opening_time', 'closing_time']
    missing_fields = [field for field in required_fields if not restaurant_data.get(field)]
    if missing_fields:
        return Response({'error': f'Missing required fields: {", ".join(missing_fields)}'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Get manager details
    manager_data = {
        'phone': request.data.get('manager_phone'),
        'password': request.data.get('manager_password'),
        'first_name': request.data.get('manager_first_name'),
        'last_name': request.data.get('manager_last_name'),
    }
    
    # Validate required fields
    required_fields = ['phone', 'password', 'first_name', 'last_name']
    missing_fields = [field for field in required_fields if not manager_data.get(field)]
    if missing_fields:
        return Response({'error': f'Missing required manager fields: {", ".join(missing_fields)}'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Check if manager phone already exists
    if User.objects.filter(phone=manager_data['phone']).exists():
        return Response({'error': 'Manager phone number already exists'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Create restaurant
    restaurant = Restaurant.objects.create(
        name=restaurant_data['name'],
        address=restaurant_data['address'],
        phone=restaurant_data['phone'],
        email=restaurant_data.get('email', ''),
        description=restaurant_data.get('description', ''),
        opening_time=restaurant_data['opening_time'],
        closing_time=restaurant_data['closing_time'],
    )
    
    # Add categories if provided
    categories = request.data.get('categories', [])
    if categories:
        for category_id in categories:
            try:
                category = Category.objects.get(id=category_id)
                restaurant.categories.add(category)
            except Category.DoesNotExist:
                pass
    
    # Set service options if provided
    restaurant.offers_dine_in = request.data.get('offers_dine_in', True)
    restaurant.offers_takeaway = request.data.get('offers_takeaway', True)
    restaurant.offers_delivery = request.data.get('offers_delivery', False)
    restaurant.save()
    
    # Create manager user
    manager_user = User.objects.create_user(
        phone=manager_data['phone'],
        password=manager_data['password'],
        first_name=manager_data['first_name'],
        last_name=manager_data['last_name'],
        is_staff_member=True,
        is_phone_verified=True
    )
    
    # Create manager profile
    manager_profile = StaffProfile.objects.create(
        user=manager_user,
        role='manager',
        restaurant=restaurant
    )
    
    return Response({
        'success': 'Restaurant and manager created successfully',
        'restaurant': {
            'id': restaurant.id,
            'name': restaurant.name,
        },
        'manager': {
            'id': manager_user.id,
            'name': f"{manager_user.first_name} {manager_user.last_name}",
            'phone': manager_user.phone,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def create_restaurant_category(request):
    """Create a new food category (superuser only)"""
    name = request.data.get('name')
    if not name:
        return Response({'error': 'Category name is required'}, 
                        status=status.HTTP_400_BAD_REQUEST)
    
    description = request.data.get('description', '')
    
    # Create the category
    category = Category.objects.create(
        name=name,
        description=description,
        is_active=True
    )
    
    # Handle image upload if provided
    if 'image' in request.FILES:
        category.image = request.FILES['image']
        category.save()
    
    return Response({
        'success': 'Category created successfully',
        'category': {
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'image': request.build_absolute_uri(category.image.url) if category.image else None,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsRestaurantManager])
def create_menu_item(request):
    """Create a new menu item (manager only)"""
    user = request.user
    
    try:
        staff_profile = user.staff_profile
        restaurant = staff_profile.restaurant
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get menu item details
    name = request.data.get('name')
    description = request.data.get('description', '')
    price = request.data.get('price')
    
    # Validate required fields
    if not name or not price:
        return Response({'error': 'Name and price are required'}, 
                        status=status.HTTP_400_BAD_REQUEST)
    
    # Create menu item
    menu_item = MenuItem.objects.create(
        restaurant=restaurant,
        name=name,
        description=description,
        price=price,
        is_vegetarian=request.data.get('is_vegetarian', False),
        is_vegan=request.data.get('is_vegan', False),
        is_gluten_free=request.data.get('is_gluten_free', False),
        contains_nuts=request.data.get('contains_nuts', False),
        contains_dairy=request.data.get('contains_dairy', False),
        is_spicy=request.data.get('is_spicy', False),
        preparation_time=request.data.get('preparation_time', 15),
        is_active=True
    )
    
    # Handle image upload if provided
    if 'image' in request.FILES:
        menu_item.image = request.FILES['image']
        menu_item.save()
    
    return Response({
        'success': 'Menu item created successfully',
        'menu_item': {
            'id': menu_item.id,
            'name': menu_item.name,
            'price': menu_item.price,
            'description': menu_item.description,
            'image': request.build_absolute_uri(menu_item.image.url) if menu_item.image else None,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsRestaurantManager])
def add_category_to_restaurant(request):
    """Add existing food category to restaurant (manager only)"""
    user = request.user
    
    try:
        staff_profile = user.staff_profile
        restaurant = staff_profile.restaurant
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get category ID
    category_id = request.data.get('category_id')
    if not category_id:
        return Response({'error': 'Category ID is required'}, 
                        status=status.HTTP_400_BAD_REQUEST)
    
    # Add category to restaurant
    try:
        category = Category.objects.get(id=category_id, is_active=True)
        restaurant.categories.add(category)
        return Response({
            'success': f'Category "{category.name}" added to restaurant successfully',
        }, status=status.HTTP_200_OK)
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, 
                        status=status.HTTP_404_NOT_FOUND)


# Staff Views for Waiters and Chefs

@api_view(['GET'])
@permission_classes([IsWaiterOrChef])
def staff_dashboard(request):
    """Dashboard for staff (waiters and chefs)"""
    user = request.user
    
    try:
        staff_profile = user.staff_profile
        restaurant = staff_profile.restaurant
        role = staff_profile.role
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Different data based on role
    if role == 'waiter':
        # Get active reservations for today
        from datetime import datetime, timedelta
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        reservations = Reservation.objects.filter(
            restaurant=restaurant,
            reservation_date__gte=today,
            reservation_date__lt=tomorrow,
            status__in=['confirmed', 'checked_in']
        ).order_by('reservation_time')
        
        # Get active orders
        from orders.models import Order
        orders = Order.objects.filter(
            restaurant=restaurant,
            status__in=['pending', 'approved', 'preparing', 'ready'],
            created_at__gte=datetime.now() - timedelta(days=1)
        ).order_by('-created_at')
        
        # Format reservation data
        reservation_data = []
        for reservation in reservations:
            reservation_data.append({
                'id': reservation.id,
                'customer': f"{reservation.customer.first_name} {reservation.customer.last_name}" if reservation.customer.first_name else reservation.customer.phone,
                'time': reservation.reservation_time.strftime('%H:%M'),
                'party_size': reservation.party_size,
                'table': reservation.table.name if reservation.table else 'Not assigned',
                'status': reservation.status,
            })
        
        # Format order data
        order_data = []
        for order in orders:
            order_data.append({
                'id': order.id,
                'customer': f"{order.customer.first_name} {order.customer.last_name}" if order.customer.first_name else order.customer.phone,
                'total': order.total,
                'status': order.status,
                'time': order.created_at.strftime('%H:%M'),
                'type': order.order_type,
            })
        
        data = {
            'reservations': reservation_data,
            'orders': order_data,
        }
        
    elif role == 'chef':
        # Only need active orders for chefs
        from orders.models import Order
        from datetime import datetime, timedelta
        
        orders = Order.objects.filter(
            restaurant=restaurant,
            status__in=['approved', 'preparing'],
            created_at__gte=datetime.now() - timedelta(days=1)
        ).order_by('-created_at')
        
        # Format order data with items
        order_data = []
        for order in orders:
            items = []
            for item in order.items.all():
                items.append({
                    'name': item.menu_item.name,
                    'quantity': item.quantity,
                    'special_instructions': item.special_instructions,
                })
            
            order_data.append({
                'id': order.id,
                'status': order.status,
                'time': order.created_at.strftime('%H:%M'),
                'items': items,
                'special_instructions': order.special_instructions,
            })
        
        data = {
            'orders': order_data,
        }
    
    else:
        # Unsupported role
        return Response({'error': f'Unsupported role: {role}'}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsWaiterOrChef])
def staff_shifts(request):
    """View upcoming shifts for staff"""
    user = request.user
    
    try:
        staff_profile = user.staff_profile
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get upcoming shifts
    from datetime import datetime
    now = datetime.now()
    
    from accounts.models import StaffShift
    shifts = StaffShift.objects.filter(
        staff=staff_profile,
        end_time__gte=now,
        is_active=True
    ).order_by('start_time')
    
    # Format shift data
    shift_data = []
    for shift in shifts:
        shift_data.append({
            'id': shift.id,
            'start_time': shift.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': shift.end_time.strftime('%Y-%m-%d %H:%M'),
            'created_by': f"{shift.created_by.first_name} {shift.created_by.last_name}" if shift.created_by else "System",
        })
    
    return Response(shift_data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsWaiterOrChef])
def update_order_status(request, order_id):
    """Update order status (waiters and chefs)"""
    user = request.user
    
    try:
        staff_profile = user.staff_profile
        restaurant = staff_profile.restaurant
        role = staff_profile.role
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get order
    from orders.models import Order, OrderStatusUpdate
    try:
        order = Order.objects.get(id=order_id, restaurant=restaurant)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get new status
    new_status = request.data.get('status')
    if not new_status:
        return Response({'error': 'New status is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate status based on role
    if role == 'waiter':
        valid_statuses = ['pending', 'approved', 'completed', 'cancelled']
    elif role == 'chef':
        valid_statuses = ['approved', 'preparing', 'ready', 'rejected']
    else:
        return Response({'error': f'Unsupported role: {role}'}, status=status.HTTP_400_BAD_REQUEST)
    
    if new_status not in valid_statuses:
        return Response({'error': f'Invalid status for {role}. Valid statuses: {", ".join(valid_statuses)}'}, 
                        status=status.HTTP_400_BAD_REQUEST)
    
    # Update order status
    order.status = new_status
    order.save()
    
    # Create status update record
    notes = request.data.get('notes', '')
    OrderStatusUpdate.objects.create(
        order=order,
        status=new_status,
        notes=notes,
        updated_by=user
    )
    
    return Response({
        'success': f'Order status updated to {new_status}',
        'order_id': order.id,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsWaiterOrChef])
def analytics_dashboard(request):
    """Basic analytics dashboard for staff"""
    user = request.user
    
    try:
        staff_profile = user.staff_profile
        restaurant = staff_profile.restaurant
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get analytics data
    from orders.models import Order
    from datetime import datetime, timedelta
    
    # Get time range from request or default to last 7 days
    days = int(request.GET.get('days', 7))
    if days > 30:  # Limit to 30 days for performance
        days = 30
    
    start_date = datetime.now() - timedelta(days=days)
    
    # Get orders in time range
    orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__gte=start_date,
        status__in=['completed', 'paid']  # Only count completed orders
    )
    
    # Calculate basic stats
    total_orders = orders.count()
    total_sales = sum(order.total for order in orders)
    
    # Order types breakdown
    dine_in_count = orders.filter(order_type='dine_in').count()
    pickup_count = orders.filter(order_type='pickup').count()
    delivery_count = orders.filter(order_type='delivery').count()
    
    # Popular items
    from django.db.models import Sum, Count
    from orders.models import OrderItem
    
    popular_items = OrderItem.objects.filter(
        order__in=orders
    ).values(
        'menu_item__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        order_count=Count('order', distinct=True)
    ).order_by('-total_quantity')[:5]
    
    popular_items_data = []
    for item in popular_items:
        popular_items_data.append({
            'name': item['menu_item__name'],
            'total_quantity': item['total_quantity'],
            'order_count': item['order_count'],
        })
    
    # Daily sales
    daily_sales = []
    for i in range(days):
        day = datetime.now() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        day_orders = orders.filter(created_at__gte=day_start, created_at__lte=day_end)
        daily_sales.append({
            'date': day.strftime('%Y-%m-%d'),
            'sales': sum(order.total for order in day_orders),
            'count': day_orders.count(),
        })
    
    # Return analytics data
    return Response({
        'total_orders': total_orders,
        'total_sales': total_sales,
        'order_types': {
            'dine_in': dine_in_count,
            'pickup': pickup_count,
            'delivery': delivery_count,
        },
        'popular_items': popular_items_data,
        'daily_sales': daily_sales,
    }, status=status.HTTP_200_OK)
