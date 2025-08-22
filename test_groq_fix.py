#!/usr/bin/env python
"""
Test script to verify Groq client initialization works
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rms.settings')
django.setup()

def test_groq_initialization():
    """Test that Groq client can be initialized without errors"""
    print("Testing Groq client initialization...")
    
    try:
        from ai.services import AIService
        
        # Try to create an AIService instance
        ai_service = AIService()
        print("SUCCESS: Groq client initialized successfully!")
        print(f"Model: {ai_service.model}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to initialize Groq client: {str(e)}")
        return False

if __name__ == '__main__':
    success = test_groq_initialization()
    sys.exit(0 if success else 1)