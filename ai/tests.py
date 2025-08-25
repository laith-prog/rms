from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, time
from restaurants.models import Restaurant, Table, Category
from ai.services import AIService
from ai.models import TableSelectionLog

User = get_user_model()


class AITableSelectionTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create a test user
        self.user = User.objects.create_user(
            email='test@example.com',
            phone='+1234567890',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create a test category
        self.category = Category.objects.create(
            name='Italian',
            description='Italian cuisine'
        )
        
        # Create a test restaurant
        self.restaurant = Restaurant.objects.create(
            name='Test Restaurant',
            address='123 Test St',
            phone='1234567890',
            opening_time=time(9, 0),
            closing_time=time(22, 0)
        )
        self.restaurant.categories.add(self.category)
        
        # Create test tables
        self.table1 = Table.objects.create(
            restaurant=self.restaurant,
            table_number='T1',
            capacity=2
        )
        self.table2 = Table.objects.create(
            restaurant=self.restaurant,
            table_number='T2',
            capacity=4
        )
        self.table3 = Table.objects.create(
            restaurant=self.restaurant,
            table_number='T3',
            capacity=6
        )
        
        try:
            self.ai_service = AIService()
        except Exception:
            # Skip tests if AI service can't be initialized (e.g., missing API key)
            self.skipTest("AI service initialization failed - likely missing API key or dependency issue")
    
    def test_ai_table_selection_fallback(self):
        """Test that AI table selection falls back gracefully when AI fails"""
        available_tables = [self.table1, self.table2, self.table3]
        
        # Test with invalid API key to trigger fallback
        original_api_key = self.ai_service.client.api_key
        self.ai_service.client.api_key = "invalid_key"
        
        result = self.ai_service.select_optimal_table(
            restaurant_id=self.restaurant.id,
            party_size=2,
            reservation_date=date.today(),
            reservation_time=time(19, 0),
            duration_hours=2,
            available_tables=available_tables
        )
        
        # Should fallback to first available table
        self.assertIsNotNone(result.get('selected_table'))
        self.assertEqual(result['selected_table'], available_tables[0])
        self.assertFalse(result.get('success', True))
        self.assertIn('error', result)
        
        # Restore original API key
        self.ai_service.client.api_key = original_api_key
    
    def test_ai_table_selection_empty_tables(self):
        """Test AI table selection with no available tables"""
        result = self.ai_service.select_optimal_table(
            restaurant_id=self.restaurant.id,
            party_size=2,
            reservation_date=date.today(),
            reservation_time=time(19, 0),
            duration_hours=2,
            available_tables=[]
        )
        
        self.assertFalse(result.get('success', True))
        self.assertIsNone(result.get('selected_table'))
        self.assertIn('error', result)
    
    def test_ai_table_selection_with_preferences(self):
        """Test AI table selection with user preferences"""
        available_tables = [self.table1, self.table2, self.table3]
        user_preferences = {
            'quiet_area': True,
            'window_seat': False
        }
        
        result = self.ai_service.select_optimal_table(
            restaurant_id=self.restaurant.id,
            party_size=2,
            reservation_date=date.today(),
            reservation_time=time(19, 0),
            duration_hours=2,
            available_tables=available_tables,
            user_preferences=user_preferences,
            special_occasion='birthday'
        )
        
        # Should return a table (either AI selected or fallback)
        self.assertIsNotNone(result.get('selected_table'))
        self.assertIn(result['selected_table'], available_tables)
        self.assertIn('reasoning', result)
        self.assertIn('confidence', result)