from rest_framework import serializers


class ChatSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    context = serializers.CharField(required=False, allow_blank=True)
    session_id = serializers.UUIDField(required=False)


class MenuRecommendationsSerializer(serializers.Serializer):
    restaurant_id = serializers.IntegerField()
    dietary_preferences = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    dietary_restrictions = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    allergies = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    budget_range = serializers.ChoiceField(choices=['low', 'medium', 'high'], default='medium')
    preferences = serializers.CharField(required=False, allow_blank=True)
    cuisine_type = serializers.CharField(required=False, allow_blank=True)


class ReservationSuggestionsSerializer(serializers.Serializer):
    restaurant_id = serializers.IntegerField()
    party_size = serializers.IntegerField(min_value=1)
    preferred_date = serializers.DateField()
    preferred_time = serializers.TimeField(required=False)
    special_occasion = serializers.CharField(required=False, allow_blank=True)


class SentimentSerializer(serializers.Serializer):
    text = serializers.CharField()
    context = serializers.CharField(required=False, allow_blank=True)


class BasicRecommendationsSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    recommendation_type = serializers.ChoiceField(choices=['restaurants', 'dishes', 'experiences'], default='restaurants')
    location = serializers.CharField(required=False, allow_blank=True)
    preferences = serializers.JSONField(required=False)


class SemanticMenuSearchSerializer(serializers.Serializer):
    query = serializers.CharField()
    restaurant_id = serializers.IntegerField(required=False)


class UpsellRecommendationsSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()


class ReviewsSummarizeSerializer(serializers.Serializer):
    restaurant_id = serializers.IntegerField()
    since = serializers.DateField(required=False)


class PredictWaitTimeSerializer(serializers.Serializer):
    restaurant_id = serializers.IntegerField()
    party_size = serializers.IntegerField(min_value=1)
    time = serializers.TimeField()