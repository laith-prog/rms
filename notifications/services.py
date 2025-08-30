"""
Notification service for handling push notifications in the RMS system
"""
import logging
from typing import List, Dict, Optional, Union
from django.contrib.auth import get_user_model
from django.db import transaction
from firebase_service import firebase_service
from .models import FCMToken, NotificationTemplate, NotificationLog, TopicSubscription

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service class for handling push notifications
    """
    
    def __init__(self):
        self.firebase_service = firebase_service
    
    def register_fcm_token(self, user: User, token: str, device_type: str = 'android', device_id: str = None) -> FCMToken:
        """
        Register or update FCM token for a user
        
        Args:
            user: User instance
            token: FCM registration token
            device_type: Type of device (android, ios, web)
            device_id: Optional device identifier
            
        Returns:
            FCMToken instance
        """
        try:
            # Try to get existing token
            fcm_token, created = FCMToken.objects.get_or_create(
                user=user,
                token=token,
                defaults={
                    'device_type': device_type,
                    'device_id': device_id,
                    'is_active': True
                }
            )
            
            if not created:
                # Update existing token
                fcm_token.device_type = device_type
                fcm_token.device_id = device_id
                fcm_token.is_active = True
                fcm_token.save()
            
            logger.info(f"FCM token registered for user {user.username}")
            return fcm_token
            
        except Exception as e:
            logger.error(f"Failed to register FCM token: {e}")
            raise
    
    def get_user_tokens(self, user: User, active_only: bool = True) -> List[str]:
        """
        Get all FCM tokens for a user.
        Combines the legacy User.fcm_token field and FCMToken table, de-duplicated.
        """
        tokens: List[str] = []
        # Legacy single token on user
        if getattr(user, 'fcm_token', None):
            tokens.append(user.fcm_token)
        # Tokens from FCMToken model
        qs = FCMToken.objects.filter(user=user)
        if active_only:
            qs = qs.filter(is_active=True)
        tokens.extend(list(qs.values_list('token', flat=True)))
        # De-duplicate while preserving order
        seen = set()
        unique_tokens: List[str] = []
        for t in tokens:
            if t and t not in seen:
                seen.add(t)
                unique_tokens.append(t)
        return unique_tokens
    
    def get_users_tokens(self, users: List[User], active_only: bool = True) -> List[str]:
        """
        Get all FCM tokens for multiple users using get_user_tokens.
        """
        tokens: List[str] = []
        for user in users:
            tokens.extend(self.get_user_tokens(user, active_only=active_only))
        # De-duplicate across all users
        seen = set()
        unique_tokens: List[str] = []
        for t in tokens:
            if t and t not in seen:
                seen.add(t)
                unique_tokens.append(t)
        return unique_tokens
    
    def send_notification_to_user(
        self,
        user: User,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
        notification_type: str = 'general',
        order=None,
        reservation=None
    ) -> Dict[str, Union[int, List[str]]]:
        """
        Send notification to a specific user
        
        Args:
            user: User to send notification to
            title: Notification title
            body: Notification body
            data: Optional custom data payload
            image_url: Optional image URL
            notification_type: Type of notification for logging
            order: Optional order instance for context
            reservation: Optional reservation instance for context
            
        Returns:
            dict: Results with success_count, failure_count, and failed_tokens
        """
        tokens = self.get_user_tokens(user)
        if not tokens:
            logger.warning(f"No FCM tokens found for user {user.username}")
            return {"success_count": 0, "failure_count": 0, "failed_tokens": []}
        
        # Log notifications
        logs = []
        for token in tokens:
            log = NotificationLog.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                body=body,
                data=data or {},
                fcm_token=token,
                order=order,
                reservation=reservation
            )
            logs.append(log)
        
        # Send notification
        if len(tokens) == 1:
            success = self.firebase_service.send_notification(
                token=tokens[0],
                title=title,
                body=body,
                data=data,
                image_url=image_url
            )
            
            # Update log
            log = logs[0]
            if success:
                log.mark_as_sent()
                return {"success_count": 1, "failure_count": 0, "failed_tokens": []}
            else:
                log.mark_as_failed("Failed to send notification")
                return {"success_count": 0, "failure_count": 1, "failed_tokens": tokens}
        else:
            result = self.firebase_service.send_multicast_notification(
                tokens=tokens,
                title=title,
                body=body,
                data=data,
                image_url=image_url
            )
            
            # Update logs
            failed_tokens = result.get('failed_tokens', [])
            for log in logs:
                if log.fcm_token in failed_tokens:
                    log.mark_as_failed("Failed to send notification")
                else:
                    log.mark_as_sent()
            
            return result
    
    def send_notification_to_users(
        self,
        users: List[User],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
        notification_type: str = 'general'
    ) -> Dict[str, Union[int, List[str]]]:
        """
        Send notification to multiple users
        
        Args:
            users: List of users to send notification to
            title: Notification title
            body: Notification body
            data: Optional custom data payload
            image_url: Optional image URL
            notification_type: Type of notification for logging
            
        Returns:
            dict: Results with success_count, failure_count, and failed_tokens
        """
        tokens = self.get_users_tokens(users)
        if not tokens:
            logger.warning("No FCM tokens found for provided users")
            return {"success_count": 0, "failure_count": 0, "failed_tokens": []}
        
        # Create user-token mapping for logging
        user_tokens = {}
        for user in users:
            user_tokens[user.id] = self.get_user_tokens(user)
        
        # Log notifications
        logs = []
        for user in users:
            for token in user_tokens[user.id]:
                log = NotificationLog.objects.create(
                    user=user,
                    notification_type=notification_type,
                    title=title,
                    body=body,
                    data=data or {},
                    fcm_token=token
                )
                logs.append(log)
        
        # Send multicast notification
        result = self.firebase_service.send_multicast_notification(
            tokens=tokens,
            title=title,
            body=body,
            data=data,
            image_url=image_url
        )
        
        # Update logs
        failed_tokens = result.get('failed_tokens', [])
        for log in logs:
            if log.fcm_token in failed_tokens:
                log.mark_as_failed("Failed to send notification")
            else:
                log.mark_as_sent()
        
        return result
    
    def send_topic_notification(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> bool:
        """
        Send notification to a topic
        
        Args:
            topic: Topic name
            title: Notification title
            body: Notification body
            data: Optional custom data payload
            image_url: Optional image URL
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.firebase_service.send_topic_notification(
            topic=topic,
            title=title,
            body=body,
            data=data,
            image_url=image_url
        )
    
    def send_templated_notification(
        self,
        template_name: str,
        notification_type: str,
        context: Dict[str, str],
        users: Optional[List[User]] = None,
        user: Optional[User] = None,
        topic: Optional[str] = None,
        order=None,
        reservation=None
    ) -> Union[Dict[str, Union[int, List[str]]], bool]:
        """
        Send notification using a template
        
        Args:
            template_name: Name of the notification template
            notification_type: Type of notification
            context: Context variables for template rendering
            users: List of users to send to (for multicast)
            user: Single user to send to
            topic: Topic to send to
            order: Optional order instance for context
            reservation: Optional reservation instance for context
            
        Returns:
            Result of the notification sending operation
        """
        try:
            template = NotificationTemplate.objects.get(
                name=template_name,
                notification_type=notification_type,
                is_active=True
            )
        except NotificationTemplate.DoesNotExist:
            logger.error(f"Template not found: {template_name} ({notification_type})")
            return {"success_count": 0, "failure_count": 0, "failed_tokens": []}
        
        # Render template
        title = template.render_title(context)
        body = template.render_body(context)
        data = template.render_data(context)
        
        # Send notification
        if topic:
            return self.send_topic_notification(
                topic=topic,
                title=title,
                body=body,
                data=data,
                image_url=template.image_url
            )
        elif user:
            return self.send_notification_to_user(
                user=user,
                title=title,
                body=body,
                data=data,
                image_url=template.image_url,
                notification_type=notification_type,
                order=order,
                reservation=reservation
            )
        elif users:
            return self.send_notification_to_users(
                users=users,
                title=title,
                body=body,
                data=data,
                image_url=template.image_url,
                notification_type=notification_type
            )
        else:
            logger.error("No target specified for templated notification")
            return {"success_count": 0, "failure_count": 0, "failed_tokens": []}
    
    def subscribe_user_to_topic(self, user: User, topic: str) -> bool:
        """
        Subscribe user to a notification topic
        
        Args:
            user: User to subscribe
            topic: Topic name
            
        Returns:
            bool: True if successful, False otherwise
        """
        tokens = self.get_user_tokens(user)
        if not tokens:
            logger.warning(f"No FCM tokens found for user {user.username}")
            return False
        
        # Subscribe to Firebase topic
        result = self.firebase_service.subscribe_to_topic(tokens, topic)
        
        # Update database
        subscription, created = TopicSubscription.objects.get_or_create(
            user=user,
            topic=topic,
            defaults={'is_subscribed': True}
        )
        
        if not created and not subscription.is_subscribed:
            subscription.resubscribe()
        
        return result['success_count'] > 0
    
    def unsubscribe_user_from_topic(self, user: User, topic: str) -> bool:
        """
        Unsubscribe user from a notification topic
        
        Args:
            user: User to unsubscribe
            topic: Topic name
            
        Returns:
            bool: True if successful, False otherwise
        """
        tokens = self.get_user_tokens(user)
        if not tokens:
            logger.warning(f"No FCM tokens found for user {user.username}")
            return False
        
        # Unsubscribe from Firebase topic
        result = self.firebase_service.unsubscribe_from_topic(tokens, topic)
        
        # Update database
        try:
            subscription = TopicSubscription.objects.get(user=user, topic=topic)
            subscription.unsubscribe()
        except TopicSubscription.DoesNotExist:
            pass
        
        return result['success_count'] > 0
    
    def deactivate_token(self, token: str) -> bool:
        """
        Deactivate an FCM token (e.g., when it's invalid)
        
        Args:
            token: FCM token to deactivate
            
        Returns:
            bool: True if token was found and deactivated
        """
        try:
            fcm_token = FCMToken.objects.get(token=token)
            fcm_token.is_active = False
            fcm_token.save()
            logger.info(f"Deactivated FCM token: {token[:20]}...")
            return True
        except FCMToken.DoesNotExist:
            logger.warning(f"FCM token not found for deactivation: {token[:20]}...")
            return False


# Global instance
notification_service = NotificationService()