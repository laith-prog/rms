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
                        'categories': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            )
                        ),
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
        data.append({
            'id': restaurant.id,
            'name': restaurant.name,
            'logo': request.build_absolute_uri(restaurant.logo.url) if restaurant.logo else None,
            'average_rating': restaurant.average_rating,
            'categories': [{'id': cat.id, 'name': cat.name} for cat in restaurant.categories.all()],
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
        'categories': [{'id': cat.id, 'name': cat.name} for cat in restaurant.categories.all()],
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
    
    if not user.is_customer:
        return Response({'error': 'Only customers can make reservations'}, status=status.HTTP_403_FORBIDDEN)
    
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
    
    return Response({
        'success': 'Reservation created successfully',
        'reservation_id': reservation.id
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
