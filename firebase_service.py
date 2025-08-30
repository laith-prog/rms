"""
Firebase Cloud Messaging (FCM) Service for sending push notifications
"""
import os
import json
import logging
from typing import List, Dict, Optional, Union
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)


class FirebaseService:
    """
    Service class for handling Firebase Cloud Messaging operations
    """
    
    def __init__(self):
        self._app = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Try to get service account key from environment variable first
                service_account_key = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
                service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
                
                if service_account_key:
                    # Parse the JSON string from environment variable
                    try:
                        service_account_info = json.loads(service_account_key)
                        cred = credentials.Certificate(service_account_info)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in FIREBASE_SERVICE_ACCOUNT_KEY: {e}")
                        return
                        
                elif service_account_path and os.path.exists(service_account_path):
                    # Use file path
                    cred = credentials.Certificate(service_account_path)
                    
                else:
                    logger.error("Neither FIREBASE_SERVICE_ACCOUNT_KEY nor FIREBASE_SERVICE_ACCOUNT_PATH is set or valid")
                    return
                
                # Initialize Firebase with service account
                self._app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                self._app = firebase_admin.get_app()
                logger.info("Firebase Admin SDK already initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self._app = None
    
    def is_initialized(self) -> bool:
        """Check if Firebase is properly initialized"""
        return self._app is not None
    
    def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> bool:
        """
        Send a push notification to a single device
        
        Args:
            token: FCM registration token
            title: Notification title
            body: Notification body
            data: Optional custom data payload
            image_url: Optional image URL for rich notifications
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized. Cannot send notification.")
            return False
        
        try:
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Build message
            message = messaging.Message(
                notification=notification,
                data=data or {},
                token=token,
                android=messaging.AndroidConfig(
                    notification=messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#FF6B35'  # Your app's primary color
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            badge=1,
                            sound='default'
                        )
                    )
                )
            )
            
            # Send message
            response = messaging.send(message)
            logger.info(f"Successfully sent message: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    def send_multicast_notification(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Union[int, List[str]]]:
        """
        Send a push notification to multiple devices
        
        Args:
            tokens: List of FCM registration tokens
            title: Notification title
            body: Notification body
            data: Optional custom data payload
            image_url: Optional image URL for rich notifications
            
        Returns:
            dict: Results with success_count, failure_count, and failed_tokens
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized. Cannot send notifications.")
            return {"success_count": 0, "failure_count": len(tokens), "failed_tokens": tokens}
        
        if not tokens:
            logger.warning("No tokens provided for multicast notification")
            return {"success_count": 0, "failure_count": 0, "failed_tokens": []}
        
        try:
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Build multicast message
            message = messaging.MulticastMessage(
                notification=notification,
                data=data or {},
                tokens=tokens,
                android=messaging.AndroidConfig(
                    notification=messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#FF6B35'  # Your app's primary color
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            badge=1,
                            sound='default'
                        )
                    )
                )
            )
            
            # Send multicast message
            response = messaging.send_each_for_multicast(message)
            
            # Collect failed tokens
            failed_tokens = []
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        failed_tokens.append(tokens[idx])
                        logger.error(f"Failed to send to token {tokens[idx]}: {resp.exception}")
            
            logger.info(f"Multicast notification sent. Success: {response.success_count}, Failed: {response.failure_count}")
            
            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "failed_tokens": failed_tokens
            }
            
        except Exception as e:
            logger.error(f"Failed to send multicast notification: {e}")
            return {"success_count": 0, "failure_count": len(tokens), "failed_tokens": tokens}
    
    def send_topic_notification(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> bool:
        """
        Send a push notification to a topic
        
        Args:
            topic: Topic name (e.g., 'order_updates', 'restaurant_news')
            title: Notification title
            body: Notification body
            data: Optional custom data payload
            image_url: Optional image URL for rich notifications
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized. Cannot send topic notification.")
            return False
        
        try:
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Build message
            message = messaging.Message(
                notification=notification,
                data=data or {},
                topic=topic,
                android=messaging.AndroidConfig(
                    notification=messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#FF6B35'  # Your app's primary color
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            badge=1,
                            sound='default'
                        )
                    )
                )
            )
            
            # Send message
            response = messaging.send(message)
            logger.info(f"Successfully sent topic notification to '{topic}': {response}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send topic notification: {e}")
            return False
    
    def subscribe_to_topic(self, tokens: List[str], topic: str) -> Dict[str, int]:
        """
        Subscribe tokens to a topic
        
        Args:
            tokens: List of FCM registration tokens
            topic: Topic name
            
        Returns:
            dict: Results with success_count and failure_count
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized. Cannot subscribe to topic.")
            return {"success_count": 0, "failure_count": len(tokens)}
        
        try:
            response = messaging.subscribe_to_topic(tokens, topic)
            logger.info(f"Topic subscription results - Success: {response.success_count}, Failed: {response.failure_count}")
            return {"success_count": response.success_count, "failure_count": response.failure_count}
            
        except Exception as e:
            logger.error(f"Failed to subscribe to topic: {e}")
            return {"success_count": 0, "failure_count": len(tokens)}
    
    def unsubscribe_from_topic(self, tokens: List[str], topic: str) -> Dict[str, int]:
        """
        Unsubscribe tokens from a topic
        
        Args:
            tokens: List of FCM registration tokens
            topic: Topic name
            
        Returns:
            dict: Results with success_count and failure_count
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized. Cannot unsubscribe from topic.")
            return {"success_count": 0, "failure_count": len(tokens)}
        
        try:
            response = messaging.unsubscribe_from_topic(tokens, topic)
            logger.info(f"Topic unsubscription results - Success: {response.success_count}, Failed: {response.failure_count}")
            return {"success_count": response.success_count, "failure_count": response.failure_count}
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from topic: {e}")
            return {"success_count": 0, "failure_count": len(tokens)}


# Global instance
firebase_service = FirebaseService()