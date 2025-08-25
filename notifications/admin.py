from django.contrib import admin
from django.utils.html import format_html
from .models import FCMToken, NotificationTemplate, NotificationLog, TopicSubscription


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_type', 'token_preview', 'is_active', 'created_at', 'last_used']
    list_filter = ['device_type', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'token']
    readonly_fields = ['created_at', 'updated_at']
    
    def token_preview(self, obj):
        return f"{obj.token[:20]}..." if obj.token else ""
    token_preview.short_description = "Token Preview"


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'notification_type', 'is_active', 'created_at']
    list_filter = ['notification_type', 'is_active', 'created_at']
    search_fields = ['name', 'title_template', 'body_template']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'notification_type', 'is_active')
        }),
        ('Template Content', {
            'fields': ('title_template', 'body_template', 'data_template', 'image_url')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'status', 'sent_at']
    list_filter = ['notification_type', 'status', 'sent_at']
    search_fields = ['user__username', 'user__email', 'title', 'body']
    readonly_fields = ['sent_at', 'delivered_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'notification_type', 'status')
        }),
        ('Content', {
            'fields': ('title', 'body', 'data')
        }),
        ('Technical Details', {
            'fields': ('fcm_token_preview', 'firebase_message_id', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Context', {
            'fields': ('order', 'reservation'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'delivered_at'),
            'classes': ('collapse',)
        })
    )
    
    def fcm_token_preview(self, obj):
        return f"{obj.fcm_token[:20]}..." if obj.fcm_token else ""
    fcm_token_preview.short_description = "FCM Token Preview"


@admin.register(TopicSubscription)
class TopicSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'topic', 'subscription_status', 'subscribed_at']
    list_filter = ['topic', 'is_subscribed', 'subscribed_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['subscribed_at', 'unsubscribed_at']
    
    def subscription_status(self, obj):
        if obj.is_subscribed:
            return format_html('<span style="color: green;">✓ Subscribed</span>')
        else:
            return format_html('<span style="color: red;">✗ Unsubscribed</span>')
    subscription_status.short_description = "Status"
