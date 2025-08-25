from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import FCMToken, NotificationTemplate, NotificationLog, TopicSubscription
from .serializers import (
    FCMTokenSerializer, NotificationTemplateSerializer, NotificationLogSerializer,
    TopicSubscriptionSerializer, SendNotificationSerializer, TestNotificationSerializer
)
from .services import notification_service

User = get_user_model()


class FCMTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing FCM tokens
    """
    serializer_class = FCMTokenSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return FCMToken.objects.filter(user=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Register or update FCM token for the authenticated user",
        request_body=FCMTokenSerializer,
        responses={
            201: FCMTokenSerializer,
            400: "Bad Request"
        }
    )
    def create(self, request, *args, **kwargs):
        """Register or update FCM token"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Register token using the service
        fcm_token = notification_service.register_fcm_token(
            user=request.user,
            token=serializer.validated_data['token'],
            device_type=serializer.validated_data.get('device_type', 'android'),
            device_id=serializer.validated_data.get('device_id')
        )
        
        response_serializer = self.get_serializer(fcm_token)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(
        operation_description="Send a test notification to the authenticated user",
        request_body=TestNotificationSerializer,
        responses={
            200: openapi.Response(
                description="Test notification sent",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'result': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['post'])
    def test_notification(self, request):
        """Send a test notification to the authenticated user"""
        serializer = TestNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = notification_service.send_notification_to_user(
            user=request.user,
            title=serializer.validated_data['title'],
            body=serializer.validated_data['body'],
            data=serializer.validated_data.get('data', {}),
            notification_type='test'
        )
        
        return Response({
            'success': result['success_count'] > 0,
            'message': f"Sent to {result['success_count']} devices, failed on {result['failure_count']} devices",
            'result': result
        })


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification templates (Admin only)
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAdminUser]
    
    @swagger_auto_schema(
        operation_description="Test a notification template",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'context': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description="Context variables for template rendering"
                ),
                'user_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="User ID to send test notification to"
                )
            },
            required=['context', 'user_id']
        ),
        responses={
            200: openapi.Response(
                description="Template test result",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'rendered_title': openapi.Schema(type=openapi.TYPE_STRING),
                        'rendered_body': openapi.Schema(type=openapi.TYPE_STRING),
                        'rendered_data': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'result': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            )
        }
    )
    @action(detail=True, methods=['post'])
    def test_template(self, request, pk=None):
        """Test a notification template"""
        template = self.get_object()
        context = request.data.get('context', {})
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Render template
        rendered_title = template.render_title(context)
        rendered_body = template.render_body(context)
        rendered_data = template.render_data(context)
        
        # Send test notification
        result = notification_service.send_notification_to_user(
            user=user,
            title=rendered_title,
            body=rendered_body,
            data=rendered_data,
            image_url=template.image_url,
            notification_type=f"test_{template.notification_type}"
        )
        
        return Response({
            'success': result['success_count'] > 0,
            'rendered_title': rendered_title,
            'rendered_body': rendered_body,
            'rendered_data': rendered_data,
            'result': result
        })


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing notification logs
    """
    serializer_class = NotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return NotificationLog.objects.all().order_by('-sent_at')
        return NotificationLog.objects.filter(user=self.request.user).order_by('-sent_at')


class TopicSubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing topic subscriptions
    """
    serializer_class = TopicSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return TopicSubscription.objects.filter(user=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Subscribe to a notification topic",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'topic': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['order_updates', 'restaurant_news', 'promotions', 'system_alerts']
                )
            },
            required=['topic']
        ),
        responses={
            200: openapi.Response(
                description="Subscription result",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        """Subscribe to a notification topic"""
        topic = request.data.get('topic')
        if not topic:
            return Response(
                {'error': 'topic is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = notification_service.subscribe_user_to_topic(request.user, topic)
        
        return Response({
            'success': success,
            'message': f"{'Successfully subscribed to' if success else 'Failed to subscribe to'} topic: {topic}"
        })
    
    @swagger_auto_schema(
        operation_description="Unsubscribe from a notification topic",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'topic': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['order_updates', 'restaurant_news', 'promotions', 'system_alerts']
                )
            },
            required=['topic']
        ),
        responses={
            200: openapi.Response(
                description="Unsubscription result",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['post'])
    def unsubscribe(self, request):
        """Unsubscribe from a notification topic"""
        topic = request.data.get('topic')
        if not topic:
            return Response(
                {'error': 'topic is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = notification_service.unsubscribe_user_from_topic(request.user, topic)
        
        return Response({
            'success': success,
            'message': f"{'Successfully unsubscribed from' if success else 'Failed to unsubscribe from'} topic: {topic}"
        })


class NotificationViewSet(viewsets.ViewSet):
    """
    ViewSet for sending notifications (Admin only)
    """
    permission_classes = [permissions.IsAdminUser]
    
    @swagger_auto_schema(
        operation_description="Send custom notification to users or topic",
        request_body=SendNotificationSerializer,
        responses={
            200: openapi.Response(
                description="Notification sent",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'result': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['post'])
    def send_notification(self, request):
        """Send custom notification"""
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        if data.get('topic'):
            # Send to topic
            success = notification_service.send_topic_notification(
                topic=data['topic'],
                title=data['title'],
                body=data['body'],
                data=data.get('data', {}),
                image_url=data.get('image_url')
            )
            
            return Response({
                'success': success,
                'message': f"{'Successfully sent' if success else 'Failed to send'} notification to topic: {data['topic']}"
            })
        
        else:
            # Send to specific users
            user_ids = data.get('user_ids', [])
            if not user_ids:
                # Send to all users
                users = User.objects.filter(is_active=True)
            else:
                users = User.objects.filter(id__in=user_ids, is_active=True)
            
            result = notification_service.send_notification_to_users(
                users=list(users),
                title=data['title'],
                body=data['body'],
                data=data.get('data', {}),
                image_url=data.get('image_url'),
                notification_type='admin_broadcast'
            )
            
            return Response({
                'success': result['success_count'] > 0,
                'message': f"Sent to {result['success_count']} devices, failed on {result['failure_count']} devices",
                'result': result
            })
