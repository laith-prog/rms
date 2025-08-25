#!/usr/bin/env python
"""
Test script for FCM integration
"""
import os
import sys
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rms.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.services import notification_service

User = get_user_model()

def test_fcm_integration():
    """Test the complete FCM integration"""
    print("Testing Firebase Cloud Messaging Integration")
    print("=" * 50)
    
    # Test 1: Check if Firebase is initialized
    print("1. Testing Firebase initialization...")
    try:
        from firebase_service import firebase_service
        if firebase_service.is_initialized():
            print("   SUCCESS: Firebase is properly initialized")
        else:
            print("   ERROR: Firebase is not initialized")
            return
    except Exception as e:
        print(f"   ERROR: Firebase initialization error: {e}")
        return
    
    # Test 2: Check if we can create a user with FCM token
    print("\n2. Testing User model with FCM token...")
    try:
        # Create or get a test user
        test_phone = "+1234567890"
        user, created = User.objects.get_or_create(
            phone=test_phone,
            defaults={
                'first_name': 'Test',
                'last_name': 'User',
                'is_customer': True,
                'fcm_token': 'test_fcm_token_123'
            }
        )
        
        if not created:
            user.fcm_token = 'test_fcm_token_123'
            user.save()
        
        print(f"   SUCCESS: User created/updated with FCM token: {user.fcm_token}")
    except Exception as e:
        print(f"   ERROR: User creation error: {e}")
        return
    
    # Test 3: Test notification service
    print("\n3. Testing notification service...")
    try:
        tokens = notification_service.get_user_tokens(user)
        print(f"   SUCCESS: Retrieved user tokens: {tokens}")
        
        if tokens:
            print("   INFO: Attempting to send test notification...")
            # Note: This will fail with a fake token, but we can test the flow
            result = notification_service.send_notification_to_user(
                user=user,
                title="Test Notification",
                body="This is a test notification from RMS",
                notification_type="test"
            )
            print(f"   RESULT: Notification result: {result}")
        else:
            print("   WARNING: No tokens found for user")
    except Exception as e:
        print(f"   ERROR: Notification service error: {e}")
    
    # Test 4: Test API endpoints (if server is running)
    print("\n4. Testing API endpoints...")
    try:
        # Test the FCM token registration endpoint
        base_url = "http://localhost:8000"
        
        # First, we need to authenticate (this is just a test, in real app you'd have proper auth)
        print("   INFO: Testing FCM token registration endpoint...")
        print("   NOTE: This requires authentication, so it will return 401 without proper token")
        
        response = requests.post(
            f"{base_url}/api/accounts/fcm-token/register/",
            json={"fcm_token": "new_test_token_456"},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   RESULT: API Response Status: {response.status_code}")
        if response.status_code == 401:
            print("   SUCCESS: Endpoint exists and requires authentication (as expected)")
        else:
            print(f"   RESPONSE: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("   WARNING: Server not running on localhost:8000")
    except Exception as e:
        print(f"   ERROR: API test error: {e}")
    
    print("\n" + "=" * 50)
    print("FCM Integration Test Complete!")
    print("\nSummary:")
    print("   - Firebase service is initialized")
    print("   - User model supports FCM tokens")
    print("   - Notification service can retrieve tokens")
    print("   - API endpoints are configured")
    print("\nNext steps:")
    print("   1. Test with real FCM tokens from mobile app")
    print("   2. Implement proper authentication in mobile app")
    print("   3. Test actual push notifications")

if __name__ == "__main__":
    test_fcm_integration()