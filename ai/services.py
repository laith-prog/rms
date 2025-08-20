import os
from typing import List, Optional
from abc import ABC, abstractmethod

from django.conf import settings

# Try importing AI providers
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# API Keys
OPENAI_API_KEY = getattr(settings, "OPENAI_API_KEY", None)
GROQ_API_KEY = getattr(settings, "GROQ_API_KEY", None)


class BaseAIClient(ABC):
    """Abstract base class for AI clients."""
    
    @abstractmethod
    def chat(self, messages: List[dict], model: str = None, temperature: float = 0.3) -> str:
        pass


class GroqClient(BaseAIClient):
    """Client wrapper around Groq API - Free and very fast inference."""
    
    def __init__(self, api_key: Optional[str] = None):
        if not GROQ_AVAILABLE:
            raise ImportError("Groq library not installed. Run: pip install groq")
            
        self.api_key = api_key or GROQ_API_KEY
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        
        self.client = Groq(api_key=self.api_key)
    
    def chat(self, messages: List[dict], model: str = "llama3-8b-8192", temperature: float = 0.3) -> str:
        """
        Send a chat completion request to Groq.
        
        Available models:
        - llama3-8b-8192 (fast, good quality)
        - llama3-70b-8192 (slower, better quality)
        - mixtral-8x7b-32768 (good balance)
        - gemma-7b-it (Google's model)
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=1000,
                timeout=30.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")


class OpenAIClient(BaseAIClient):
    """Client wrapper around OpenAI Chat Completions."""

    def __init__(self, api_key: Optional[str] = None):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not installed. Run: pip install openai")
            
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        
        self.client = OpenAI(api_key=self.api_key)

    def chat(self, messages: List[dict], model: str = "gpt-3.5-turbo", temperature: float = 0.3) -> str:
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=1000,
                timeout=30.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")


class AIClientFactory:
    """Factory to create AI clients with fallback support."""
    
    @staticmethod
    def create_client(provider: str = "auto") -> BaseAIClient:
        """
        Create an AI client based on provider preference.
        
        Args:
            provider: "groq", "openai", or "auto" (tries in order of preference)
        """
        if provider == "groq":
            return GroqClient()
        elif provider == "openai":
            return OpenAIClient()
        elif provider == "auto":
            # Try providers in order of preference (free first)
            if GROQ_AVAILABLE and GROQ_API_KEY:
                try:
                    return GroqClient()
                except Exception:
                    pass
            
            if OPENAI_AVAILABLE and OPENAI_API_KEY:
                try:
                    return OpenAIClient()
                except Exception:
                    pass
            
            raise Exception("No AI provider available. Please configure GROQ_API_KEY or OPENAI_API_KEY")
        else:
            raise ValueError(f"Unknown provider: {provider}")


# Convenience function for backward compatibility
def get_ai_client() -> BaseAIClient:
    """Get the best available AI client."""
    return AIClientFactory.create_client("auto")


class AIRecommendationService:
    """Service for AI-powered menu recommendations."""
    
    def __init__(self):
        self.client = get_ai_client()
    
    def get_menu_recommendations(self, user_preferences: dict, available_items: list) -> dict:
        """
        Get personalized menu recommendations based on user preferences.
        
        Args:
            user_preferences: Dict with dietary restrictions, cuisine preferences, budget, etc.
            available_items: List of available menu items with details
        
        Returns:
            Dict with recommended items and reasoning
        """
        items_text = "\n".join([
            f"- {item['name']}: ${item['price']} ({item.get('category', 'No category')})"
            f" - {item.get('description', 'No description')}"
            f" - Dietary: {'Vegetarian' if item.get('is_vegetarian') else ''}"
            f"{'Vegan' if item.get('is_vegan') else ''}"
            f"{'Gluten-Free' if item.get('is_gluten_free') else ''}"
            for item in available_items[:20]  # Limit to avoid token limits
        ])
        
        preferences_text = ", ".join([
            f"{k}: {v}" for k, v in user_preferences.items() if v
        ])
        
        prompt = f"""You are a restaurant recommendation expert. Based on the user's preferences and available menu items, recommend the top 3-5 items that best match their needs.

USER PREFERENCES: {preferences_text}

AVAILABLE MENU ITEMS:
{items_text}

Please provide recommendations in this JSON format:
{{
    "recommendations": [
        {{
            "item_name": "Item Name",
            "reason": "Why this item matches their preferences",
            "match_score": 85
        }}
    ],
    "summary": "Brief explanation of the recommendations"
}}

Focus on matching dietary restrictions, cuisine preferences, and budget constraints."""

        try:
            response = self.client.chat([
                {"role": "system", "content": "You are a helpful restaurant recommendation assistant. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ])
            
            # Try to parse JSON response
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Fallback if AI doesn't return valid JSON
                return {
                    "recommendations": [],
                    "summary": response,
                    "error": "Could not parse recommendations"
                }
        except Exception as e:
            return {
                "recommendations": [],
                "summary": f"Error getting recommendations: {str(e)}",
                "error": str(e)
            }


class AIReservationService:
    """Service for AI-powered reservation suggestions."""
    
    def __init__(self):
        self.client = get_ai_client()
    
    def get_reservation_suggestions(self, restaurant_data: dict, user_request: str) -> dict:
        """
        Get intelligent reservation suggestions based on restaurant availability and user needs.
        
        Args:
            restaurant_data: Dict with restaurant info, available tables, busy times, etc.
            user_request: User's reservation request (party size, preferred time, etc.)
        
        Returns:
            Dict with suggested times, table options, and recommendations
        """
        prompt = f"""You are a restaurant reservation assistant. Based on the restaurant information and user request, provide helpful reservation suggestions.

