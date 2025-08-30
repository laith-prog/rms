from django.shortcuts import render, get_object_or_404
from django.db.models import Avg, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import pytz

from .models import Restaurant, Category, MenuItem, Table, Reservation, Review, ReservationStatusUpdate
from accounts.models import User, StaffProfile
from accounts.permissions import IsSuperAdmin, IsRestaurantManager, IsWaiterOrChef, IsCustomer, IsStaffMember, IsRestaurantStaff
from orders.models import Order, OrderItem, OrderStatusUpdate
from ai.services import AIService
from ai.models import TableSelectionLog
import time

# Helper: mark expired reservations as completed

def _mark_expired_reservations():
    """Automatically complete reservations whose end time has passed."""
    now = timezone.now()
    try:
        pending_or_confirmed = Reservation.objects.filter(status__in=['pending', 'confirmed'])
        for r in pending_or_confirmed:
            end_dt = datetime.combine(r.reservation_date, r.reservation_time) + timedelta(hours=r.duration_hours)
            # Make aware using current timezone for comparison
            end_dt = timezone.make_aware(end_dt, timezone.get_current_timezone())
            if end_dt <= now:
                r.status = 'completed'
                r.save(update_fields=['status'])
    except Exception:
        # Fail-safe: never break main flow due to auto-complete
        pass


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


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('restaurant_id', openapi.IN_PATH, description="Restaurant ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('date', openapi.IN_QUERY, description="Date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
        openapi.Parameter('time', openapi.IN_QUERY, description="Time (HH:MM)", type=openapi.TYPE_STRING),
        openapi.Parameter('party_size', openapi.IN_QUERY, description="Number of guests (default: 2)", type=openapi.TYPE_INTEGER),
        openapi.Parameter('duration', openapi.IN_QUERY, description="Duration in hours (default: 2)", type=openapi.TYPE_INTEGER),
    ],
    responses={
        200: openapi.Response(
            description="Available tables for the specified time slot",
            schema=openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'table_number': openapi.Schema(type=openapi.TYPE_STRING),
                        'capacity': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            )
        )
    },
    operation_description="Get available tables for a specific date, time, party size, and duration"
)
@api_view(['GET'])
@permission_classes([AllowAny])
def available_tables(request, restaurant_id):
    # Auto-complete any past reservations before computing availability
    _mark_expired_reservations()
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
    
    # Get duration (default to 2 hours)
    duration = int(request.GET.get('duration', 2))
    
    # Find tables that are big enough and not reserved at the requested time
    tables = Table.objects.filter(
        restaurant=restaurant,
        is_active=True,
        capacity__gte=party_size
    )
    
    # Calculate end time based on duration
    reservation_datetime = datetime.combine(reservation_date, reservation_time)
    end_datetime = reservation_datetime + timedelta(hours=duration)
    end_time = end_datetime.time()
    
    # Exclude tables that are already reserved during the requested time period
    # We need to check for overlapping reservations considering duration
    reserved_table_ids = []
    
    for table in tables:
        # Get all reservations for this table on the requested date
        existing_reservations = Reservation.objects.filter(
            restaurant=restaurant,
            reservation_date=reservation_date,
            status__in=['pending', 'confirmed'],
            table=table
        )
        
        # Check if any existing reservation overlaps with our requested time slot
        for reservation in existing_reservations:
            existing_start = reservation.reservation_time
            existing_duration = getattr(reservation, 'duration_hours', 2)  # Default to 2 hours if not set
            existing_end_datetime = datetime.combine(reservation_date, existing_start) + timedelta(hours=existing_duration)
            existing_end = existing_end_datetime.time()
            
            # Check for overlap: new reservation overlaps if it starts before existing ends and ends after existing starts
            if (reservation_time < existing_end and end_time > existing_start):
                reserved_table_ids.append(table.id)
                break
    
    available_tables = tables.exclude(id__in=reserved_table_ids)
    
    data = []
    for table in available_tables:
        data.append({
            'id': table.id,
            'table_number': table.table_number,
            'capacity': table.capacity,
        })
    
    return Response(data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['party_size', 'date', 'time'],
        properties={
            'selection_type': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Reservation type: 'customized' (user selects table) or 'smart' (AI-powered table selection with random fallback)",
                enum=['customized', 'smart'],
                default='customized'
            ),
            'table_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="Table ID (required if selection_type='customized')"),
            'party_size': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of guests"),
            'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description="Reservation date (YYYY-MM-DD)"),
            'time': openapi.Schema(type=openapi.TYPE_STRING, description="Reservation time (HH:MM)"),
            'duration_hours': openapi.Schema(type=openapi.TYPE_INTEGER, default=1, description="Duration in hours (default: 1)"),
            'special_requests': openapi.Schema(type=openapi.TYPE_STRING, description="Special requests (optional)"),
            'special_occasion': openapi.Schema(type=openapi.TYPE_STRING, description="Special occasion (e.g., birthday, anniversary) for AI table selection"),
            'user_preferences': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description="User preferences for AI table selection (e.g., {'quiet_area': True, 'window_seat': True})"
            ),
        }
    ),
    responses={
        201: openapi.Response(
            description="Reservation created successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_STRING),
                    'reservation': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                            'selection_type': openapi.Schema(type=openapi.TYPE_STRING),
                            'date': openapi.Schema(type=openapi.TYPE_STRING),
                            'time': openapi.Schema(type=openapi.TYPE_STRING),
                            'duration_hours': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'party_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'table': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'number': openapi.Schema(type=openapi.TYPE_STRING),
                                    'capacity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                }
                            ),
                            'special_requests': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    ),
                    'ai_selection': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        description="AI selection information (only present when selection_type='smart')",
                        properties={
                            'method': openapi.Schema(type=openapi.TYPE_STRING, description="'ai' or 'fallback'"),
                            'reasoning': openapi.Schema(type=openapi.TYPE_STRING, description="AI reasoning for table selection"),
                            'confidence': openapi.Schema(type=openapi.TYPE_NUMBER, description="AI confidence score (0-1)"),
                            'response_time_ms': openapi.Schema(type=openapi.TYPE_INTEGER, description="AI response time in milliseconds"),
                            'factors_considered': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(type=openapi.TYPE_STRING),
                                description="Factors considered by AI"
                            ),
                            'alternative_table_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="Alternative table suggested by AI (optional)")
                        }
                    )
                }
            )
        ),
        400: openapi.Response(description="Bad request - validation errors"),
        403: openapi.Response(description="Forbidden - insufficient permissions"),
        404: openapi.Response(description="Restaurant or table not found"),
    },
    operation_description="Create a new table reservation with two modes: 'customized' (user selects table) or 'smart' (AI-powered intelligent table selection with random fallback)."
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_reservation(request, restaurant_id):
    """Create a new reservation (customized or smart AI-powered selection)."""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    user = request.user
    
    # Allow customers, waiters, and managers to make reservations, but not chefs
    if user.is_customer:
        pass
    elif user.is_staff_member:
        try:
            staff_profile = user.staff_profile
            if staff_profile.restaurant.id != restaurant.id:
                return Response({'error': 'Staff can only make reservations at their own restaurant'}, status=status.HTTP_403_FORBIDDEN)
            if staff_profile.role == 'chef':
                return Response({'error': 'Chefs are not allowed to make reservations'}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    else:
        return Response({'error': 'Only customers, waiters, or managers can make reservations'}, status=status.HTTP_403_FORBIDDEN)

    selection_type = request.data.get('selection_type', 'customized')

    # Common fields
    party_size = request.data.get('party_size')
    if not party_size:
        return Response({'error': 'Party size is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        party_size = int(party_size)
        if party_size < 1:
            return Response({'error': 'Party size must be at least 1'}, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({'error': 'Invalid party size'}, status=status.HTTP_400_BAD_REQUEST)

    date_str = request.data.get('date')
    time_str = request.data.get('time')
    try:
        reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        reservation_time = datetime.strptime(time_str, '%H:%M').time()
    except (ValueError, TypeError):
        return Response({'error': 'Invalid date or time format'}, status=status.HTTP_400_BAD_REQUEST)

    if reservation_date < timezone.now().date():
        return Response({'error': 'Cannot make reservation for past date'}, status=status.HTTP_400_BAD_REQUEST)

    duration = request.data.get('duration_hours', 1)
    try:
        duration = int(duration)
        if duration < 1:
            duration = 1
    except (ValueError, TypeError):
        duration = 1

    # Calculate requested end time
    end_datetime = datetime.combine(reservation_date, reservation_time) + timedelta(hours=duration)
    end_time = end_datetime.time()

    table = None

    if selection_type == 'customized':
        table_id = request.data.get('table_id')
        if not table_id:
            return Response({'error': "'table_id' is required when selection_type='customized'"}, status=status.HTTP_400_BAD_REQUEST)
        table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
        if party_size > table.capacity:
            return Response({'error': 'Table capacity is not sufficient for your party size'}, status=status.HTTP_400_BAD_REQUEST)

        # Check for conflicts on the chosen table
        conflicting_reservations = Reservation.objects.filter(
            table=table,
            reservation_date=reservation_date,
            status__in=['pending', 'confirmed']
        )
        for existing in conflicting_reservations:
            existing_end_time = existing.end_time
            if (reservation_time < existing_end_time and end_time > existing.reservation_time):
                return Response({'error': f'Table is already reserved from {existing.reservation_time.strftime("%H:%M")} to {existing_end_time.strftime("%H:%M")}'}, status=status.HTTP_400_BAD_REQUEST)

    elif selection_type == 'smart':
        # Build candidate tables
        candidate_tables = Table.objects.filter(
            restaurant=restaurant,
            is_active=True,
            capacity__gte=party_size
        )
        available_tables = []
        for t in candidate_tables:
            overlaps = False
            existing_reservations = Reservation.objects.filter(
                table=t,
                reservation_date=reservation_date,
                status__in=['pending', 'confirmed']
            )
            for r in existing_reservations:
                if (reservation_time < r.end_time and end_time > r.reservation_time):
                    overlaps = True
                    break
            if not overlaps:
                available_tables.append(t)
        
        if not available_tables:
            return Response({'error': 'No available tables for the selected time and party size'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user preferences and special occasion from request
        user_preferences = request.data.get('user_preferences', {})
        special_occasion = request.data.get('special_occasion', '')
        
        # Initialize AI service and track timing
        ai_service = AIService()
        start_time = time.time()
        
        # Try AI-powered table selection
        ai_result = ai_service.select_optimal_table(
            restaurant_id=restaurant.id,
            party_size=party_size,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            duration_hours=duration,
            available_tables=available_tables,
            user_preferences=user_preferences,
            special_occasion=special_occasion
        )
        
        ai_response_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        # Get the selected table from AI result
        table = ai_result.get('selected_table')
        
        # If AI failed to select a table, fallback to random selection
        if not table:
            table = available_tables[0]  # Fallback to first available table
            ai_result = {
                'success': False,
                'selected_table': table,
                'reasoning': 'AI service failed, selected first available table as fallback',
                'confidence': 0.1,
                'alternative_table_id': None,
                'factors_considered': ['error_fallback'],
                'error': 'AI service returned no table'
            }
        
        # Store AI selection data for later logging
        ai_selection_data = {
            'ai_result': ai_result,
            'ai_response_time': ai_response_time,
            'available_tables': available_tables,
            'user_preferences': user_preferences,
            'special_occasion': special_occasion
        }
        
    else:
        return Response({'error': "Invalid selection_type. Use 'customized' or 'smart'"}, status=status.HTTP_400_BAD_REQUEST)

    # Create the reservation
    reservation = Reservation.objects.create(
        customer=user,
        restaurant=restaurant,
        table=table,
        party_size=party_size,
        reservation_date=reservation_date,
        reservation_time=reservation_time,
        duration_hours=duration,
        status='pending',
        special_requests=request.data.get('special_requests', '')
    )

    # Auto-approve if the user is a manager
    if user.is_staff_member and user.staff_profile.role == 'manager':
        reservation.status = 'confirmed'
        reservation.save()
        ReservationStatusUpdate.objects.create(
            reservation=reservation,
            status='confirmed',
            notes='Auto-approved by manager',
            updated_by=user
        )
    
    # Log AI table selection if it was used
    if selection_type == 'smart' and 'ai_selection_data' in locals():
        try:
            ai_result = ai_selection_data['ai_result']
            
            # Determine selection method based on AI success
            if ai_result.get('success', False):
                selection_method = 'ai'
            elif 'error_fallback' in ai_result.get('factors_considered', []):
                selection_method = 'error_fallback'
            else:
                selection_method = 'random'
            
            # Prepare available tables data for logging
            available_tables_data = []
            for t in ai_selection_data['available_tables']:
                available_tables_data.append({
                    'id': t.id,
                    'table_number': t.table_number,
                    'capacity': t.capacity
                })
            
            # Create the table selection log
            TableSelectionLog.objects.create(
                reservation=reservation,
                restaurant=restaurant,
                user=user,
                selection_method=selection_method,
                selected_table=table,
                available_tables_count=len(ai_selection_data['available_tables']),
                available_tables_data=available_tables_data,
                ai_reasoning=ai_result.get('reasoning', ''),
                ai_confidence=ai_result.get('confidence', 0.0),
                ai_factors_considered=ai_result.get('factors_considered', []),
                ai_alternative_table_id=ai_result.get('alternative_table_id'),
                party_size=party_size,
                reservation_date=reservation_date,
                reservation_time=reservation_time,
                duration_hours=duration,
                special_occasion=ai_selection_data.get('special_occasion', ''),
                user_preferences=ai_selection_data.get('user_preferences', {}),
                ai_response_time_ms=ai_selection_data['ai_response_time'],
                ai_success=ai_result.get('success', False),
                ai_error_message=ai_result.get('error', '')
            )
        except Exception as log_error:
            # Don't fail the reservation if logging fails
            print(f"Failed to log AI table selection: {log_error}")

    # Build response data
    response_data = {
        'success': 'Reservation created successfully',
        'reservation': {
            'id': reservation.id,
            'status': reservation.status,
            'selection_type': selection_type,
            'date': reservation.reservation_date.strftime('%Y-%m-%d'),
            'time': reservation.reservation_time.strftime('%H:%M'),
            'duration_hours': reservation.duration_hours,
            'party_size': reservation.party_size,
            'table': {
                'id': reservation.table.id,
                'number': reservation.table.table_number,
                'capacity': reservation.table.capacity,
            },
            'special_requests': reservation.special_requests,
        }
    }
    
    # Add AI selection information if smart selection was used
    if selection_type == 'smart' and 'ai_selection_data' in locals():
        ai_result = ai_selection_data['ai_result']
        response_data['ai_selection'] = {
            'method': 'ai' if ai_result.get('success', False) else 'fallback',
            'reasoning': ai_result.get('reasoning', ''),
            'confidence': ai_result.get('confidence', 0.0),
            'response_time_ms': ai_selection_data['ai_response_time'],
            'factors_considered': ai_result.get('factors_considered', [])
        }
        if ai_result.get('alternative_table_id'):
            response_data['ai_selection']['alternative_table_id'] = ai_result.get('alternative_table_id')
    
    return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_reservations(request):
    # Auto-complete any past reservations before returning list
    _mark_expired_reservations()
    """Get all reservations for the current user"""
    user = request.user
    
    if not user.is_customer:
        return Response({'error': 'Only customers can view their reservations'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    reservations = Reservation.objects.filter(customer=user).select_related('restaurant', 'table').prefetch_related('restaurant__categories').order_by('-reservation_date', '-reservation_time')
    
    data = []
    for reservation in reservations:
        # Format time to 12-hour format
        time_12_hour = reservation.reservation_time.strftime('%I:%M %p')
        
        # Get restaurant categories
        categories = [{'id': cat.id, 'name': cat.name} for cat in reservation.restaurant.categories.all()]
        
        # Get restaurant logo/cover image URL
        logo_url = None
        cover_image_url = None
        if reservation.restaurant.logo:
            logo_url = request.build_absolute_uri(reservation.restaurant.logo.url)
        if reservation.restaurant.cover_image:
            cover_image_url = request.build_absolute_uri(reservation.restaurant.cover_image.url)
        
        data.append({
            'id': reservation.id,
            'restaurant': {
                'id': reservation.restaurant.id,
                'name': reservation.restaurant.name,
                'address': reservation.restaurant.address,
                'average_rating': float(reservation.restaurant.average_rating),
                'logo': logo_url,
                'cover_image': cover_image_url,
                'categories': categories,
            },
            'table': reservation.table.table_number,
            'party_size': reservation.party_size,
            'date': reservation.reservation_date,
            'time': time_12_hour,
            'duration_hours': reservation.duration_hours,
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
    
    # Add cancellation information for customers
    if user.is_customer:
        from .utils import get_reservation_cancellation_info
        data['cancellation_info'] = get_reservation_cancellation_info(reservation)
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_reservation(request, reservation_id):
    """Cancel a reservation with time restrictions"""
    user = request.user
    
    if not user.is_customer:
        return Response({'error': 'Only customers can cancel their reservations'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    reservation = get_object_or_404(Reservation, id=reservation_id, customer=user)
    
    # Check if reservation can be cancelled using utility function
    from .utils import can_cancel_reservation
    from datetime import datetime
    
    can_cancel, reason = can_cancel_reservation(reservation)
    if not can_cancel:
        return Response({'error': reason}, status=status.HTTP_400_BAD_REQUEST)
    
    # Calculate time until reservation for logging
    now = timezone.now()
    reservation_datetime = datetime.combine(reservation.reservation_date, reservation.reservation_time)
    reservation_datetime = timezone.make_aware(reservation_datetime) if timezone.is_naive(reservation_datetime) else reservation_datetime
    time_until_reservation = reservation_datetime - now
    
    # Cancel the reservation
    reservation.status = 'cancelled'
    reservation.save()
    
    # Create status update record for tracking
    from .models import ReservationStatusUpdate
    ReservationStatusUpdate.objects.create(
        reservation=reservation,
        status='cancelled',
        notes=f'Cancelled by customer with {time_until_reservation.total_seconds() / 3600:.1f} hours advance notice',
        updated_by=user
    )
    
    return Response({
        'success': 'Reservation cancelled successfully',
        'cancelled_at': now.isoformat(),
        'advance_notice_hours': time_until_reservation.total_seconds() / 3600
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reservation_cancellation_info(request, reservation_id):
    """Get cancellation information for a reservation"""
    user = request.user
    
    if not user.is_customer:
        return Response({'error': 'Only customers can check their reservation cancellation info'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    reservation = get_object_or_404(Reservation, id=reservation_id, customer=user)
    
    from .utils import get_reservation_cancellation_info
    cancellation_info = get_reservation_cancellation_info(reservation)
    
    return Response(cancellation_info, status=status.HTTP_200_OK)


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
        'categories': [category.name for category in restaurant.categories.all()],
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


# Enhanced Reservation System Views

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('restaurant_id', openapi.IN_PATH, description="Restaurant ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('party_size', openapi.IN_QUERY, description="Number of guests", type=openapi.TYPE_INTEGER),
    ],
    responses={
        200: openapi.Response(
            description="Available dates for reservation",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'available_dates': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                                'available_slots': openapi.Schema(type=openapi.TYPE_INTEGER),
                            }
                        )
                    )
                }
            )
        )
    },
    operation_description="Get available dates for reservation based on party size"
)
@api_view(['GET'])
@permission_classes([AllowAny])
def available_dates(request, restaurant_id):
    """
    Get available dates for reservation based on party size.
    Shows dates for the next 30 days with available time slots.
    """
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    
    # Get party size (no limits as requested)
    party_size = int(request.GET.get('party_size', 1))
    
    # Get available dates for the next 30 days
    available_dates = []
    today = timezone.now().date()
    
    for i in range(30):  # Next 30 days
        check_date = today + timedelta(days=i)
        
        # Skip past dates
        if check_date < today:
            continue
            
        # Find tables that can accommodate the party size
        suitable_tables = Table.objects.filter(
            restaurant=restaurant,
            is_active=True,
            capacity__gte=party_size
        )
        
        if not suitable_tables.exists():
            continue
            
        # Check how many time slots are available for this date
        available_slots = 0
        
        # Generate time slots from opening to closing time (every hour)
        opening_time = restaurant.opening_time
        closing_time = restaurant.closing_time
        
        # Convert times to datetime for easier calculation
        current_time = datetime.combine(check_date, opening_time)
        end_time = datetime.combine(check_date, closing_time)
        
        while current_time < end_time:
            slot_time = current_time.time()
            
            # Consider a 1-hour slot window for date-level availability
            slot_end_time = (current_time + timedelta(hours=1)).time()
            
            # Determine if at least one table is free for the entire 1-hour window
            any_table_free = False
            for t in suitable_tables:
                conflicts = Reservation.objects.filter(
                    restaurant=restaurant,
                    reservation_date=check_date,
                    table=t,
                    status__in=['pending', 'confirmed']
                )
                has_overlap = False
                for r in conflicts:
                    if r.reservation_time < slot_end_time and r.end_time > slot_time:
                        has_overlap = True
                        break
                if not has_overlap:
                    any_table_free = True
                    break
            
            if any_table_free:
                available_slots += 1
                
            current_time += timedelta(hours=1)
        
        if available_slots > 0:
            available_dates.append({
                'date': check_date.strftime('%Y-%m-%d'),
                'available_slots': available_slots,
                'day_name': check_date.strftime('%A')
            })
    
    return Response({
        'available_dates': available_dates,
        'restaurant': {
            'id': restaurant.id,
            'name': restaurant.name,
            'opening_time': restaurant.opening_time.strftime('%H:%M'),
            'closing_time': restaurant.closing_time.strftime('%H:%M'),
        }
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('restaurant_id', openapi.IN_PATH, description="Restaurant ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('date', openapi.IN_QUERY, description="Date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
        openapi.Parameter('party_size', openapi.IN_QUERY, description="Number of guests", type=openapi.TYPE_INTEGER),
        openapi.Parameter('duration', openapi.IN_QUERY, description="Duration in hours (default: 1)", type=openapi.TYPE_INTEGER),
    ],
    responses={
        200: openapi.Response(
            description="Available time slots for the selected date",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'available_times': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'time': openapi.Schema(type=openapi.TYPE_STRING),
                                'display_time': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    )
                }
            )
        )
    },
    operation_description="Get available time slots for a specific date"
)
@api_view(['GET'])
@permission_classes([AllowAny])
def available_times(request, restaurant_id):
    # Auto-complete any past reservations before computing availability
    _mark_expired_reservations()
    """
    Get available time slots for a specific date and party size.
    Takes into account reservation duration to avoid overlaps and calculates slot capacity.
    """
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    
    # Get parameters
    date_str = request.GET.get('date')
    party_size = int(request.GET.get('party_size', 1))
    duration = int(request.GET.get('duration', 1))  # default 1 hour
    if duration < 1:
        duration = 1
    
    if not date_str:
        return Response({'error': 'Date is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format, use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if date is in the past
    if reservation_date < timezone.now().date():
        return Response({'error': 'Cannot check availability for past dates'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Find tables that can accommodate the party size
    suitable_tables = Table.objects.filter(
        restaurant=restaurant,
        is_active=True,
        capacity__gte=party_size
    )
    
    if not suitable_tables.exists():
        return Response({
            'available_times': [],
            'message': f'No tables available for {party_size} guests'
        }, status=status.HTTP_200_OK)
    
    # Generate time slots
    available_times = []
    opening_time = restaurant.opening_time
    closing_time = restaurant.closing_time
    
    # Convert times to datetime for easier calculation
    current_time = datetime.combine(reservation_date, opening_time)
    close_dt = datetime.combine(reservation_date, closing_time)
    
    # Ensure a slot can fit entirely before closing
    while current_time + timedelta(hours=duration) <= close_dt:
        slot_time = current_time.time()
        end_time = (current_time + timedelta(hours=duration)).time()
        
        # Skip past time slots if reservation date is today (GMT+3)
        gmt_plus_3 = pytz.timezone('Etc/GMT-3')  # Note: GMT-3 means +3 hours from GMT
        current_datetime_gmt3 = timezone.now().astimezone(gmt_plus_3)
        current_date_gmt3 = current_datetime_gmt3.date()
        
        if reservation_date == current_date_gmt3:
            slot_datetime = datetime.combine(reservation_date, slot_time)
            slot_datetime_gmt3 = gmt_plus_3.localize(slot_datetime)
            if slot_datetime_gmt3 <= current_datetime_gmt3:
                current_time += timedelta(hours=1)
                continue
        
        # Count how many tables are free for the whole duration window
        free_tables_count = 0
        for t in suitable_tables:
            overlaps = Reservation.objects.filter(
                restaurant=restaurant,
                reservation_date=reservation_date,
                table=t,
                status__in=['pending', 'confirmed']
            ).filter(
                reservation_time__lt=end_time,
            )
            is_conflict = False
            for r in overlaps:
                if r.reservation_time < end_time and r.end_time > slot_time:
                    is_conflict = True
                    break
            if not is_conflict:
                free_tables_count += 1
        
        if free_tables_count > 0:
            # Build per-duration availability counts for this slot
            max_hours = int((close_dt - current_time).total_seconds() // 3600)
            duration_availability = {}
            for d in range(1, max_hours + 1):
                slot_end_for_d = (current_time + timedelta(hours=d)).time()
                count_for_d = 0
                for t in suitable_tables:
                    conflicts = Reservation.objects.filter(
                        restaurant=restaurant,
                        reservation_date=reservation_date,
                        table=t,
                        status__in=['pending', 'confirmed']
                    ).filter(
                        reservation_time__lt=slot_end_for_d,
                    )
                    has_overlap = False
                    for r in conflicts:
                        if r.reservation_time < slot_end_for_d and r.end_time > slot_time:
                            has_overlap = True
                            break
                    if not has_overlap:
                        count_for_d += 1
                duration_availability[str(d)] = count_for_d
            
            available_times.append({
                'time': slot_time.strftime('%H:%M'),
                'display_time': slot_time.strftime('%I:%M %p'),
                'available_tables': free_tables_count,
                'duration_availability': duration_availability
            })
        
        current_time += timedelta(hours=1)
    
    return Response({
        'available_times': available_times,
        'date': reservation_date.strftime('%Y-%m-%d'),
        'party_size': party_size,
        'requested_duration': duration,
        'restaurant': {
            'id': restaurant.id,
            'name': restaurant.name,
            'closing_time': restaurant.closing_time.strftime('%H:%M'),
        },
        'note': 'duration_availability shows number of tables available for each duration in hours'
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('restaurant_id', openapi.IN_PATH, description="Restaurant ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('date', openapi.IN_QUERY, description="Date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
        openapi.Parameter('time', openapi.IN_QUERY, description="Time (HH:MM)", type=openapi.TYPE_STRING),
        openapi.Parameter('party_size', openapi.IN_QUERY, description="Number of guests", type=openapi.TYPE_INTEGER),
        openapi.Parameter('duration', openapi.IN_QUERY, description="Duration in hours (minimum 1)", type=openapi.TYPE_INTEGER),
    ],
    responses={
        200: openapi.Response(
            description="Available tables grouped by floor",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'floors': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'floor': openapi.Schema(type=openapi.TYPE_STRING),
                                'floor_display': openapi.Schema(type=openapi.TYPE_STRING),
                                'tables': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'table_number': openapi.Schema(type=openapi.TYPE_STRING),
                                            'capacity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        }
                                    )
                                )
                            }
                        )
                    )
                }
            )
        )
    },
    operation_description="Get available tables grouped by floor for specific date, time, and duration"
)
@api_view(['GET'])
@permission_classes([AllowAny])
def available_tables_by_floor(request, restaurant_id):
    # Auto-complete any past reservations before computing availability
    _mark_expired_reservations()
    """
    Get available tables grouped by floor for a specific date, time, party size, and duration.
    """
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    
    # Get parameters
    date_str = request.GET.get('date')
    time_str = request.GET.get('time')
    party_size = int(request.GET.get('party_size', 1))
    duration = int(request.GET.get('duration', 1))  # Default 1 hour
    
    # Validate required parameters
    if not date_str or not time_str:
        return Response({'error': 'Date and time are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate minimum duration
    if duration < 1:
        return Response({'error': 'Minimum duration is 1 hour'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        reservation_time = datetime.strptime(time_str, '%H:%M').time()
    except ValueError:
        return Response({'error': 'Invalid date or time format'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if date/time is in the past
    reservation_datetime = timezone.make_aware(datetime.combine(reservation_date, reservation_time))
    if reservation_datetime < timezone.now():
        return Response({'error': 'Cannot check availability for past date/time'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Calculate end time for the reservation
    reservation_datetime_naive = datetime.combine(reservation_date, reservation_time)
    end_datetime = reservation_datetime_naive + timedelta(hours=duration)
    end_time = end_datetime.time()
    
    # Find tables that can accommodate the party size
    suitable_tables = Table.objects.filter(
        restaurant=restaurant,
        is_active=True,
        capacity__gte=party_size
    )
    
    # Find tables that are NOT reserved during the requested time period
    conflicting_reservations = Reservation.objects.filter(
        restaurant=restaurant,
        reservation_date=reservation_date,
        status__in=['pending', 'confirmed'],
        table__in=suitable_tables
    ).filter(
        # Check for time overlap
        reservation_time__lt=end_time,
        # Using the end_time property we added to the model
    )
    
    # Get tables that have conflicting reservations
    reserved_table_ids = []
    for reservation in conflicting_reservations:
        # Check if there's actual time overlap
        existing_end_time = reservation.end_time
        if (reservation.reservation_time < end_time and 
            existing_end_time > reservation_time):
            reserved_table_ids.append(reservation.table_id)
    
    # Get available tables
    available_tables = suitable_tables.exclude(id__in=reserved_table_ids)
    
    # Group tables by floor
    floors_data = {}
    for table in available_tables:
        floor_key = table.floor
        floor_display = table.get_floor_display()
        
        if floor_key not in floors_data:
            floors_data[floor_key] = {
                'floor': floor_key,
                'floor_display': floor_display,
                'tables': []
            }
        
        floors_data[floor_key]['tables'].append({
            'id': table.id,
            'table_number': table.table_number,
            'capacity': table.capacity,
        })
    
    # Convert to list and sort by floor order
    floor_order = ['ground', 'first', 'second', 'third', 'fourth', 'rooftop']
    floors_list = []
    
    for floor_key in floor_order:
        if floor_key in floors_data:
            floors_list.append(floors_data[floor_key])
    
    # Add any floors not in the standard order
    for floor_key, floor_data in floors_data.items():
        if floor_key not in floor_order:
            floors_list.append(floor_data)
    
    return Response({
        'floors': floors_list,
        'reservation_details': {
            'date': reservation_date.strftime('%Y-%m-%d'),
            'time': reservation_time.strftime('%H:%M'),
            'duration': duration,
            'party_size': party_size,
            'end_time': end_time.strftime('%H:%M'),
        },
        'restaurant': {
            'id': restaurant.id,
            'name': restaurant.name,
        }
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['table_id', 'party_size', 'date', 'time', 'duration'],
        properties={
            'table_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="Selected table ID"),
            'party_size': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of guests"),
            'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description="Reservation date (YYYY-MM-DD)"),
            'time': openapi.Schema(type=openapi.TYPE_STRING, description="Reservation time (HH:MM)"),
            'duration': openapi.Schema(type=openapi.TYPE_INTEGER, description="Duration in hours (minimum 1)"),
            'special_requests': openapi.Schema(type=openapi.TYPE_STRING, description="Special requests (optional)"),
        }
    ),
    responses={
        201: openapi.Response(
            description="Reservation created successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_STRING),
                    'reservation': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                            'date': openapi.Schema(type=openapi.TYPE_STRING),
                            'time': openapi.Schema(type=openapi.TYPE_STRING),
                            'duration': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'party_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'table': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'number': openapi.Schema(type=openapi.TYPE_STRING),
                                    'floor': openapi.Schema(type=openapi.TYPE_STRING),
                                    'capacity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                }
                            ),
                        }
                    ),
                }
            )
        )
    },
    operation_description="Create a new reservation with enhanced features"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_enhanced_reservation(request, restaurant_id):
    """
    Create a new reservation with enhanced features including duration and floor selection.
    """
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    user = request.user
    
    # Permission check (same as original)
    if user.is_customer:
        pass
    elif user.is_staff_member:
        try:
            staff_profile = user.staff_profile
            if staff_profile.restaurant.id != restaurant.id:
                return Response({'error': 'Staff can only make reservations at their own restaurant'}, 
                               status=status.HTTP_403_FORBIDDEN)
            if staff_profile.role == 'chef':
                return Response({'error': 'Chefs are not allowed to make reservations'}, 
                               status=status.HTTP_403_FORBIDDEN)
        except:
            return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    else:
        return Response({'error': 'Only customers, waiters, or managers can make reservations'}, 
                        status=status.HTTP_403_FORBIDDEN)
    
    # Get and validate reservation details
    table_id = request.data.get('table_id')
    party_size = request.data.get('party_size')
    date_str = request.data.get('date')
    time_str = request.data.get('time')
    duration = request.data.get('duration', 1)
    special_requests = request.data.get('special_requests', '')
    
    # Validate required fields
    if not all([table_id, party_size, date_str, time_str]):
        return Response({'error': 'Table ID, party size, date, and time are required'}, 
                        status=status.HTTP_400_BAD_REQUEST)
    
    # Validate duration
    try:
        duration = int(duration)
        if duration < 1:
            return Response({'error': 'Minimum duration is 1 hour'}, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({'error': 'Duration must be a valid number'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get and validate table
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant, is_active=True)
    
    # Validate party size
    try:
        party_size = int(party_size)
        if party_size < 1:
            return Response({'error': 'Party size must be at least 1'}, status=status.HTTP_400_BAD_REQUEST)
        if party_size > table.capacity:
            return Response({'error': f'Table capacity ({table.capacity}) is not sufficient for party size ({party_size})'}, 
                           status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({'error': 'Party size must be a valid number'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Parse and validate date/time
    try:
        reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        reservation_time = datetime.strptime(time_str, '%H:%M').time()
    except (ValueError, TypeError):
        return Response({'error': 'Invalid date or time format'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if date/time is in the past
    reservation_datetime = timezone.make_aware(datetime.combine(reservation_date, reservation_time))
    if reservation_datetime < timezone.now():
        return Response({'error': 'Cannot make reservation for past date/time'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Calculate end time
    reservation_datetime_naive = datetime.combine(reservation_date, reservation_time)
    end_datetime = reservation_datetime_naive + timedelta(hours=duration)
    end_time = end_datetime.time()
    
    # Check for conflicting reservations
    conflicting_reservations = Reservation.objects.filter(
        table=table,
        reservation_date=reservation_date,
        status__in=['pending', 'confirmed']
    )
    
    for existing_reservation in conflicting_reservations:
        existing_end_time = existing_reservation.end_time
        # Check for time overlap
        if (reservation_time < existing_end_time and 
            end_time > existing_reservation.reservation_time):
            return Response({
                'error': f'Table is already reserved from {existing_reservation.reservation_time.strftime("%H:%M")} to {existing_end_time.strftime("%H:%M")}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create the reservation
    reservation = Reservation.objects.create(
        customer=user,
        restaurant=restaurant,
        table=table,
        party_size=party_size,
        reservation_date=reservation_date,
        reservation_time=reservation_time,
        duration_hours=duration,
        status='pending',
        special_requests=special_requests
    )
    
    # Auto-approve if the user is a manager
    if user.is_staff_member and hasattr(user, 'staff_profile') and user.staff_profile.role == 'manager':
        reservation.status = 'confirmed'
        reservation.save()
        
        # Create notification for auto-approval
        from .models import ReservationStatusUpdate
        ReservationStatusUpdate.objects.create(
            reservation=reservation,
            status='confirmed',
            notes='Auto-approved by manager',
            updated_by=user
        )
    
    return Response({
        'success': 'Reservation created successfully',
        'reservation': {
            'id': reservation.id,
            'status': reservation.status,
            'date': reservation.reservation_date.strftime('%Y-%m-%d'),
            'time': reservation.reservation_time.strftime('%H:%M'),
            'duration': reservation.duration_hours,
            'party_size': reservation.party_size,
            'end_time': end_time.strftime('%H:%M'),
            'table': {
                'number': table.table_number,
                'floor': table.get_floor_display(),
                'capacity': table.capacity,
            },
            'special_requests': reservation.special_requests,
        }
    }, status=status.HTTP_201_CREATED)


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('restaurant_id', openapi.IN_PATH, description="Restaurant ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('date', openapi.IN_QUERY, description="Date (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=True),
        openapi.Parameter('time', openapi.IN_QUERY, description="Time (HH:MM)", type=openapi.TYPE_STRING, required=True),
        openapi.Parameter('party_size', openapi.IN_QUERY, description="Party size", type=openapi.TYPE_INTEGER, default=1),
    ],
    responses={
        200: openapi.Response(
            description="Available durations for the specified date, time, and party size",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'available_durations': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'duration': openapi.Schema(type=openapi.TYPE_INTEGER, description="Duration in hours"),
                                'end_time': openapi.Schema(type=openapi.TYPE_STRING, description="End time (HH:MM)"),
                                'available_tables': openapi.Schema(type=openapi.TYPE_INTEGER, description="Number of available tables"),
                                'display_text': openapi.Schema(type=openapi.TYPE_STRING, description="Human-readable duration text"),
                            }
                        )
                    ),
                    'date': openapi.Schema(type=openapi.TYPE_STRING),
                    'time': openapi.Schema(type=openapi.TYPE_STRING),
                    'party_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'restaurant': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'closing_time': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            )
        ),
        400: openapi.Response(description="Bad request - missing or invalid parameters"),
        404: openapi.Response(description="Restaurant not found"),
    },
    operation_description="Get available reservation durations for a specific date, time, and party size"
)
@api_view(['GET'])
@permission_classes([AllowAny])
def available_durations(request, restaurant_id):
    """
    Get available reservation durations for a specific date, time, and party size.
    Shows how long a reservation can be based on restaurant closing time and other reservations.
    """
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    
    # Get parameters
    date_str = request.GET.get('date')
    time_str = request.GET.get('time')
    party_size = int(request.GET.get('party_size', 1))
    
    # Validate required parameters
    if not date_str or not time_str:
        return Response({'error': 'Date and time are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        reservation_time = datetime.strptime(time_str, '%H:%M').time()
    except ValueError:
        return Response({'error': 'Invalid date or time format'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if date/time is in the past
    reservation_datetime = timezone.make_aware(datetime.combine(reservation_date, reservation_time))
    if reservation_datetime < timezone.now():
        return Response({'error': 'Cannot check availability for past date/time'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Find tables that can accommodate the party size
    suitable_tables = Table.objects.filter(
        restaurant=restaurant,
        is_active=True,
        capacity__gte=party_size
    )
    
    if not suitable_tables.exists():
        return Response({
            'available_durations': [],
            'message': f'No tables available for {party_size} guests'
        }, status=status.HTTP_200_OK)
    
    # Calculate maximum possible duration based on restaurant closing time
    closing_time = restaurant.closing_time
    reservation_datetime_naive = datetime.combine(reservation_date, reservation_time)
    closing_datetime = datetime.combine(reservation_date, closing_time)
    
    # If closing time is earlier than reservation time (next day closing), add a day
    if closing_time < reservation_time:
        closing_datetime += timedelta(days=1)
    
    max_duration_hours = int((closing_datetime - reservation_datetime_naive).total_seconds() / 3600)
    
    # Limit to reasonable maximum (e.g., 6 hours)
    max_duration_hours = min(max_duration_hours, 6)
    
    if max_duration_hours < 1:
        return Response({
            'available_durations': [],
            'message': 'No time available before restaurant closes'
        }, status=status.HTTP_200_OK)
    
    # Check each possible duration (1 to max_duration_hours)
    available_durations = []
    
    for duration in range(1, max_duration_hours + 1):
        # Calculate end time for this duration
        end_datetime = reservation_datetime_naive + timedelta(hours=duration)
        end_time = end_datetime.time()
        
        # Find tables that are NOT reserved during this entire time period
        # Get all reservations for this date
        all_reservations = Reservation.objects.filter(
            restaurant=restaurant,
            reservation_date=reservation_date,
            status__in=['pending', 'confirmed']
        )
        
        # Check for overlapping reservations manually
        conflicting_reservation_ids = []
        for res in all_reservations:
            # Calculate existing reservation end time
            res_start = datetime.combine(reservation_date, res.reservation_time)
            res_end = res_start + timedelta(hours=res.duration_hours)
            
            # Calculate our proposed reservation times
            our_start = datetime.combine(reservation_date, reservation_time)
            our_end = datetime.combine(reservation_date, end_time)
            
            # Check for overlap: reservations overlap if one starts before the other ends
            if (our_start < res_end) and (our_end > res_start):
                conflicting_reservation_ids.append(res.id)
        
        conflicting_reservations = Reservation.objects.filter(id__in=conflicting_reservation_ids)
        
        reserved_table_ids = conflicting_reservations.values_list('table_id', flat=True)
        available_tables_for_duration = suitable_tables.exclude(id__in=reserved_table_ids)
        available_count = available_tables_for_duration.count()
        
        if available_count > 0:
            # Create display text
            if duration == 1:
                display_text = "1 hour"
            else:
                display_text = f"{duration} hours"
            
            available_durations.append({
                'duration': duration,
                'end_time': end_time.strftime('%H:%M'),
                'available_tables': available_count,
                'display_text': display_text
            })
    
    return Response({
        'available_durations': available_durations,
        'date': reservation_date.strftime('%Y-%m-%d'),
        'time': reservation_time.strftime('%H:%M'),
        'party_size': party_size,
        'restaurant': {
            'id': restaurant.id,
            'name': restaurant.name,
            'closing_time': restaurant.closing_time.strftime('%H:%M'),
        }
    }, status=status.HTTP_200_OK)
