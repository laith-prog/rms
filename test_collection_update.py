#!/usr/bin/env python3
"""
Test script to verify the updated Postman collection with AI features
"""
import json
import requests
from datetime import date, timedelta

# Configuration
BASE_URL = "http://127.0.0.1:8000"
TEST_PHONE = "+1234567890"
TEST_PASSWORD = "password123"

def test_collection_endpoints():
    """Test the key endpoints from the updated collection"""
    print("🧪 Testing Updated Postman Collection Endpoints")
    print("=" * 60)
    
    # Test 1: Login (from Authentication section)
    print("\n1️⃣ Testing Customer Login...")
    login_response = requests.post(f"{BASE_URL}/api/accounts/login/", json={
        "phone": TEST_PHONE,
        "password": TEST_PASSWORD
    })
    
    if login_response.status_code == 200:
        token = login_response.json().get("access")
        print("✅ Login successful")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Test 2: Get Restaurants (from Restaurants section)
        print("\n2️⃣ Testing Get Restaurants...")
        restaurants_response = requests.get(f"{BASE_URL}/api/restaurants/", headers=headers)
        
        if restaurants_response.status_code == 200:
            restaurants = restaurants_response.json()
            if restaurants:
                restaurant_id = restaurants[0]['id']
                print(f"✅ Found {len(restaurants)} restaurants")
                
                # Test 3: Smart AI Reservation (NEW - from Reservations section)
                print("\n3️⃣ Testing Smart AI Reservation...")
                tomorrow = date.today() + timedelta(days=1)
                
                smart_reservation_data = {
                    "selection_type": "smart",
                    "date": tomorrow.strftime("%Y-%m-%d"),
                    "time": "19:00",
                    "party_size": 2,
                    "duration_hours": 2,
                    "special_requests": "Window seat if possible",
                    "special_occasion": "anniversary",
                    "user_preferences": {
                        "quiet_area": True,
                        "window_seat": True,
                        "romantic_setting": True,
                        "near_kitchen": False,
                        "accessible": False
                    }
                }
                
                smart_response = requests.post(
                    f"{BASE_URL}/api/restaurants/{restaurant_id}/reserve/",
                    headers=headers,
                    json=smart_reservation_data
                )
                
                if smart_response.status_code == 201:
                    result = smart_response.json()
                    print("✅ Smart AI Reservation created successfully!")
                    print(f"   Reservation ID: {result['reservation']['id']}")
                    print(f"   Table: {result['reservation']['table']['number']}")
                    
                    if 'ai_selection' in result:
                        ai_info = result['ai_selection']
                        print(f"   AI Method: {ai_info['method']}")
                        print(f"   AI Confidence: {ai_info['confidence']:.2f}")
                        print(f"   AI Reasoning: {ai_info['reasoning'][:100]}...")
                else:
                    print(f"❌ Smart reservation failed: {smart_response.status_code}")
                    print(f"   Error: {smart_response.text[:200]}...")
                
                # Test 4: Customized Reservation (UPDATED - from Reservations section)
                print("\n4️⃣ Testing Customized Reservation...")
                
                # First get available tables
                tables_response = requests.get(
                    f"{BASE_URL}/api/restaurants/{restaurant_id}/available-tables/",
                    headers=headers,
                    params={
                        "date": tomorrow.strftime("%Y-%m-%d"),
                        "time": "20:00",
                        "party_size": 4,
                        "duration_hours": 2
                    }
                )
                
                if tables_response.status_code == 200:
                    tables = tables_response.json()
                    if tables:
                        table_id = tables[0]['id']
                        
                        customized_reservation_data = {
                            "selection_type": "customized",
                            "table_id": table_id,
                            "date": tomorrow.strftime("%Y-%m-%d"),
                            "time": "20:00",
                            "party_size": 4,
                            "special_requests": "Birthday celebration",
                            "duration_hours": 2
                        }
                        
                        customized_response = requests.post(
                            f"{BASE_URL}/api/restaurants/{restaurant_id}/reserve/",
                            headers=headers,
                            json=customized_reservation_data
                        )
                        
                        if customized_response.status_code == 201:
                            result = customized_response.json()
                            print("✅ Customized Reservation created successfully!")
                            print(f"   Reservation ID: {result['reservation']['id']}")
                            print(f"   Selected Table: {result['reservation']['table']['number']}")
                        else:
                            print(f"❌ Customized reservation failed: {customized_response.status_code}")
                    else:
                        print("⚠️  No available tables found for customized reservation")
                else:
                    print(f"❌ Failed to get available tables: {tables_response.status_code}")
                
            else:
                print("⚠️  No restaurants found")
        else:
            print(f"❌ Failed to get restaurants: {restaurants_response.status_code}")
    else:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"   Error: {login_response.text}")
    
    print("\n" + "=" * 60)
    print("🏁 Collection testing completed!")
    print("\n📋 Collection Update Summary:")
    print("✅ Updated 'Create Reservation' → 'Create Reservation (Customized)'")
    print("✅ Added 'Create Smart AI Reservation' with AI selection")
    print("✅ Added 'AI Services' section with 3 new endpoints")
    print("✅ Enhanced documentation with response examples")
    print("✅ Updated collection info with AI capabilities")

if __name__ == "__main__":
    test_collection_endpoints()