from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import date, time
from restaurants.models import Restaurant, Table, Category
from ai.services import AIService

User = get_user_model()


class Command(BaseCommand):
    help = 'Test AI table selection functionality'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing AI Table Selection...'))
        
        try:
            # Get or create test data
            restaurant = Restaurant.objects.first()
            if not restaurant:
                self.stdout.write(self.style.ERROR('No restaurants found. Please create a restaurant first.'))
                return
            
            tables = Table.objects.filter(restaurant=restaurant, is_active=True)[:3]
            if not tables:
                self.stdout.write(self.style.ERROR('No tables found. Please create tables first.'))
                return
            
            self.stdout.write(f'Using restaurant: {restaurant.name}')
            self.stdout.write(f'Available tables: {[t.table_number for t in tables]}')
            
            # Test AI service
            ai_service = AIService()
            
            # Test 1: Normal AI selection
            self.stdout.write('\n--- Test 1: Normal AI Selection ---')
            result = ai_service.select_optimal_table(
                restaurant_id=restaurant.id,
                party_size=2,
                reservation_date=date.today(),
                reservation_time=time(19, 0),
                duration_hours=2,
                available_tables=list(tables),
                user_preferences={'quiet_area': True},
                special_occasion='birthday'
            )
            
            self.stdout.write(f'Success: {result.get("success", False)}')
            self.stdout.write(f'Selected table: {result.get("selected_table")}')
            self.stdout.write(f'Reasoning: {result.get("reasoning", "N/A")}')
            self.stdout.write(f'Confidence: {result.get("confidence", 0)}')
            
            # Test 2: Empty tables list
            self.stdout.write('\n--- Test 2: Empty Tables List ---')
            result = ai_service.select_optimal_table(
                restaurant_id=restaurant.id,
                party_size=2,
                reservation_date=date.today(),
                reservation_time=time(19, 0),
                duration_hours=2,
                available_tables=[],
            )
            
            self.stdout.write(f'Success: {result.get("success", False)}')
            self.stdout.write(f'Error: {result.get("error", "N/A")}')
            
            # Test 3: Fallback scenario (simulate API failure)
            self.stdout.write('\n--- Test 3: Fallback Scenario ---')
            original_api_key = ai_service.client.api_key
            ai_service.client.api_key = "invalid_key"
            
            result = ai_service.select_optimal_table(
                restaurant_id=restaurant.id,
                party_size=4,
                reservation_date=date.today(),
                reservation_time=time(20, 0),
                duration_hours=1,
                available_tables=list(tables),
            )
            
            self.stdout.write(f'Success: {result.get("success", False)}')
            self.stdout.write(f'Selected table: {result.get("selected_table")}')
            self.stdout.write(f'Reasoning: {result.get("reasoning", "N/A")}')
            self.stdout.write(f'Error: {result.get("error", "N/A")}')
            
            # Restore API key
            ai_service.client.api_key = original_api_key
            
            self.stdout.write(self.style.SUCCESS('\nAI Table Selection tests completed!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Test failed with error: {str(e)}'))