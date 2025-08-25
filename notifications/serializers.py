from rest_framework import serializers
from .models import FCMToken, NotificationTemplate, NotificationLog, TopicSubscription


class FCMTokenSerializer(serializers.ModelSerializer):
    """Serializer for FCM Token registration"""
    
    class Meta:
        model = FCMToken
        fields = ['id', 'token', 'device_type', 'device_id', 'is_active', 'created_at', 'last_used']
        read_only_fields = ['id', 'created_at', 'last_used']

    def create(self, validated_data):
        # Get the user from the request context
        user = self.context['request'].user
        validated_data['user'] = user
        
        # Check if token already exists for this user
        token = validated_data.get('token')
        existing_token = FCMToken.objects.filter(user=user, token=token).first()
        
        if existing_token:
            # Update existing token
            for attr, value in validated_data.items():
                setattr(existing_token, attr, value)
            existing_token.save()
            return existing_token
        
        return super().create(validated_data)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for Notification Templates"""
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'notification_type', 'title_template', 
            'body_template', 'data_template', 'image_url', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for Notification Logs"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'user', 'user_username', 'notification_type', 
            'title', 'body', 'data', 'status', 'error_message',
            'firebase_message_id', 'sent_at', 'delivered_at',
            'order', 'reservation'
        ]
        read_only_fields = [
            'id', 'user_username', 'firebase_message_id', 
            'sent_at', 'delivered_at'
        ]


class TopicSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Topic Subscriptions"""
    
    class Meta:
        model = TopicSubscription
        fields = [
            'id', 'topic', 'is_subscribed', 
            'subscribed_at', 'unsubscribed_at'
        ]
        read_only_fields = ['id', 'subscribed_at', 'unsubscribed_at']

    def create(self, validated_data):
        # Get the user from the request context
        user = self.context['request'].user
        validated_data['user'] = user
        
        # Check if subscription already exists
        topic = validated_data.get('topic')
        existing_subscription = TopicSubscription.objects.filter(user=user, topic=topic).first()
        
        if existing_subscription:
            # Update existing subscription
            existing_subscription.is_subscribed = validated_data.get('is_subscribed', True)
            if existing_subscription.is_subscribed:
                existing_subscription.resubscribe()
            else:
                existing_subscription.unsubscribe()
            return existing_subscription
        
        return super().create(validated_data)


class SendNotificationSerializer(serializers.Serializer):
    """Serializer for sending custom notifications"""
    title = serializers.CharField(max_length=255)
    body = serializers.CharField()
    data = serializers.JSONField(required=False, default=dict)
    image_url = serializers.URLField(required=False, allow_blank=True)
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of user IDs to send notification to. If not provided, sends to all users."
    )
    topic = serializers.CharField(
        required=False,
        help_text="Topic to send notification to instead of specific users"
    )

    def validate(self, data):
        if not data.get('user_ids') and not data.get('topic'):
            raise serializers.ValidationError(
                "Either 'user_ids' or 'topic' must be provided"
            )
        return data


class TestNotificationSerializer(serializers.Serializer):
    """Serializer for sending test notifications"""
    title = serializers.CharField(max_length=255, default="Test Notification")
    body = serializers.CharField(default="This is a test notification from your RMS app!")
    data = serializers.JSONField(required=False, default=dict)