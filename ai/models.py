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
        ('table_selection', 'table_selection'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    context = models.CharField(max_length=20, choices=CONTEXT_CHOICES)
    input_payload = models.JSONField()
    output = models.JSONField()
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RecommendationLog {self.id} - {self.context}"


class TableSelectionLog(models.Model):
    """
    Tracks AI-powered table selection decisions for analysis and improvement
    """
    SELECTION_METHOD_CHOICES = (
        ('ai', 'AI Selection'),
        ('random', 'Random Fallback'),
        ('error_fallback', 'Error Fallback'),
    )
    
    reservation = models.OneToOneField('restaurants.Reservation', on_delete=models.CASCADE, related_name='ai_selection_log')
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Selection details
    selection_method = models.CharField(max_length=20, choices=SELECTION_METHOD_CHOICES)
    selected_table = models.ForeignKey('restaurants.Table', on_delete=models.CASCADE)
    available_tables_count = models.IntegerField()
    available_tables_data = models.JSONField()  # Store table options that were available
    
    # AI response details
    ai_reasoning = models.TextField(blank=True, null=True)
    ai_confidence = models.FloatField(default=0.0)
    ai_factors_considered = models.JSONField(default=list)
    ai_alternative_table_id = models.IntegerField(null=True, blank=True)
    
    # Request context
    party_size = models.IntegerField()
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    duration_hours = models.IntegerField()
    special_occasion = models.CharField(max_length=100, blank=True, null=True)
    user_preferences = models.JSONField(default=dict)
    
    # Performance tracking
    ai_response_time_ms = models.IntegerField(null=True, blank=True)
    ai_success = models.BooleanField(default=True)
    ai_error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"TableSelection {self.reservation_id} - {self.selection_method} - Table {self.selected_table.table_number}"