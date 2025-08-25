#!/usr/bin/env python3
"""
Test script for smart AI-powered table reservation
"""
import requests
import json
from datetime import date, timedelta

# Configuration
BASE_URL = "http://127.0.0.1:8000"
TEST_PHONE = "+1234567890"
TEST_PASSWORD = "password123"

def get_auth_token():
    """Get authentication token for testing"""
    login_data = {
        "phone": TEST_PHONE,
        "password": TEST_PASSWORD
    }
    
    response = requests.post(f"{BASE_URL}/api/accounts/login/", json=login_data)
    if response.status_code == 200:
        return response.json().get("access")
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None

def test_smart_reservation():
    """Test smart AI-powered reservation creation"""
    print("🤖 Testing Smart AI-Powered Table Reservation")
    print("=" * 50)
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Get available restaurants
    print("\n📍 Getting available restaurants...")
    restaurants_response = requests.get(f"{BASE_URL}/api/restaurants/", headers=headers)
    
    if restaurants_response.status_code != 200:
        print(f"❌ Failed to get restaurants: {restaurants_response.status_code}")
        return
    
    restaurants = restaurants_response.json()
    if not restaurants:
        print("❌ No restaurants available")
        return
    
    restaurant = restaurants[0]
    restaurant_id = restaurant['id']
    print(f"✅ Using restaurant: {restaurant['name']} (ID: {restaurant_id})")
    
    # Test smart reservation
    tomorrow = date.today() + timedelta(days=1)
    reservation_data = {
        "selection_type": "smart",
        "party_size": 2,
        "date": tomorrow.strftime("%Y-%m-%d"),
        "time": "19:00",
        "duration_hours": 2,
        "special_requests": "Window seat if possible",
        "special_occasion": "anniversary",
        "user_preferences": {
            "quiet_area": True,
            "window_seat": True,
            "romantic_setting": True
        }
    }
    
    print(f"\n🎯 Creating smart reservation...")
    print(f"   Party size: {reservation_data['party_size']}")
    print(f"   Date: {reservation_data['date']}")
    print(f"   Time: {reservation_data['time']}")
    print(f"   Special occasion: {reservation_data['special_occasion']}")
    print(f"   Preferences: {reservation_data['user_preferences']}")
    
    response = requests.post(
        f"{BASE_URL}/api/restaurants/{restaurant_id}/reserve/",
        headers=headers,
        json=reservation_data
    )
    
    print(f"\n📊 Response Status: {response.status_code}")
    
    if response.status_code == 201:
        result = response.json()
        print("✅ Smart reservation created successfully!")
        print(f"   Reservation ID: {result['reservation']['id']}")
        print(f"   Table: {result['reservation']['table']['number']} (Capacity: {result['reservation']['table']['capacity']})")
        print(f"   Status: {result['reservation']['status']}")
        
        # Check if AI selection info is included
        if 'ai_selection' in result:
            ai_info = result['ai_selection']
            print(f"\n🤖 AI Selection Details:")
            print(f"   Method: {ai_info['method']}")
            print(f"   Confidence: {ai_info['confidence']:.2f}")
            print(f"   Response Time: {ai_info['response_time_ms']}ms")
            print(f"   Reasoning: {ai_info['reasoning']}")
            print(f"   Factors: {', '.join(ai_info['factors_considered'])}")
            
            if ai_info.get('alternative_table_id'):
                print(f"   Alternative Table: {ai_info['alternative_table_id']}")
        else:
            print("ℹ️  No AI selection information returned")
            
    else:
        print(f"❌ Reservation failed: {response.text}")
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")

if __name__ == "__main__":
    test_smart_reservation()