RESTAURANT INFO:
- Name: {restaurant_data.get('name', 'Unknown')}
- Opening Hours: {restaurant_data.get('opening_time', 'Unknown')} - {restaurant_data.get('closing_time', 'Unknown')}
- Available Tables: {restaurant_data.get('available_tables', 'Unknown')}
- Busy Times: {restaurant_data.get('busy_times', 'Unknown')}
- Special Notes: {restaurant_data.get('notes', 'None')}

USER REQUEST: {user_request}

Please provide suggestions in this JSON format:
{{
    "suggested_times": [
        {{
            "time": "7:00 PM",
            "availability": "Good",
            "reason": "Less crowded time, good service"
        }}
    ],
    "table_recommendations": [
        {{
            "table_type": "Window table for 2",
            "reason": "Romantic setting as requested"
        }}
    ],
    "additional_tips": [
        "Arrive 10 minutes early",
        "Try the chef's special"
    ],
    "summary": "Brief summary of recommendations"
}}

Consider factors like party size, preferred ambiance, special occasions, and restaurant capacity."""

        try:
            response = self.client.chat([
                {"role": "system", "content": "You are a helpful restaurant reservation assistant. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ])
            
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {
                    "suggested_times": [],
                    "table_recommendations": [],
                    "additional_tips": [],
                    "summary": response,
                    "error": "Could not parse suggestions"
                }
        except Exception as e:
            return {
                "suggested_times": [],
                "table_recommendations": [],
                "additional_tips": [],
                "summary": f"Error getting suggestions: {str(e)}",
                "error": str(e)
            }


class AISentimentService:
    """Service for AI-powered sentiment analysis."""
    
    def __init__(self):
        self.client = get_ai_client()
    
    def analyze_sentiment(self, text: str, context: str = "restaurant_review") -> dict:
        """
        Analyze sentiment of text (reviews, feedback, etc.).
        
        Args:
            text: Text to analyze
            context: Context of the text (restaurant_review, customer_feedback, etc.)
        
        Returns:
            Dict with sentiment analysis results
        """
        prompt = f"""Analyze the sentiment of the following {context}. Provide detailed insights about the customer's experience.

TEXT TO ANALYZE: "{text}"

Please provide analysis in this JSON format:
{{
    "overall_sentiment": "positive/negative/neutral",
    "confidence_score": 85,
    "key_emotions": ["satisfied", "disappointed", "excited"],
    "specific_aspects": {{
        "food_quality": "positive",
        "service": "neutral",
        "ambiance": "positive",
        "value_for_money": "negative"
    }},
    "key_phrases": [
        "delicious food",
        "slow service",
        "great atmosphere"
    ],
    "actionable_insights": [
        "Customer loved the food quality",
        "Service speed needs improvement",
        "Pricing concerns mentioned"
    ],
    "priority_level": "high/medium/low",
    "summary": "Brief summary of the sentiment analysis"
}}

Focus on identifying specific aspects of the restaurant experience and actionable feedback."""

        try:
            response = self.client.chat([
                {"role": "system", "content": "You are an expert sentiment analysis assistant specializing in restaurant feedback. You MUST respond with ONLY valid JSON, no other text. Do not include any explanations or markdown formatting."},
                {"role": "user", "content": prompt}
            ])
            
            import json
            import re
            
            # Clean the response to extract JSON
            cleaned_response = response.strip()
            
            # Remove markdown code blocks if present
            if "```json" in cleaned_response:
                cleaned_response = re.sub(r'```json\s*', '', cleaned_response)
                cleaned_response = re.sub(r'\s*```', '', cleaned_response)
            elif "```" in cleaned_response:
                cleaned_response = re.sub(r'```\s*', '', cleaned_response)
                cleaned_response = re.sub(r'\s*```', '', cleaned_response)
            
            try:
                return json.loads(cleaned_response)
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass
                
                # Fallback: create a basic analysis
                sentiment = "neutral"
                if any(word in response.lower() for word in ["good", "great", "excellent", "amazing", "love", "perfect"]):
                    sentiment = "positive"
                elif any(word in response.lower() for word in ["bad", "terrible", "awful", "hate", "worst", "horrible"]):
                    sentiment = "negative"
                
                return {
                    "overall_sentiment": sentiment,
                    "confidence_score": 50,
                    "key_emotions": [],
                    "specific_aspects": {},
                    "key_phrases": [],
                    "actionable_insights": [],
                    "priority_level": "medium",
                    "summary": response,
                    "error": "Could not parse JSON, used fallback analysis"
                }
        except Exception as e:
            return {
                "overall_sentiment": "neutral",
                "confidence_score": 0,
                "key_emotions": [],
                "specific_aspects": {},
                "key_phrases": [],
                "actionable_insights": [],
                "priority_level": "low",
                "summary": f"Error analyzing sentiment: {str(e)}",
                "error": str(e)
            }