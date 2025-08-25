from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class FCMToken(models.Model):
    """
    Model to store FCM registration tokens for users
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_tokens')
    token = models.TextField(unique=True)
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('android', 'Android'),
            ('ios', 'iOS'),
            ('web', 'Web'),
        ],
        default='android'
    )
    device_id = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'notifications_fcm_token'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['token']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.device_type} - {self.token[:20]}..."

    def mark_as_used(self):
        """Update the last_used timestamp"""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])


class NotificationTemplate(models.Model):
    """
    Model to store notification templates for different types of notifications
    """
    NOTIFICATION_TYPES = [
        ('order_placed', 'Order Placed'),
        ('order_confirmed', 'Order Confirmed'),
        ('order_preparing', 'Order Preparing'),
        ('order_ready', 'Order Ready'),
        ('order_delivered', 'Order Delivered'),
        ('order_cancelled', 'Order Cancelled'),
        ('reservation_confirmed', 'Reservation Confirmed'),
        ('reservation_reminder', 'Reservation Reminder'),
        ('reservation_cancelled', 'Reservation Cancelled'),
        ('payment_success', 'Payment Success'),
        ('payment_failed', 'Payment Failed'),
        ('promotion', 'Promotion'),
        ('general', 'General'),
    ]

    name = models.CharField(max_length=100)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title_template = models.CharField(max_length=255)
    body_template = models.TextField()
    data_template = models.JSONField(default=dict, blank=True)
    image_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications_template'
        unique_together = ['notification_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.notification_type})"

    def render_title(self, context: dict) -> str:
        """Render title template with context variables"""
        try:
            return self.title_template.format(**context)
        except KeyError as e:
            return f"Template error: Missing variable {e}"

    def render_body(self, context: dict) -> str:
        """Render body template with context variables"""
        try:
            return self.body_template.format(**context)
        except KeyError as e:
            return f"Template error: Missing variable {e}"

    def render_data(self, context: dict) -> dict:
        """Render data template with context variables"""
        try:
            rendered_data = {}
            for key, value in self.data_template.items():
                if isinstance(value, str):
                    rendered_data[key] = value.format(**context)
                else:
                    rendered_data[key] = str(value)
            return rendered_data
        except KeyError as e:
            return {"error": f"Template error: Missing variable {e}"}


class NotificationLog(models.Model):
    """
    Model to log sent notifications for tracking and analytics
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_logs')
    notification_type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    fcm_token = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    firebase_message_id = models.CharField(max_length=255, blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(blank=True, null=True)

    # Optional foreign keys for context
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, blank=True, null=True)
    reservation = models.ForeignKey('restaurants.Reservation', on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        db_table = 'notifications_log'
        indexes = [
            models.Index(fields=['user', 'sent_at']),
            models.Index(fields=['notification_type', 'status']),
            models.Index(fields=['sent_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.status}"

    def mark_as_sent(self, firebase_message_id: str = None):
        """Mark notification as sent"""
        self.status = 'sent'
        self.firebase_message_id = firebase_message_id
        self.save(update_fields=['status', 'firebase_message_id'])

    def mark_as_failed(self, error_message: str):
        """Mark notification as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])

    def mark_as_delivered(self):
        """Mark notification as delivered"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])


class TopicSubscription(models.Model):
    """
    Model to track user subscriptions to notification topics
    """
    TOPIC_CHOICES = [
        ('order_updates', 'Order Updates'),
        ('restaurant_news', 'Restaurant News'),
        ('promotions', 'Promotions'),
        ('system_alerts', 'System Alerts'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topic_subscriptions')
    topic = models.CharField(max_length=50, choices=TOPIC_CHOICES)
    is_subscribed = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'notifications_topic_subscription'
        unique_together = ['user', 'topic']

    def __str__(self):
        status = "Subscribed" if self.is_subscribed else "Unsubscribed"
        return f"{self.user.username} - {self.topic} - {status}"

    def unsubscribe(self):
        """Unsubscribe from topic"""
        self.is_subscribed = False
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=['is_subscribed', 'unsubscribed_at'])

    def resubscribe(self):
        """Resubscribe to topic"""
        self.is_subscribed = True
        self.unsubscribed_at = None
        self.save(update_fields=['is_subscribed', 'unsubscribed_at'])
