#!/usr/bin/env python
"""
Comprehensive test script for all AI features:
- Menu Recommendations
- Reservation Suggestions  
- Sentiment Analysis
- Enhanced Chat with Database Context
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rms.settings')
django.setup()

from ai.services import AIRecommendationService, AIReservationService, AISentimentService
from restaurants.models import Restaurant, MenuItem

def test_menu_recommendations():
    """Test AI-powered menu recommendations."""
    print("🍽️  Testing Menu Recommendations")
    print("=" * 50)
    
    try:
        # Get some menu items
        items = MenuItem.objects.filter(is_active=True)[:10]
        available_items = []
        
        for item in items:
            available_items.append({
                "name": item.name,
                "price": float(item.price),
                "description": item.description or "Delicious dish",
                "category": item.food_category.name if item.food_category else "Main Course",
                "is_vegetarian": item.is_vegetarian,
                "is_vegan": item.is_vegan,
                "is_gluten_free": item.is_gluten_free,
                "restaurant": item.restaurant.name
            })
        
        # Test preferences
        user_preferences = {
            "dietary_restrictions": ["vegetarian"],
            "budget_range": "medium",
            "occasion": "romantic dinner",
            "party_size": 2
        }
        
        print(f"Available items: {len(available_items)}")
        print(f"User preferences: {user_preferences}")
        
        # Get AI recommendations
        ai_service = AIRecommendationService()
        recommendations = ai_service.get_menu_recommendations(user_preferences, available_items)
        
        print("\n🤖 AI Recommendations:")
        print(f"Summary: {recommendations.get('summary', 'No summary')}")
        
        for rec in recommendations.get('recommendations', []):
            print(f"- {rec.get('item_name', 'Unknown')}: {rec.get('reason', 'No reason')} (Score: {rec.get('match_score', 0)})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing menu recommendations: {e}")
        return False

def test_reservation_suggestions():
    """Test AI-powered reservation suggestions."""
    print("\n🏪 Testing Reservation Suggestions")
    print("=" * 50)
    
    try:
        # Get a restaurant
        restaurant = Restaurant.objects.first()
        if not restaurant:
            print("❌ No restaurants found in database")
            return False
        
        restaurant_data = {
            "name": restaurant.name,
            "opening_time": "11:00",
            "closing_time": "22:00",
            "available_tables": ["Table 1 (capacity: 4)", "Table 2 (capacity: 2)", "Table 3 (capacity: 6)"],
            "busy_times": "7-9 PM on weekends",
            "notes": restaurant.description or "Great restaurant"
        }
        
        user_request = "Party of 4 for Saturday evening, celebrating anniversary"
        
        print(f"Restaurant: {restaurant.name}")
        print(f"User request: {user_request}")
        
        # Get AI suggestions
        ai_service = AIReservationService()
        suggestions = ai_service.get_reservation_suggestions(restaurant_data, user_request)
        
        print("\n🤖 AI Suggestions:")
        print(f"Summary: {suggestions.get('summary', 'No summary')}")
        
        print("\nSuggested Times:")
        for time_suggestion in suggestions.get('suggested_times', []):
            print(f"- {time_suggestion.get('time', 'Unknown')}: {time_suggestion.get('reason', 'No reason')}")
        
        print("\nTable Recommendations:")
        for table_rec in suggestions.get('table_recommendations', []):
            print(f"- {table_rec.get('table_type', 'Unknown')}: {table_rec.get('reason', 'No reason')}")
        
        print("\nAdditional Tips:")
        for tip in suggestions.get('additional_tips', []):
            print(f"- {tip}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing reservation suggestions: {e}")
        return False

def test_sentiment_analysis():
    """Test AI-powered sentiment analysis."""
    print("\n😊 Testing Sentiment Analysis")
    print("=" * 50)
    
    try:
        # Test different types of reviews
        test_reviews = [
            {
                "text": "The food was absolutely amazing! The service was quick and the staff was very friendly. I especially loved the pasta dish. Will definitely come back!",
                "expected": "positive"
            },
            {
                "text": "The food was okay but the service was really slow. We waited 45 minutes for our order. The restaurant was also quite noisy.",
                "expected": "mixed/negative"
            },
            {
                "text": "Terrible experience. The food was cold, the staff was rude, and the place was dirty. Would not recommend to anyone.",
                "expected": "negative"
            }
        ]
        
        ai_service = AISentimentService()
        
        for i, review in enumerate(test_reviews, 1):
            print(f"\n--- Test Review {i} ---")
            print(f"Text: {review['text'][:100]}...")
            print(f"Expected: {review['expected']}")
            
            analysis = ai_service.analyze_sentiment(review['text'], "restaurant_review")
            
            print(f"🤖 AI Analysis:")
            print(f"Overall Sentiment: {analysis.get('overall_sentiment', 'Unknown')}")
            print(f"Confidence: {analysis.get('confidence_score', 0)}%")
            print(f"Key Emotions: {', '.join(analysis.get('key_emotions', []))}")
            print(f"Priority Level: {analysis.get('priority_level', 'Unknown')}")
            
            # Show specific aspects
            aspects = analysis.get('specific_aspects', {})
            if aspects:
                print("Specific Aspects:")
                for aspect, sentiment in aspects.items():
                    print(f"  - {aspect}: {sentiment}")
            
            # Show actionable insights
            insights = analysis.get('actionable_insights', [])
            if insights:
                print("Actionable Insights:")
                for insight in insights[:3]:  # Show first 3
                    print(f"  - {insight}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing sentiment analysis: {e}")
        return False

def test_enhanced_chat():
    """Test enhanced chat with database context."""
    print("\n💬 Testing Enhanced Chat with Database")
    print("=" * 50)
    
    try:
        from ai.views import get_restaurant_context
        from ai.services import get_ai_client
        
        # Test questions
        test_questions = [
            "What restaurants do you have?",
            "Tell me about Tasty Bites menu and prices",
            "Do you have any vegetarian options?",
            "What's the most expensive item on the menu?"
        ]
        
        client = get_ai_client()
        
        for question in test_questions:
            print(f"\n--- Question: {question} ---")
            
            # Get context
            context = get_restaurant_context(question)
            print(f"Context length: {len(context)} characters")
            
            # Create enhanced prompt
            system_prompt = f"""You are an AI assistant for a Restaurant Management System. 
