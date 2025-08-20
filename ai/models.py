import uuid
from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_chat_sessions')
    restaurant = models.ForeignKey('restaurants.Restaurant', null=True, blank=True, on_delete=models.SET_NULL)
    topic = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ChatSession {self.id} - {self.user_id}"


class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ('user', 'user'),
        ('assistant', 'assistant'),
        ('system', 'system'),
    )
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.session_id} - {self.role}"


class ReviewAnalysis(models.Model):
    review = models.OneToOneField('restaurants.Review', on_delete=models.CASCADE, related_name='analysis')
    sentiment = models.CharField(max_length=10)
    confidence = models.FloatField(default=0.0)
    emotions = models.JSONField(default=dict)
    summary = models.TextField(blank=True)
    suggestions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ReviewAnalysis {self.review_id} - {self.sentiment}"


class RecommendationLog(models.Model):
    CONTEXT_CHOICES = (
        ('menu', 'menu'),
        ('upsell', 'upsell'),
        ('semantic', 'semantic'),
        ('basic', 'basic'),
        ('chat', 'chat'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    context = models.CharField(max_length=20, choices=CONTEXT_CHOICES)
    input_payload = models.JSONField()
    output = models.JSONField()
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RecommendationLog {self.id} - {self.context}"