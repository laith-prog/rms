import os
from groq import Groq
from django.conf import settings
from restaurants.models import Restaurant, MenuItem, Review, Reservation
from orders.models import Order
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AIService:
    """
    AI Service using Groq API for various restaurant management tasks
    """
    
    def __init__(self):
        self.client = Groq(
            api_key=os.getenv('GROQ_API_KEY')
        )
        self.model = "llama3-8b-8192"  # Fast and efficient model
    
    def chat(self, message, user=None, context=None):
        """
        General chat functionality with restaurant context
        """
        try:
            # Build system prompt with restaurant context
            system_prompt = """You are a helpful AI assistant for a restaurant management system. 
            You can help with:
            - Restaurant recommendations
            - Menu suggestions
            - Reservation assistance
            - General dining questions
            - Order assistance
            
            Keep responses concise and helpful. If asked about specific restaurants or menus, 
            let the user know you'd need more specific information to provide detailed recommendations."""
            
            if context:
                system_prompt += f"\n\nAdditional context: {context}"
            
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                model=self.model,
                max_tokens=500,
                temperature=0.7
            )
            
            return {
                'success': True,
                'response': response.choices[0].message.content,
                'user_message': message
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'AI service error: {str(e)}',
                'user_message': message
            }
    
    def get_menu_recommendations(self, restaurant_id, dietary_preferences=None, allergies=None, budget_range='medium', additional_preferences='', cuisine_preference=''):
        """
        Get AI-powered menu recommendations
        """
        try:
            # Get restaurant and menu items
            restaurant = Restaurant.objects.get(id=restaurant_id, is_active=True)
            menu_items = MenuItem.objects.filter(restaurant=restaurant, is_active=True)
            
            if not menu_items.exists():
                return {
                    'success': False,
                    'error': 'No menu items found for this restaurant'
                }
            
            # Build menu context
            menu_context = []
            for item in menu_items:
                menu_context.append({
                    'name': item.name,
                    'description': item.description or '',
                    'price': float(item.price),
                    'category': item.food_category.name if item.food_category else 'Uncategorized',
                    'preparation_time': item.preparation_time,
                    'is_vegetarian': item.is_vegetarian,
                    'is_vegan': item.is_vegan,
                    'is_gluten_free': item.is_gluten_free,
                    'contains_nuts': item.contains_nuts,
                    'contains_dairy': item.contains_dairy,
                    'is_spicy': item.is_spicy
                })
            
            # Build dietary restrictions text
            dietary_text = ', '.join(dietary_preferences) if dietary_preferences else 'None specified'
            allergies_text = ', '.join(allergies) if allergies else 'None specified'
            
            # Build prompt (avoiding f-string with JSON examples to prevent formatting errors)
            prompt = "Based on the following menu from " + restaurant.name + ", recommend 3-5 dishes that would be perfect for someone with these preferences:\n\n"
            prompt += "Dietary preferences: " + dietary_text + "\n"
            prompt += "Allergies to avoid: " + allergies_text + "\n"
            prompt += "Budget range: " + budget_range + "\n"
            if additional_preferences:
                prompt += "Additional preferences: " + additional_preferences + "\n"
            if cuisine_preference:
                prompt += "Preferred cuisine type: " + cuisine_preference + "\n"
            prompt += "\n"
            prompt += "Menu items available:\n"
            prompt += json.dumps(menu_context, indent=2) + "\n\n"
            prompt += """Please analyze each menu item and recommend the best matches. Consider:
- Dietary preferences (vegetarian, vegan, etc.)
- Allergies (nuts, dairy, etc.)
- Budget range
- Preparation time
- Overall appeal

Respond with a JSON array containing 3-5 recommendations. Each recommendation should have:
- "name": exact dish name from the menu
- "reason": brief explanation why it fits the preferences
- "price": price of the dish
- "category": food category
- "prep_time": preparation time in minutes

Example format:
[
  {
    "name": "Dish Name",
    "reason": "Perfect for vegetarians and nut-free",
    "price": 15.99,
    "category": "Main Course",
    "prep_time": 20
  }
]"""
            
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful restaurant AI that provides menu recommendations. You MUST respond with ONLY a valid JSON array, no additional text or explanations. Start your response with [ and end with ]."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                max_tokens=800,
                temperature=0.3  # Lower temperature for more consistent JSON formatting
            )
            
            # Try to parse JSON response
            response_content = response.choices[0].message.content.strip()
            
            try:
                # First try to parse the entire response as JSON
                recommendations = json.loads(response_content)
            except json.JSONDecodeError:
                # Try to extract JSON from the response if it's wrapped in text
                try:
                    # Look for JSON array in the response
                    start_idx = response_content.find('[')
                    end_idx = response_content.rfind(']') + 1
                    
                    if start_idx != -1 and end_idx != 0:
                        json_str = response_content[start_idx:end_idx]
                        recommendations = json.loads(json_str)
                    else:
                        raise json.JSONDecodeError("No JSON array found", response_content, 0)
                        
                except json.JSONDecodeError:
                    # Final fallback - create a structured response from the text
                    recommendations = [
                        {
                            'name': 'AI Response (Parsing Issue)',
                            'reason': 'The AI provided recommendations but in an unexpected format. Please try again.',
                            'price': 0,
                            'category': 'Various',
                            'prep_time': 0,
                            'raw_response': response_content[:500] + '...' if len(response_content) > 500 else response_content
                        }
                    ]
            
            return {
                'success': True,
                'recommendations': recommendations,
                'restaurant_name': restaurant.name,
                'total_menu_items': menu_items.count()
            }
            
        except Restaurant.DoesNotExist:
            return {
                'success': False,
                'error': 'Restaurant not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'AI service error: {str(e)}'
            }
    
    def get_reservation_suggestions(self, restaurant_id, party_size, preferred_date, preferred_time=None, special_occasion=None):
        """
        Get AI-powered reservation suggestions
        """
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id, is_active=True)
            
            # Get restaurant categories for cuisine info
            categories = restaurant.categories.all()
            cuisine_info = ', '.join([cat.name for cat in categories]) if categories.exists() else 'Various cuisines'
            
            # Build context about the restaurant
            context = f"""Restaurant: {restaurant.name}
Location: {restaurant.address}
Cuisine: {cuisine_info}
Opening hours: {restaurant.opening_time} - {restaurant.closing_time}
Services: {'Dine-in' if restaurant.offers_dine_in else ''} {'Takeaway' if restaurant.offers_takeaway else ''} {'Delivery' if restaurant.offers_delivery else ''}
Party size: {party_size}
Preferred date: {preferred_date}
Preferred time: {preferred_time or 'Flexible'}
Special occasion: {special_occasion or 'None'}"""
            
            prompt = "Based on the following restaurant information, provide suggestions for the best reservation times and experience:\n\n"
            prompt += context + "\n\n"
            prompt += """Please provide:
1. Recommended time slots (considering typical dining patterns)
2. Special considerations for the party size
3. Suggestions for the special occasion (if any)
4. Any dining tips or recommendations

Respond with EXACTLY this JSON structure:
{
  "time_suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"],
  "party_size_tips": "tips for the party size",
  "occasion_suggestions": "suggestions for the special occasion",
  "dining_tips": "general dining tips"
}

Keep suggestions as simple strings, not objects."""
            
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a restaurant reservation AI assistant. You MUST respond with ONLY valid JSON, no additional text. Start with { and end with }."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                max_tokens=600,
                temperature=0.3
            )
            
            response_content = response.choices[0].message.content.strip()
            
            try:
                suggestions = json.loads(response_content)
                
                # Normalize the suggestions to expected format
                if 'time_suggestions' in suggestions:
                    # If time_suggestions is a list of objects, convert to strings
                    if isinstance(suggestions['time_suggestions'], list) and suggestions['time_suggestions']:
                        if isinstance(suggestions['time_suggestions'][0], dict):
                            # Convert objects to readable strings
                            time_strings = []
                            for time_obj in suggestions['time_suggestions']:
                                if 'time' in time_obj and 'description' in time_obj:
                                    time_strings.append(f"{time_obj['time']} - {time_obj['description']}")
                                elif 'time' in time_obj:
                                    time_strings.append(str(time_obj['time']))
                                else:
                                    time_strings.append(str(time_obj))
                            suggestions['time_suggestions'] = time_strings
                
            except json.JSONDecodeError:
                # Try to extract JSON object from response
                try:
                    start_idx = response_content.find('{')
                    end_idx = response_content.rfind('}') + 1
                    
                    if start_idx != -1 and end_idx != 0:
                        json_str = response_content[start_idx:end_idx]
                        suggestions = json.loads(json_str)
                        
                        # Apply the same normalization
                        if 'time_suggestions' in suggestions and isinstance(suggestions['time_suggestions'], list):
                            if suggestions['time_suggestions'] and isinstance(suggestions['time_suggestions'][0], dict):
                                time_strings = []
                                for time_obj in suggestions['time_suggestions']:
                                    if 'time' in time_obj and 'description' in time_obj:
                                        time_strings.append(f"{time_obj['time']} - {time_obj['description']}")
                                    elif 'time' in time_obj:
                                        time_strings.append(str(time_obj['time']))
                                    else:
                                        time_strings.append(str(time_obj))
                                suggestions['time_suggestions'] = time_strings
                    else:
                        raise json.JSONDecodeError("No JSON object found", response_content, 0)
                        
                except json.JSONDecodeError:
                    # Final fallback
                    suggestions = {
                        'time_suggestions': ['7:00 PM - 8:00 PM (Peak dining time)', '6:00 PM - 7:00 PM (Early dinner)'],
                        'party_size_tips': f'For a party of {party_size}, consider booking in advance.',
                        'occasion_suggestions': 'AI response parsing failed. Please try again.',
                        'dining_tips': 'Arrive 10-15 minutes early for your reservation.',
                        'parsing_error': 'JSON structure was different than expected',
                        'raw_response': response_content[:500] + '...' if len(response_content) > 500 else response_content
                    }
            
            return {
                'success': True,
                'suggestions': suggestions,
                'restaurant_name': restaurant.name
            }
            
        except Restaurant.DoesNotExist:
            return {
                'success': False,
                'error': 'Restaurant not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'AI service error: {str(e)}'
            }
    
    def analyze_sentiment(self, text, context='general'):
        """
        Analyze sentiment of customer feedback
        """
        try:
            prompt = f"""Analyze the sentiment of the following text in the context of {context}:

"{text}"

Provide a JSON response with:
- sentiment: "positive", "negative", or "neutral"
- confidence: score from 0.0 to 1.0
- emotions: object with emotion scores
- summary: brief explanation of the analysis
- suggestions: actionable suggestions based on the sentiment (if negative)"""
            
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a sentiment analysis AI. You MUST respond with ONLY valid JSON, no additional text. Start with { and end with }."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                max_tokens=400,
                temperature=0.3
            )
            
            response_content = response.choices[0].message.content.strip()
            
            try:
                analysis = json.loads(response_content)
            except json.JSONDecodeError:
                # Try to extract JSON object from response
                try:
                    start_idx = response_content.find('{')
                    end_idx = response_content.rfind('}') + 1
                    
                    if start_idx != -1 and end_idx != 0:
                        json_str = response_content[start_idx:end_idx]
                        analysis = json.loads(json_str)
                    else:
                        raise json.JSONDecodeError("No JSON object found", response_content, 0)
                        
                except json.JSONDecodeError:
                    # Fallback analysis based on text content
                    content = text.lower()
                    if any(word in content for word in ['good', 'great', 'excellent', 'amazing', 'love', 'perfect', 'wonderful', 'fantastic']):
                        sentiment = 'positive'
                        confidence = 0.8
                    elif any(word in content for word in ['bad', 'terrible', 'awful', 'hate', 'worst', 'horrible', 'disgusting', 'disappointing']):
                        sentiment = 'negative'
                        confidence = 0.8
                    else:
                        sentiment = 'neutral'
                        confidence = 0.6
                    
                    analysis = {
                        'sentiment': sentiment,
                        'confidence': confidence,
                        'emotions': {'general': confidence},
                        'summary': f'Analyzed as {sentiment} with {confidence} confidence',
                        'suggestions': ['AI response parsing failed. Please try again.'] if sentiment == 'negative' else [],
                        'raw_response': response_content[:200] + '...' if len(response_content) > 200 else response_content
                    }
            
            return {
                'success': True,
                **analysis
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'AI service error: {str(e)}',
                'sentiment': 'neutral',
                'confidence': 0.0,
                'emotions': {}
            }
    
    def get_basic_recommendations(self, user_id=None, recommendation_type='restaurants', location=None, preferences=None):
        """Existing method unchanged, improvements below add new AI helpers."""

    def semantic_menu_search(self, query, restaurant_id=None):
        """Semantic-like search over menu items. If embeddings are unavailable, fallback to AI re-rank of text."""
        try:
            qs = MenuItem.objects.filter(is_active=True)
            if restaurant_id:
                qs = qs.filter(restaurant_id=restaurant_id)
            items = list(qs.select_related('restaurant', 'food_category')[:200])
            if not items:
                return {'success': False, 'error': 'No menu items found'}

            menu_context = []
            for it in items:
                menu_context.append({
                    'id': it.id,
                    'name': it.name,
                    'description': it.description or '',
                    'restaurant': it.restaurant.name,
                    'category': it.food_category.name if it.food_category else 'Uncategorized',
                    'price': float(it.price),
                    'is_spicy': it.is_spicy,
                    'is_vegan': it.is_vegan,
                    'is_vegetarian': it.is_vegetarian,
                })

            prompt = (
                "You will receive a diner query and a list of menu items. "
                "Return the top 5 best matches as a JSON array of objects with fields: id, name, reason, score (0-1)."
            )
            user_text = f"Query: {query}\nMenu: {json.dumps(menu_context)[:6000]}"

            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a semantic search assistant. Respond ONLY with a JSON array."},
                    {"role": "user", "content": prompt + "\n" + user_text},
                ],
                model=self.model,
                max_tokens=700,
                temperature=0.2,
            )
            content = response.choices[0].message.content.strip()
            try:
                matches = json.loads(content)
            except json.JSONDecodeError:
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                matches = json.loads(content[start_idx:end_idx]) if start_idx != -1 and end_idx != 0 else []

            return {'success': True, 'results': matches[:5]}
        except Exception as e:
            return {'success': False, 'error': f'AI service error: {str(e)}'}

    def upsell_recommendations(self, order_id):
        """Suggest complementary items for an existing order."""
        try:
            order = Order.objects.select_related('restaurant').prefetch_related('items__menu_item').get(id=order_id)
            restaurant = order.restaurant
            items = [f"{it.quantity}x {it.menu_item.name}" for it in order.items.all()]
            all_menu = list(MenuItem.objects.filter(restaurant=restaurant, is_active=True).values('id','name','price'))
            prompt = (
                "Given the current order items and full menu, propose up to 3 upsell suggestions (sides/drinks/desserts). "
                "Return JSON array with fields: id (menu item id), name, reason, estimated_impact (low|medium|high)."
            )
            user_text = f"Order items: {items}\nMenu: {json.dumps(all_menu)[:6000]}"

            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an upsell assistant. Respond ONLY with JSON array."},
                    {"role": "user", "content": prompt + "\n" + user_text},
                ],
                model=self.model,
                max_tokens=500,
                temperature=0.3,
            )
            content = response.choices[0].message.content.strip()
            try:
                suggestions = json.loads(content)
            except json.JSONDecodeError:
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                suggestions = json.loads(content[start_idx:end_idx]) if start_idx != -1 and end_idx != 0 else []

            return {'success': True, 'suggestions': suggestions[:3]}
        except Order.DoesNotExist:
            return {'success': False, 'error': 'Order not found'}
        except Exception as e:
            return {'success': False, 'error': f'AI service error: {str(e)}'}

    def reviews_summarize(self, restaurant_id, since=None):
        """Summarize reviews into themes and actions, and persist basic analysis link if needed."""
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id, is_active=True)
            reviews = Review.objects.filter(restaurant=restaurant).order_by('-created_at')
            if since:
                reviews = reviews.filter(created_at__date__gte=since)
            reviews = list(reviews[:200])
            if not reviews:
                return {'success': False, 'error': 'No reviews found'}

            data = [{'rating': r.rating, 'comment': r.comment or ''} for r in reviews]
            prompt = (
                "Summarize these reviews into: summary, themes (array of {name, mentions}), pros, cons, action_items (array). "
                "Return a JSON object."
            )
            user_text = json.dumps(data)[:6000]
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You analyze restaurant reviews and respond ONLY with a JSON object."},
                    {"role": "user", "content": prompt + "\nReviews: " + user_text},
                ],
                model=self.model,
                max_tokens=800,
                temperature=0.2,
            )
            content = response.choices[0].message.content.strip()
            try:
                summary = json.loads(content)
            except json.JSONDecodeError:
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                summary = json.loads(content[start_idx:end_idx]) if start_idx != -1 and end_idx != 0 else {}

            return {'success': True, 'restaurant': restaurant.name, 'summary': summary}
        except Restaurant.DoesNotExist:
            return {'success': False, 'error': 'Restaurant not found'}
        except Exception as e:
            return {'success': False, 'error': f'AI service error: {str(e)}'}

    def predict_wait_time(self, restaurant_id, party_size, time):
        """Heuristic + AI: predict wait time window with confidence."""
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id, is_active=True)
            # Very simple heuristic context; in future, use historical reservations
            context = {
                'opening_time': str(restaurant.opening_time),
                'closing_time': str(restaurant.closing_time),
                'party_size': party_size,
                'time': time,
            }
            prompt = (
                "Given restaurant hours and party size, estimate wait time and confidence as JSON object: "
                "{ 'estimate_minutes': int, 'range': 'min-max', 'confidence': 0..1, 'tips': [..] }."
            )
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Wait-time predictor. Respond ONLY with a JSON object."},
                    {"role": "user", "content": prompt + "\nContext: " + json.dumps(context)},
                ],
                model=self.model,
                max_tokens=300,
                temperature=0.2,
            )
            content = response.choices[0].message.content.strip()
            try:
                obj = json.loads(content)
            except json.JSONDecodeError:
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                obj = json.loads(content[start_idx:end_idx]) if start_idx != -1 and end_idx != 0 else {}
            return {'success': True, **obj}
        except Restaurant.DoesNotExist:
            return {'success': False, 'error': 'Restaurant not found'}
        except Exception as e:
            return {'success': False, 'error': f'AI service error: {str(e)}'}
        """
        Get basic AI recommendations
        """
        try:
            # Build context based on recommendation type
            if recommendation_type == 'restaurants':
                restaurants = Restaurant.objects.filter(is_active=True)[:10]
                context = "Available restaurants:\n"
                for restaurant in restaurants:
                    cats = ', '.join([c.name for c in restaurant.categories.all()[:3]]) or 'Various'
                    context += f"- {restaurant.name}: {cats} cuisine, {restaurant.address}\n"
            else:
                context = f"Providing {recommendation_type} recommendations"
            
            prompt = f"""Provide {recommendation_type} recommendations based on:
Location: {location or 'Not specified'}
Preferences: {preferences or 'General'}
User context: {context}

Please provide 3-5 recommendations with brief descriptions and reasons why they're good choices.
Format as JSON array with 'name', 'description', 'reason' fields."""
            
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": f"You are a helpful AI providing {recommendation_type} recommendations. You MUST respond with ONLY a valid JSON array, no additional text. Start with [ and end with ]."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                max_tokens=600,
                temperature=0.3
            )
            
            response_content = response.choices[0].message.content.strip()
            
            try:
                recommendations = json.loads(response_content)
            except json.JSONDecodeError:
                # Try to extract JSON array from response
                try:
                    start_idx = response_content.find('[')
                    end_idx = response_content.rfind(']') + 1
                    
                    if start_idx != -1 and end_idx != 0:
                        json_str = response_content[start_idx:end_idx]
                        recommendations = json.loads(json_str)
                    else:
                        raise json.JSONDecodeError("No JSON array found", response_content, 0)
                        
                except json.JSONDecodeError:
                    recommendations = [
                        {
                            'name': f'AI {recommendation_type} recommendation',
                            'description': 'AI response parsing failed. Please try again.',
                            'reason': 'Generated by AI based on your preferences',
                            'raw_response': response_content[:300] + '...' if len(response_content) > 300 else response_content
                        }
                    ]
            
            return {
                'success': True,
                'recommendations': recommendations,
                'recommendation_type': recommendation_type
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'AI service error: {str(e)}',
                'recommendations': []
            }
    
    def select_optimal_table(self, restaurant_id, party_size, reservation_date, reservation_time, duration_hours, available_tables, user_preferences=None, special_occasion=None):
        """
        AI-powered intelligent table selection based on multiple factors
        """
        try:
            from restaurants.models import Restaurant, Table, Reservation
            from datetime import datetime, timedelta
            
            restaurant = Restaurant.objects.get(id=restaurant_id, is_active=True)
            
            if not available_tables:
                return {
                    'success': False,
                    'error': 'No available tables provided',
                    'selected_table': None,
                    'reasoning': 'No tables available for selection'
                }
            
            # Build context about available tables
            table_context = []
            for table in available_tables:
                # Get recent reservation history for this table
                recent_reservations = Reservation.objects.filter(
                    table=table,
                    reservation_date__gte=reservation_date - timedelta(days=30),
                    status__in=['confirmed', 'completed']
                ).count()
                
                table_info = {
                    'id': table.id,
                    'table_number': table.table_number,
                    'capacity': table.capacity,
                    'recent_bookings': recent_reservations,
                    'capacity_utilization': round((party_size / table.capacity) * 100, 1)
                }
                table_context.append(table_info)
            
            # Build user preferences context
            preferences_text = ""
            if user_preferences:
                if isinstance(user_preferences, dict):
                    prefs = []
                    for key, value in user_preferences.items():
                        if value:
                            prefs.append(f"{key}: {value}")
                    preferences_text = ", ".join(prefs) if prefs else "None specified"
                else:
                    preferences_text = str(user_preferences)
            else:
                preferences_text = "None specified"
            
            # Build the AI prompt
            prompt = f"""You are an intelligent table selection system for {restaurant.name}. 
            
Reservation Details:
- Party size: {party_size} people
- Date: {reservation_date}
- Time: {reservation_time}
- Duration: {duration_hours} hours
- Special occasion: {special_occasion or 'None'}
- User preferences: {preferences_text}

Available Tables:
{json.dumps(table_context, indent=2)}

Selection Criteria (in order of importance):
1. Optimal capacity utilization (prefer tables that fit the party size well, not too big or too small)
2. Table popularity (balance between popular and less used tables)
3. Special occasion considerations (if applicable)
4. User preferences (if any)

Please analyze each table and select the BEST one. Consider:
- A table with 80-100% capacity utilization is ideal
- For special occasions, prefer tables with better positioning or ambiance
- Balance table usage to distribute wear evenly
- Avoid oversized tables unless necessary

Respond with EXACTLY this JSON structure:
{{
  "selected_table_id": table_id_number,
  "reasoning": "Brief explanation of why this table was selected",
  "confidence": confidence_score_0_to_1,
  "alternative_table_id": alternative_table_id_or_null,
  "factors_considered": ["factor1", "factor2", "factor3"]
}}

Select only from the provided available tables."""
            
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an intelligent table selection AI. You MUST respond with ONLY valid JSON, no additional text. Start with { and end with }."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                max_tokens=400,
                temperature=0.2  # Low temperature for consistent decision making
            )
            
            response_content = response.choices[0].message.content.strip()
            
            try:
                selection_result = json.loads(response_content)
                
                # Validate the selected table ID is in available tables
                selected_table_id = selection_result.get('selected_table_id')
                available_table_ids = [t.id for t in available_tables]
                
                if selected_table_id not in available_table_ids:
                    # Fallback to first available table if AI selected invalid table
                    selected_table = available_tables[0]
                    selection_result['selected_table_id'] = selected_table.id
                    selection_result['reasoning'] = f"AI selected invalid table, defaulted to Table {selected_table.table_number}"
                    selection_result['confidence'] = 0.5
                else:
                    selected_table = next(t for t in available_tables if t.id == selected_table_id)
                
                return {
                    'success': True,
                    'selected_table': selected_table,
                    'reasoning': selection_result.get('reasoning', 'AI-powered selection'),
                    'confidence': selection_result.get('confidence', 0.8),
                    'alternative_table_id': selection_result.get('alternative_table_id'),
                    'factors_considered': selection_result.get('factors_considered', []),
                    'ai_response': selection_result
                }
                
            except json.JSONDecodeError:
                # Try to extract JSON from response
                try:
                    start_idx = response_content.find('{')
                    end_idx = response_content.rfind('}') + 1
                    
                    if start_idx != -1 and end_idx != 0:
                        json_str = response_content[start_idx:end_idx]
                        selection_result = json.loads(json_str)
                        
                        # Same validation as above
                        selected_table_id = selection_result.get('selected_table_id')
                        available_table_ids = [t.id for t in available_tables]
                        
                        if selected_table_id not in available_table_ids:
                            selected_table = available_tables[0]
                            selection_result['selected_table_id'] = selected_table.id
                            selection_result['reasoning'] = f"AI parsing issue, defaulted to Table {selected_table.table_number}"
                        else:
                            selected_table = next(t for t in available_tables if t.id == selected_table_id)
                        
                        return {
                            'success': True,
                            'selected_table': selected_table,
                            'reasoning': selection_result.get('reasoning', 'AI-powered selection with parsing recovery'),
                            'confidence': selection_result.get('confidence', 0.7),
                            'alternative_table_id': selection_result.get('alternative_table_id'),
                            'factors_considered': selection_result.get('factors_considered', []),
                            'ai_response': selection_result
                        }
                    else:
                        raise json.JSONDecodeError("No JSON object found", response_content, 0)
                        
                except json.JSONDecodeError:
                    # Final fallback - return first available table
                    selected_table = available_tables[0]
                    return {
                        'success': False,
                        'selected_table': selected_table,
                        'reasoning': f'AI response parsing failed, selected Table {selected_table.table_number} as fallback',
                        'confidence': 0.3,
                        'alternative_table_id': None,
                        'factors_considered': ['fallback_selection'],
                        'error': 'AI response parsing failed',
                        'raw_response': response_content[:200] + '...' if len(response_content) > 200 else response_content
                    }
            
        except Exception as e:
            # Complete fallback - select first available table
            if available_tables:
                selected_table = available_tables[0]
                return {
                    'success': False,
                    'selected_table': selected_table,
                    'reasoning': f'AI service error, selected Table {selected_table.table_number} as fallback',
                    'confidence': 0.2,
                    'alternative_table_id': None,
                    'factors_considered': ['error_fallback'],
                    'error': f'AI service error: {str(e)}'
                }
            else:
                return {
                    'success': False,
                    'selected_table': None,
                    'reasoning': 'No available tables and AI service failed',
                    'confidence': 0.0,
                    'alternative_table_id': None,
                    'factors_considered': [],
                    'error': f'AI service error: {str(e)}'
                }