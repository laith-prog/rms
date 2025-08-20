from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from .serializers import (
    ChatMessageSerializer, 
    RecommendationRequestSerializer,
    MenuRecommendationSerializer,
    ReservationSuggestionSerializer,
    SentimentAnalysisSerializer
)
from .services import (
    get_ai_client, 
    AIRecommendationService, 
    AIReservationService, 
    AISentimentService
)
from restaurants.models import MenuItem, Restaurant
from accounts.permissions import IsCustomer


def get_restaurant_context(user_message: str) -> str:
    """
    Get relevant restaurant data based on the user's message.
    This provides context to the AI about available restaurants and menus.
    """
    # Get active restaurants with their basic info
    restaurants = Restaurant.objects.filter(is_active=True).select_related().prefetch_related('menu_items')
    
    if not restaurants.exists():
        return "No restaurants are currently available in the system."
    
    context_parts = []
    
    # Check if user is asking about specific restaurant or general info
    user_msg_lower = user_message.lower()
    specific_restaurant = None
    
    # Try to find if user mentioned a specific restaurant
    for restaurant in restaurants:
        if restaurant.name.lower() in user_msg_lower:
            specific_restaurant = restaurant
            break
    
    if specific_restaurant:
        # Provide detailed info about the specific restaurant
        context_parts.append(f"RESTAURANT: {specific_restaurant.name}")
        context_parts.append(f"Description: {specific_restaurant.description or 'No description available'}")
        context_parts.append(f"Address: {specific_restaurant.address}")
        context_parts.append(f"Phone: {specific_restaurant.phone}")
        context_parts.append(f"Email: {specific_restaurant.email}")
        
        # Get menu items for this restaurant
        menu_items = MenuItem.objects.filter(
            restaurant=specific_restaurant, 
            is_active=True
        ).select_related('food_category')
        
        if menu_items.exists():
            context_parts.append("\nMENU ITEMS:")
            for item in menu_items[:15]:  # Limit to avoid token limits
                dietary_info = []
                if item.is_vegetarian:
                    dietary_info.append("Vegetarian")
                if item.is_vegan:
                    dietary_info.append("Vegan")
                if item.is_gluten_free:
                    dietary_info.append("Gluten-Free")
                
                dietary_str = f" ({', '.join(dietary_info)})" if dietary_info else ""
                category_str = f" [{item.food_category.name}]" if item.food_category else ""
                
                context_parts.append(
                    f"- {item.name}: ${item.price}{category_str}{dietary_str}"
                )
                if item.description:
                    context_parts.append(f"  Description: {item.description}")
    else:
        # Provide overview of all restaurants
        context_parts.append("AVAILABLE RESTAURANTS:")
        for restaurant in restaurants[:5]:  # Limit to avoid token limits
            context_parts.append(f"\n{restaurant.name}")
            context_parts.append(f"  Address: {restaurant.address}")
            context_parts.append(f"  Phone: {restaurant.phone}")
            if restaurant.description:
                context_parts.append(f"  Description: {restaurant.description[:100]}...")
            
            # Add a few popular menu items
            popular_items = MenuItem.objects.filter(
                restaurant=restaurant, 
                is_active=True
            )[:3]
            
            if popular_items.exists():
                context_parts.append("  Popular items:")
                for item in popular_items:
                    context_parts.append(f"    - {item.name}: ${item.price}")
    
    return "\n".join(context_parts)


