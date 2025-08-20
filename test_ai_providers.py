#!/usr/bin/env python
"""
Test script for AI providers.
Run this to test which AI providers are available and working.
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rms.settings')
django.setup()

from ai.services import AIClientFactory, GroqClient, OpenAIClient, GROQ_AVAILABLE, OPENAI_AVAILABLE, GROQ_API_KEY, OPENAI_API_KEY

def test_provider(provider_name, client_class, api_key):
    """Test a specific AI provider."""
    print(f"\n=== Testing {provider_name} ===")
    
    if not api_key or api_key == "your_groq_api_key_here":
        print(f"❌ {provider_name} API key not configured")
        return False
    
    try:
        client = client_class()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello from " + provider_name + "!' in one sentence."}
        ]
        
        print(f"🔄 Testing {provider_name} API...")
        response = client.chat(messages)
        print(f"✅ {provider_name} working! Response: {response}")
        return True
        
    except Exception as e:
        print(f"❌ {provider_name} failed: {str(e)}")
        return False

def main():
    print("🤖 AI Provider Test Script")
    print("=" * 50)
    
    # Check library availability
    print(f"Groq library available: {'✅' if GROQ_AVAILABLE else '❌'}")
    print(f"OpenAI library available: {'✅' if OPENAI_AVAILABLE else '❌'}")
    
    working_providers = []
    
    # Test Groq
    if GROQ_AVAILABLE:
        if test_provider("Groq", GroqClient, GROQ_API_KEY):
            working_providers.append("Groq")
    else:
        print("\n❌ Groq library not installed")
    
    # Test OpenAI
    if OPENAI_AVAILABLE:
        if test_provider("OpenAI", OpenAIClient, OPENAI_API_KEY):
            working_providers.append("OpenAI")
    else:
        print("\n❌ OpenAI library not installed")
    
    # Test auto selection
    print(f"\n=== Testing Auto Selection ===")
    try:
        client = AIClientFactory.create_client("auto")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Auto selection works!' in one sentence."}
        ]
        response = client.chat(messages)
        print(f"✅ Auto selection working! Response: {response}")
        print(f"🎯 Selected provider: {type(client).__name__}")
    except Exception as e:
        print(f"❌ Auto selection failed: {str(e)}")
    
    # Summary
    print(f"\n{'='*50}")
    print(f"📊 Summary:")
    print(f"Working providers: {', '.join(working_providers) if working_providers else 'None'}")
    
    if not working_providers:
        print("\n🚨 No AI providers are working!")
        print("To fix this:")
        print("1. Get a free Groq API key from https://console.groq.com/")
        print("2. Add it to your .env file: GROQ_API_KEY=your_actual_key")
        print("3. Or fix your OpenAI billing at https://platform.openai.com/")
    else:
        print(f"\n🎉 You have {len(working_providers)} working AI provider(s)!")

if __name__ == "__main__":
    main()