You have access to real restaurant data and should provide helpful, accurate information.

AVAILABLE RESTAURANT DATA:
{context[:1000]}...

Instructions:
- Use the provided restaurant data to answer questions about specific restaurants, menus, prices, and availability
- Be friendly and helpful
- Always mention specific prices, restaurant names, and menu items when relevant
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ]
            
            response = client.chat(messages)
            print(f"🤖 AI Response: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing enhanced chat: {e}")
        return False

def main():
    print("🧪 Comprehensive AI Features Test")
    print("=" * 60)
    
    results = {
        "Menu Recommendations": test_menu_recommendations(),
        "Reservation Suggestions": test_reservation_suggestions(),
        "Sentiment Analysis": test_sentiment_analysis(),
        "Enhanced Chat": test_enhanced_chat()
    }
    
    print("\n" + "="*60)
    print("📊 Test Results Summary:")
    print("="*60)
    
    for feature, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{feature}: {status}")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All AI features are working correctly!")
        print("\n💡 Available API endpoints:")
        print("- POST /api/ai/chat/ - Enhanced chat with database context")
        print("- POST /api/ai/menu-recommendations/ - AI menu recommendations")
        print("- POST /api/ai/reservation-suggestions/ - AI reservation suggestions")
        print("- POST /api/ai/sentiment-analysis/ - AI sentiment analysis")
    else:
        print("⚠️  Some features need attention. Check the error messages above.")

if __name__ == "__main__":
    main()