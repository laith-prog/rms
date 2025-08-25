from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FCMTokenViewSet, NotificationTemplateViewSet, NotificationLogViewSet,
    TopicSubscriptionViewSet, NotificationViewSet
)

router = DefaultRouter()
router.register(r'fcm-tokens', FCMTokenViewSet, basename='fcm-tokens')
router.register(r'templates', NotificationTemplateViewSet, basename='notification-templates')
router.register(r'logs', NotificationLogViewSet, basename='notification-logs')
router.register(r'topics', TopicSubscriptionViewSet, basename='topic-subscriptions')
router.register(r'send', NotificationViewSet, basename='send-notifications')

urlpatterns = [
    path('', include(router.urls)),
]