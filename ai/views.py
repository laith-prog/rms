from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .services import AIService
from .serializers import (
    ChatSerializer,
    MenuRecommendationsSerializer,
    ReservationSuggestionsSerializer,
    SentimentSerializer,
    BasicRecommendationsSerializer,
    SemanticMenuSearchSerializer,
    UpsellRecommendationsSerializer,
    ReviewsSummarizeSerializer,
    PredictWaitTimeSerializer,
)
from .models import ChatSession, ChatMessage


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['message'],
        properties={
            'message': openapi.Schema(type=openapi.TYPE_STRING, description='User message to AI'),
            'context': openapi.Schema(type=openapi.TYPE_STRING, description='Additional context', default=''),
            'session_id': openapi.Schema(type=openapi.TYPE_STRING, description='Existing chat session ID (UUID)'),
        },
    ),
    responses={
        200: openapi.Response(
            description="AI response",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'response': openapi.Schema(type=openapi.TYPE_STRING, description='AI response'),
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Success status'),
                    'session_id': openapi.Schema(type=openapi.TYPE_STRING, description='Chat session id'),
                }
            )
        ),
        400: 'Bad request - message is required',
        503: 'Service unavailable - AI service not configured',
    },
    operation_description="Chat with AI assistant with optional session context"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def ai_chat(request):
    ai_chat.throttle_scope = 'ai'
    serializer = ChatSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # Persist or create session
    session = None
    if data.get('session_id'):
        try:
            session = ChatSession.objects.get(id=data['session_id'], user=request.user)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Invalid session_id'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        session = ChatSession.objects.create(user=request.user)

    # Build short history context (last 6 messages)
    last_msgs = list(session.messages.order_by('-created_at')[:6][::-1])
    history_text = "\n".join([f"{m.role}: {m.content}" for m in last_msgs])
    combined_context = (data.get('context') or '')
    if history_text:
        combined_context = (combined_context + "\n\nRecent history:\n" + history_text).strip()

    ai_service = AIService()
    result = ai_service.chat(message=data['message'], user=request.user, context=combined_context)

    # Store user and assistant messages
    ChatMessage.objects.create(session=session, role='user', content=data['message'])
    if result.get('success'):
        ChatMessage.objects.create(session=session, role='assistant', content=result.get('response', ''))
        result['session_id'] = str(session.id)
        return Response(result, status=status.HTTP_200_OK)
    return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['restaurant_id'],
        properties={
            'restaurant_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Restaurant ID'),
            'dietary_preferences': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING), description='User dietary preferences (vegetarian, vegan, etc.)'),
            'dietary_restrictions': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING), description='Alternative name for dietary_preferences'),
            'allergies': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING), description='User allergies (nuts, dairy, etc.)'),
            'budget_range': openapi.Schema(type=openapi.TYPE_STRING, description='Budget range (low, medium, high)'),
            'preferences': openapi.Schema(type=openapi.TYPE_STRING, description='Additional preferences (e.g., "I like spicy food and seafood")'),
            'cuisine_type': openapi.Schema(type=openapi.TYPE_STRING, description='Preferred cuisine type (optional, for context)'),
        },
    ),
    responses={
        200: openapi.Response(
            description="Menu recommendations",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'recommendations': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                }
            )
        ),
        400: 'Bad request - restaurant_id is required',
        503: 'Service unavailable - AI service not configured',
    },
    operation_description="Get AI-powered menu recommendations based on user preferences"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def menu_recommendations(request):
    menu_recommendations.throttle_scope = 'ai'
    serializer = MenuRecommendationsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # Merge alias field
    dietary_prefs = data.get('dietary_preferences') or data.get('dietary_restrictions') or []

    # Cache key
    cache_key = f"ai:menu_recs:{data['restaurant_id']}:{','.join(sorted([p.lower() for p in dietary_prefs]))}:{','.join(sorted([a.lower() for a in data.get('allergies', [])]))}:{data.get('budget_range')}:{data.get('cuisine_type','')}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached, status=status.HTTP_200_OK)

    ai_service = AIService()
    result = ai_service.get_menu_recommendations(
        restaurant_id=data['restaurant_id'],
        dietary_preferences=dietary_prefs,
        allergies=data.get('allergies', []),
        budget_range=data.get('budget_range', 'medium'),
        additional_preferences=data.get('preferences', ''),
        cuisine_preference=data.get('cuisine_type', '')
    )

    if result.get('success'):
        cache.set(cache_key, result, 300)
        return Response(result, status=status.HTTP_200_OK)
    return Response(result, status=status.HTTP_400_BAD_REQUEST if 'not found' in result.get('error', '') else status.HTTP_503_SERVICE_UNAVAILABLE)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['restaurant_id', 'party_size', 'preferred_date'],
        properties={
            'restaurant_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Restaurant ID'),
            'party_size': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of people'),
            'preferred_date': openapi.Schema(type=openapi.TYPE_STRING, description='Preferred date (YYYY-MM-DD)'),
            'preferred_time': openapi.Schema(type=openapi.TYPE_STRING, description='Preferred time (HH:MM)'),
            'special_occasion': openapi.Schema(type=openapi.TYPE_STRING, description='Special occasion type'),
        },
    ),
    responses={
        200: openapi.Response(
            description="Reservation suggestions",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'suggestions': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                }
            )
        ),
        400: 'Bad request - required fields missing',
        503: 'Service unavailable - AI service not configured',
    },
    operation_description="Get AI-powered reservation time and table suggestions"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def reservation_suggestions(request):
    reservation_suggestions.throttle_scope = 'ai'
    serializer = ReservationSuggestionsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    ai_service = AIService()
    result = ai_service.get_reservation_suggestions(
        restaurant_id=data['restaurant_id'],
        party_size=data['party_size'],
        preferred_date=str(data['preferred_date']),
        preferred_time=(data.get('preferred_time').strftime('%H:%M') if data.get('preferred_time') else None),
        special_occasion=data.get('special_occasion')
    )

    if result.get('success'):
        return Response(result, status=status.HTTP_200_OK)
    return Response(result, status=status.HTTP_400_BAD_REQUEST if 'not found' in result.get('error', '') else status.HTTP_503_SERVICE_UNAVAILABLE)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['text'],
        properties={
            'text': openapi.Schema(type=openapi.TYPE_STRING, description='Text to analyze'),
            'context': openapi.Schema(type=openapi.TYPE_STRING, description='Context (review, feedback, complaint, etc.)'),
        },
    ),
    responses={
        200: openapi.Response(
            description="Sentiment analysis results",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'sentiment': openapi.Schema(type=openapi.TYPE_STRING, description='Sentiment (positive, negative, neutral)'),
                    'confidence': openapi.Schema(type=openapi.TYPE_NUMBER, description='Confidence score'),
                    'emotions': openapi.Schema(type=openapi.TYPE_OBJECT, description='Emotion breakdown'),
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                }
            )
        ),
        400: 'Bad request - text is required',
        503: 'Service unavailable - AI service not configured',
    },
    operation_description="Analyze sentiment and emotions in customer feedback"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def sentiment_analysis(request):
    sentiment_analysis.throttle_scope = 'ai'
    serializer = SentimentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    ai_service = AIService()
    result = ai_service.analyze_sentiment(
        text=data['text'],
        context=data.get('context', 'general')
    )

    if result.get('success'):
        return Response(result, status=status.HTTP_200_OK)
    return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID for personalized recommendations'),
            'recommendation_type': openapi.Schema(type=openapi.TYPE_STRING, description='Type of recommendation (restaurants, dishes, experiences)'),
            'location': openapi.Schema(type=openapi.TYPE_STRING, description='User location'),
            'preferences': openapi.Schema(type=openapi.TYPE_OBJECT, description='User preferences object'),
        },
    ),
    responses={
        200: openapi.Response(
            description="Basic recommendations",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'recommendations': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'recommendation_type': openapi.Schema(type=openapi.TYPE_STRING),
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                }
            )
        ),
        503: 'Service unavailable - AI service not configured',
    },
    operation_description="Get basic AI-powered recommendations for restaurants, dishes, or experiences"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def basic_recommendations(request):
    basic_recommendations.throttle_scope = 'ai'
    serializer = BasicRecommendationsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    ai_service = AIService()
    result = ai_service.get_basic_recommendations(
        user_id=data.get('user_id', request.user.id),
        recommendation_type=data.get('recommendation_type', 'restaurants'),
        location=data.get('location'),
        preferences=data.get('preferences', {})
    )

    if result.get('success'):
        return Response(result, status=status.HTTP_200_OK)
    return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def semantic_menu_search(request):
    semantic_menu_search.throttle_scope = 'ai'
    serializer = SemanticMenuSearchSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    cache_key = f"ai:semantic:{data.get('restaurant_id')}:{data['query'].strip().lower()}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached, status=status.HTTP_200_OK)

    ai_service = AIService()
    result = ai_service.semantic_menu_search(query=data['query'], restaurant_id=data.get('restaurant_id'))

    if result.get('success'):
        cache.set(cache_key, result, 300)
        return Response(result, status=status.HTTP_200_OK)
    return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def upsell_recommendations(request):
    upsell_recommendations.throttle_scope = 'ai'
    serializer = UpsellRecommendationsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    ai_service = AIService()
    result = ai_service.upsell_recommendations(order_id=data['order_id'])
    if result.get('success'):
        return Response(result, status=status.HTTP_200_OK)
    return Response(result, status=status.HTTP_400_BAD_REQUEST if 'not found' in result.get('error', '') else status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def reviews_summarize(request):
    reviews_summarize.throttle_scope = 'ai'
    serializer = ReviewsSummarizeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    ai_service = AIService()
    result = ai_service.reviews_summarize(restaurant_id=data['restaurant_id'], since=data.get('since'))
    if result.get('success'):
        return Response(result, status=status.HTTP_200_OK)
    return Response(result, status=status.HTTP_400_BAD_REQUEST if 'not found' in result.get('error', '') else status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def predict_wait_time(request):
    predict_wait_time.throttle_scope = 'ai'
    serializer = PredictWaitTimeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    ai_service = AIService()
    result = ai_service.predict_wait_time(
        restaurant_id=data['restaurant_id'],
        party_size=data['party_size'],
        time=data['time'].strftime('%H:%M')
    )
    if result.get('success'):
        return Response(result, status=status.HTTP_200_OK)
    return Response(result, status=status.HTTP_400_BAD_REQUEST if 'not found' in result.get('error', '') else status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_chat_session(request):
    session = ChatSession.objects.create(user=request.user)
    return Response({'session_id': str(session.id)}, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def chat_session_messages(request, session_id):
    chat_session_messages.throttle_scope = 'ai'
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        msgs = session.messages.order_by('created_at').values('role', 'content', 'created_at')
        return Response({'messages': list(msgs)}, status=status.HTTP_200_OK)

    # POST: send a message using ai_chat logic but fixed session
    request.data._mutable = True if hasattr(request.data, '_mutable') else False
    request.data['session_id'] = str(session.id)
    return ai_chat(request)