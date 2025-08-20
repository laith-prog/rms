from rest_framework import serializers


class ChatMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)


class RecommendationRequestSerializer(serializers.Serializer):
    # Basic preferences; extend as needed
    category_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list
    )
    vegetarian = serializers.BooleanField(required=False, default=None)
    vegan = serializers.BooleanField(required=False, default=None)
    gluten_free = serializers.BooleanField(required=False, default=None)
    price_max = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    restaurant_id = serializers.IntegerField(required=False)


class MenuRecommendationSerializer(serializers.Serializer):
    """Serializer for AI-powered menu recommendations."""
    restaurant_id = serializers.IntegerField(required=False)
    dietary_restrictions = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
        help_text="e.g., ['vegetarian', 'gluten_free', 'vegan']"
    )
    cuisine_preferences = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
        help_text="e.g., ['italian', 'asian', 'mexican']"
    )
    budget_range = serializers.CharField(
        max_length=20,
        required=False,
        help_text="e.g., 'low', 'medium', 'high' or '$10-20'"
    )
    occasion = serializers.CharField(
        max_length=100,
        required=False,
        help_text="e.g., 'romantic dinner', 'business lunch', 'family meal'"
    )
    party_size = serializers.IntegerField(required=False, min_value=1, max_value=20)
    spice_level = serializers.CharField(
        max_length=20,
        required=False,
        help_text="e.g., 'mild', 'medium', 'spicy'"
    )


class ReservationSuggestionSerializer(serializers.Serializer):
    """Serializer for AI-powered reservation suggestions."""
    restaurant_id = serializers.IntegerField()
    party_size = serializers.IntegerField(min_value=1, max_value=20)
    preferred_date = serializers.DateField()
    preferred_time = serializers.TimeField(required=False)
    occasion = serializers.CharField(
        max_length=100,
        required=False,
        help_text="e.g., 'birthday', 'anniversary', 'business meeting'"
    )
    special_requests = serializers.CharField(
        max_length=500,
        required=False,
        help_text="Any special requirements or preferences"
    )


class SentimentAnalysisSerializer(serializers.Serializer):
    """Serializer for AI-powered sentiment analysis."""
    text = serializers.CharField(max_length=5000)
    context = serializers.ChoiceField(
        choices=[
            ('restaurant_review', 'Restaurant Review'),
            ('customer_feedback', 'Customer Feedback'),
            ('staff_feedback', 'Staff Feedback'),
            ('general', 'General Text')
        ],
        default='restaurant_review'
    )
    restaurant_id = serializers.IntegerField(required=False)
    customer_id = serializers.IntegerField(required=False)