@api_view(["POST"])
@permission_classes([AllowAny])  # You can switch to IsAuthenticated once frontends pass JWT
def chat(request):
    """Enhanced chat endpoint with restaurant database context."""
    serializer = ChatMessageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user_msg = serializer.validated_data["message"]

    # Get relevant restaurant data based on the user's question
    context_data = get_restaurant_context(user_msg)
    
    # Enhanced system prompt with database context
    system_prompt = f"""You are an AI assistant for a Restaurant Management System. 
You have access to real restaurant data and should provide helpful, accurate information.

AVAILABLE RESTAURANT DATA:
{context_data}

Instructions:
- Use the provided restaurant data to answer questions about specific restaurants, menus, prices, and availability
- If asked about restaurants not in the data, politely say you don't have information about that specific restaurant
- For general dining questions, provide helpful advice
- Be friendly and helpful
- Always mention specific prices, restaurant names, and menu items when relevant
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    try:
        client = get_ai_client()
        ai_reply = client.chat(messages)
        return Response({"reply": ai_reply})
    except Exception as e:
        error_message = str(e)
        # Check for specific AI provider errors
        if "insufficient_quota" in error_message.lower() or "quota" in error_message.lower():
            return Response({
                "detail": "AI API quota exceeded. Please check your billing settings.",
                "error_type": "quota_exceeded"
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
        elif "rate_limit" in error_message.lower():
            return Response({
                "detail": "Rate limit exceeded. Please try again later.",
                "error_type": "rate_limit"
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        elif "not configured" in error_message.lower():
            return Response({
                "detail": "AI service not configured. Please contact administrator.",
                "error_type": "configuration_error"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        else:
            return Response({
                "detail": f"AI service error: {error_message}",
                "error_type": "service_error"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsCustomer])
def recommend(request):
    """Recommendation endpoint for menu items based on preferences and optional restaurant.
    Returns a small list of items sorted by relevance.
    """
    serializer = RecommendationRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    params = serializer.validated_data

    qs = MenuItem.objects.filter(is_active=True, restaurant__is_active=True)

    if params.get("restaurant_id"):
        qs = qs.filter(restaurant_id=params["restaurant_id"]) 
    
    category_ids = params.get("category_ids") or []
    if category_ids:
        qs = qs.filter(Q(food_category_id__in=category_ids) | Q(restaurant__categories__in=category_ids)).distinct()

    # Dietary filters
    for field in ["vegetarian", "vegan", "gluten_free"]:
        val = params.get(field)
        if val is True:
            qs = qs.filter(**{f"is_{field}": True})
        # if val is False or None -> no extra filter

    if params.get("price_max") is not None:
        qs = qs.filter(price__lte=params["price_max"])

    # Basic ranking by rating (if present) then price asc, recent updated
    qs = qs.order_by("price", "-updated_at")[:20]

    # Optional: add a small model re-rank using the menu text context
    items_payload = [
        {
            "id": i.id,
            "restaurant": i.restaurant.name,
            "name": i.name,
            "description": i.description or "",
            "price": str(i.price),
        }
        for i in qs
    ]

    return Response({"items": items_payload})


@api_view(["POST"])
@permission_classes([AllowAny])
def menu_recommendations(request):
    """AI-powered menu recommendations based on user preferences."""
    serializer = MenuRecommendationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    params = serializer.validated_data
    
    try:
        # Get available menu items
        qs = MenuItem.objects.filter(is_active=True, restaurant__is_active=True)
        
        if params.get("restaurant_id"):
            qs = qs.filter(restaurant_id=params["restaurant_id"])
        
        # Apply dietary filters
        dietary_restrictions = params.get("dietary_restrictions", [])
        for restriction in dietary_restrictions:
            if restriction == "vegetarian":
                qs = qs.filter(is_vegetarian=True)
            elif restriction == "vegan":
                qs = qs.filter(is_vegan=True)
            elif restriction == "gluten_free":
                qs = qs.filter(is_gluten_free=True)
        
        # Convert to list for AI processing
        available_items = []
        for item in qs[:30]:  # Limit to avoid token limits
            available_items.append({
                "name": item.name,
                "price": float(item.price),
                "description": item.description or "",
                "category": item.food_category.name if item.food_category else "No category",
                "is_vegetarian": item.is_vegetarian,
                "is_vegan": item.is_vegan,
                "is_gluten_free": item.is_gluten_free,
                "is_spicy": item.is_spicy,
                "restaurant": item.restaurant.name
            })
        
        if not available_items:
            return Response({
                "recommendations": [],
                "summary": "No menu items available matching your criteria."
            })
        
        # Use AI recommendation service
        ai_service = AIRecommendationService()
        recommendations = ai_service.get_menu_recommendations(params, available_items)
        
        return Response(recommendations)
        
    except Exception as e:
        return Response({
            "detail": f"Error getting menu recommendations: {str(e)}",
            "error_type": "service_error"
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["POST"])
@permission_classes([AllowAny])
def reservation_suggestions(request):
    """AI-powered reservation suggestions based on restaurant data and user needs."""
    serializer = ReservationSuggestionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    params = serializer.validated_data
    
    try:
        # Get restaurant data
        restaurant = Restaurant.objects.get(id=params["restaurant_id"], is_active=True)
        
        # Get available tables
        from restaurants.models import Table
        available_tables = Table.objects.filter(
            restaurant=restaurant,
            is_active=True,
            capacity__gte=params["party_size"]
        )
        
        # Prepare restaurant data for AI
        restaurant_data = {
            "name": restaurant.name,
            "opening_time": restaurant.opening_time.strftime("%H:%M"),
            "closing_time": restaurant.closing_time.strftime("%H:%M"),
            "available_tables": [
                f"Table {table.table_number} (capacity: {table.capacity})"
                for table in available_tables
            ],
            "busy_times": "Typically busy during 7-9 PM on weekends",  # Could be enhanced with real data
            "notes": restaurant.description or "No special notes"
        }
        
        # Create user request text
        user_request = f"Party of {params['party_size']} for {params['preferred_date']}"
        if params.get('preferred_time'):
            user_request += f" at {params['preferred_time']}"
        if params.get('occasion'):
            user_request += f" for {params['occasion']}"
        if params.get('special_requests'):
            user_request += f". Special requests: {params['special_requests']}"
        
        # Use AI reservation service
        ai_service = AIReservationService()
        suggestions = ai_service.get_reservation_suggestions(restaurant_data, user_request)
        
        return Response(suggestions)
        
    except Restaurant.DoesNotExist:
        return Response({
            "detail": "Restaurant not found"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            "detail": f"Error getting reservation suggestions: {str(e)}",
            "error_type": "service_error"
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["POST"])
@permission_classes([AllowAny])
def sentiment_analysis(request):
    """AI-powered sentiment analysis for reviews and feedback."""
    serializer = SentimentAnalysisSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    params = serializer.validated_data
    
    try:
        # Use AI sentiment service
        ai_service = AISentimentService()
        analysis = ai_service.analyze_sentiment(
            text=params["text"],
            context=params["context"]
        )
        
        return Response(analysis)
        
    except Exception as e:
        return Response({
            "detail": f"Error analyzing sentiment: {str(e)}",
            "error_type": "service_error"
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)