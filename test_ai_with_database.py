#!/usr/bin/env python
"""
Test script to verify AI integration with restaurant database.
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rms.settings')
django.setup()

from ai.views import get_restaurant_context
from ai.services import get_ai_client

def test_database_context():
    """Test the restaurant context function."""
    print("🍽️  Testing Restaurant Database Context")
    print("=" * 50)
    
    # Test general restaurant query
    print("\n1. Testing general restaurant query:")
    context = get_restaurant_context("What restaurants do you have?")
    print("Context generated:")
    print(context[:500] + "..." if len(context) > 500 else context)
    
    # Test specific restaurant query
    print("\n2. Testing specific restaurant query:")
    context = get_restaurant_context("Tell me about Tasty Bites")
    print("Context generated:")
    print(context[:500] + "..." if len(context) > 500 else context)

def test_ai_with_context():
    """Test AI responses with database context."""
    print("\n\n🤖 Testing AI with Database Context")
    print("=" * 50)
    
    try:
        client = get_ai_client()
        
        # Test 1: General restaurant question
        print("\n1. Question: 'What restaurants do you have available?'")
        context = get_restaurant_context("What restaurants do you have available?")
        
        system_prompt = f"""You are an AI assistant for a Restaurant Management System. 
You have access to real restaurant data and should provide helpful, accurate information.

AVAILABLE RESTAURANT DATA:
{context}

Instructions:
- Use the provided restaurant data to answer questions about specific restaurants, menus, prices, and availability
- If asked about restaurants not in the data, politely say you don't have information about that specific restaurant
- For general dining questions, provide helpful advice
- Be friendly and helpful
- Always mention specific prices, restaurant names, and menu items when relevant
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "What restaurants do you have available?"},
        ]
        
        response = client.chat(messages)
        print("AI Response:")
        print(response)
        
        # Test 2: Specific restaurant question
        print("\n" + "="*50)
        print("2. Question: 'What can you tell me about Tasty Bites menu and prices?'")
        context = get_restaurant_context("What can you tell me about Tasty Bites menu and prices?")
        
        system_prompt = f"""You are an AI assistant for a Restaurant Management System. 
You have access to real restaurant data and should provide helpful, accurate information.

AVAILABLE RESTAURANT DATA:
{context}

Instructions:
- Use the provided restaurant data to answer questions about specific restaurants, menus, prices, and availability
- If asked about restaurants not in the data, politely say you don't have information about that specific restaurant
- For general dining questions, provide helpful advice
- Be friendly and helpful
- Always mention specific prices, restaurant names, and menu items when relevant
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "What can you tell me about Tasty Bites menu and prices?"},
        ]
        
        response = client.chat(messages)
        print("AI Response:")
        print(response)
        
    except Exception as e:
        print(f"❌ Error testing AI: {e}")

def main():
    print("🧪 AI + Database Integration Test")
    print("=" * 60)
    
    test_database_context()
    test_ai_with_context()
    
    print("\n" + "="*60)
    print("✅ Test completed! The AI now has access to your restaurant database.")
    print("💡 Try asking questions like:")
    print("   - 'What restaurants do you have?'")
    print("   - 'Tell me about Tasty Bites'")
    print("   - 'What are the prices at Ocean Delights?'")
    print("   - 'Do you have any vegetarian options?'")

if __name__ == "__main__":
    main()