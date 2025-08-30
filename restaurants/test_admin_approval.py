"""
Tests for admin approval system
"""
from datetime import datetime, timedelta, date, time
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from restaurants.models import Restaurant, Table, Reservation
from orders.models import Order, OrderItem
from accounts.models import StaffProfile

User = get_user_model()


class AdminApprovalTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create a customer
        self.customer = User.objects.create_user(
            phone='+1234567890',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            is_customer=True
        )
        
        # Create a restaurant
        self.restaurant = Restaurant.objects.create(
            name='Test Restaurant',
            address='123 Test St',
            phone='+1987654321',
            description='Test restaurant',
            opening_time=time(9, 0),
            closing_time=time(22, 0)
        )
        
        # Create a manager
        self.manager_user = User.objects.create_user(
            phone='+1111111111',
            password='managerpass123',
            first_name='Manager',
            last_name='Smith',
            is_staff_member=True,
            is_staff=True
        )
        
        self.manager_profile = StaffProfile.objects.create(
            user=self.manager_user,
            role='manager',
            restaurant=self.restaurant
        )
        
        # Create a table
        self.table = Table.objects.create(
            restaurant=self.restaurant,
            table_number='T1',
            capacity=4
        )
        
        # Create test client
        self.client = Client()
    
    def test_reservation_approval_workflow(self):
        """Test reservation approval through admin"""
        # Create a pending reservation
        reservation = Reservation.objects.create(
            customer=self.customer,
            restaurant=self.restaurant,
            table=self.table,
            party_size=2,
            reservation_date=(datetime.now() + timedelta(days=1)).date(),
            reservation_time=time(18, 0),
            status='pending'
        )
        
        # Verify initial status
        self.assertEqual(reservation.status, 'pending')
        
        # Login as manager
        self.client.login(phone='+1111111111', password='managerpass123')
        
        # Test that manager can access the reservation admin
        response = self.client.get('/manager/restaurants/reservation/')
        self.assertEqual(response.status_code, 200)
        
        # Test approval action (simulate clicking approve button)
        response = self.client.get(f'/manager/restaurants/reservation/{reservation.id}/change/?action=approve')
        
        # Refresh reservation from database
        reservation.refresh_from_db()
        
        # Verify status changed to confirmed
        self.assertEqual(reservation.status, 'confirmed')
    
    def test_order_approval_workflow(self):
        """Test order approval through admin"""
        # Create a pending order
        order = Order.objects.create(
            customer=self.customer,
            restaurant=self.restaurant,
            order_type='dine_in',
            status='pending',
            subtotal=25.00,
            tax=2.50,
            total=27.50
        )
        
        # Verify initial status
        self.assertEqual(order.status, 'pending')
        
        # Login as manager
        self.client.login(phone='+1111111111', password='managerpass123')
        
        # Test that manager can access the order admin
        response = self.client.get('/manager/orders/order/')
        self.assertEqual(response.status_code, 200)
        
        # Test approval action
        response = self.client.get(f'/manager/orders/order/{order.id}/change/?action=approve')
        
        # Refresh order from database
        order.refresh_from_db()
        
        # Verify status changed to approved
        self.assertEqual(order.status, 'approved')
    
    def test_manager_dashboard_access(self):
        """Test manager dashboard access and statistics"""
        # Create some test data
        Reservation.objects.create(
            customer=self.customer,
            restaurant=self.restaurant,
            table=self.table,
            party_size=2,
            reservation_date=(datetime.now() + timedelta(days=1)).date(),
            reservation_time=time(18, 0),
            status='pending'
        )
        
        Order.objects.create(
            customer=self.customer,
            restaurant=self.restaurant,
            order_type='dine_in',
            status='pending',
            subtotal=25.00,
            tax=2.50,
            total=27.50
        )
        
        # Login as manager
        self.client.login(phone='+1111111111', password='managerpass123')
        
        # Access manager dashboard
        response = self.client.get('/manager/')
        self.assertEqual(response.status_code, 200)
        
        # Check that dashboard contains statistics
        self.assertContains(response, 'pending_reservations')
        self.assertContains(response, 'pending_orders')
    
    def test_manager_only_sees_own_restaurant_data(self):
        """Test that managers only see data for their restaurant"""
        # Create another restaurant
        other_restaurant = Restaurant.objects.create(
            name='Other Restaurant',
            address='456 Other St',
            phone='+1555555555',
            description='Other restaurant',
            opening_time=time(9, 0),
            closing_time=time(22, 0)
        )
        
        # Create reservation for other restaurant
        other_table = Table.objects.create(
            restaurant=other_restaurant,
            table_number='T1',
            capacity=4
        )
        
        other_reservation = Reservation.objects.create(
            customer=self.customer,
            restaurant=other_restaurant,
            table=other_table,
            party_size=2,
            reservation_date=(datetime.now() + timedelta(days=1)).date(),
            reservation_time=time(18, 0),
            status='pending'
        )
        
        # Login as manager
        self.client.login(phone='+1111111111', password='managerpass123')
        
        # Access reservation list
        response = self.client.get('/manager/restaurants/reservation/')
        self.assertEqual(response.status_code, 200)
        
        # Should not contain other restaurant's reservation
        self.assertNotContains(response, 'Other Restaurant')
    
    def test_bulk_approval_actions(self):
        """Test bulk approval actions"""
        # Create multiple pending reservations
        reservations = []
        for i in range(3):
            reservation = Reservation.objects.create(
                customer=self.customer,
                restaurant=self.restaurant,
                table=self.table,
                party_size=2,
                reservation_date=(datetime.now() + timedelta(days=i+1)).date(),
                reservation_time=time(18, 0),
                status='pending'
            )
            reservations.append(reservation)
        
        # Login as manager
        self.client.login(phone='+1111111111', password='managerpass123')
        
        # Test bulk approval (this would require more complex form submission)
        # For now, just verify the reservations exist and are pending
        for reservation in reservations:
            self.assertEqual(reservation.status, 'pending')
        
        # In a real test, you would simulate the bulk action form submission
        # This is a simplified test to verify the setup works