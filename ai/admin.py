from django.contrib import admin
from .models import ChatSession, ChatMessage, ReviewAnalysis, RecommendationLog, TableSelectionLog


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'restaurant', 'topic', 'created_at')
    list_filter = ('created_at', 'restaurant')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'topic')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'content_preview', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content', 'session__user__email')
    readonly_fields = ('created_at',)
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(ReviewAnalysis)
class ReviewAnalysisAdmin(admin.ModelAdmin):
    list_display = ('review', 'sentiment', 'confidence', 'created_at')
    list_filter = ('sentiment', 'created_at')
    search_fields = ('review__customer__email', 'review__restaurant__name', 'summary')
    readonly_fields = ('created_at',)


@admin.register(RecommendationLog)
class RecommendationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'context', 'accepted', 'created_at')
    list_filter = ('context', 'accepted', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at',)


@admin.register(TableSelectionLog)
class TableSelectionLogAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'selection_method', 'selected_table', 'ai_confidence', 'ai_success', 'created_at')
    list_filter = ('selection_method', 'ai_success', 'created_at', 'restaurant')
    search_fields = ('reservation__customer__email', 'restaurant__name', 'selected_table__table_number')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('reservation', 'restaurant', 'user', 'created_at')
        }),
        ('Selection Details', {
            'fields': ('selection_method', 'selected_table', 'available_tables_count', 'available_tables_data')
        }),
        ('AI Response', {
            'fields': ('ai_reasoning', 'ai_confidence', 'ai_factors_considered', 'ai_alternative_table_id', 'ai_response_time_ms', 'ai_success', 'ai_error_message')
        }),
        ('Request Context', {
            'fields': ('party_size', 'reservation_date', 'reservation_time', 'duration_hours', 'special_occasion', 'user_preferences')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('reservation', 'restaurant', 'user', 'selected_table')