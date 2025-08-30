"""
Tests for reservation cancellation functionality
"""
from datetime import datetime, timedelta, date, time
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from restaurants.models import Restaurant, Table, Reservation
from restaurants.utils import can_cancel_reservation, get_cancellation_deadline

User = get_user_model()


class ReservationCancellationTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create a customer
        self.customer = User.objects.create_user(
            phone='+1234567890',
            password='testpass123',
            is_customer=True
        )
        
        # Create a restaurant
        self.restaurant = Restaurant.objects.create(
            name='Test Restaurant',
            address='123 Test St',
            phone='+1987654321',
            description='Test restaurant',
            opening_time=time(9, 0),  # 9:00 AM
            closing_time=time(22, 0)  # 10:00 PM
        )
        
        # Create a table
        self.table = Table.objects.create(
            restaurant=self.restaurant,
            table_number='T1',
            capacity=4
        )
    
    def create_reservation(self, days_ahead=1, hours_ahead=0):
        """Helper to create a reservation"""
        reservation_date = (timezone.now() + timedelta(days=days_ahead)).date()
        reservation_time = (timezone.now() + timedelta(hours=hours_ahead)).time()
        
        return Reservation.objects.create(
            customer=self.customer,
            restaurant=self.restaurant,
            table=self.table,
            party_size=2,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            status='confirmed'
        )
    
    @override_settings(RESERVATION_CANCELLATION={
        'MINIMUM_ADVANCE_HOURS': 24,
        'ALLOW_SAME_DAY_CANCELLATION': False,
        'EMERGENCY_CONTACT_INFO': 'Call restaurant'
    })
    def test_can_cancel_with_sufficient_notice(self):
        """Test that reservation can be cancelled with sufficient advance notice"""
        # Create reservation 2 days ahead
        reservation = self.create_reservation(days_ahead=2)
        
        can_cancel, reason = can_cancel_reservation(reservation)
        self.assertTrue(can_cancel)
        self.assertEqual(reason, 'Reservation can be cancelled')
    
    @override_settings(RESERVATION_CANCELLATION={
        'MINIMUM_ADVANCE_HOURS': 24,
        'ALLOW_SAME_DAY_CANCELLATION': False,
        'EMERGENCY_CONTACT_INFO': 'Call restaurant'
    })
    def test_cannot_cancel_insufficient_notice(self):
        """Test that reservation cannot be cancelled without sufficient advance notice"""
        # Create reservation 12 hours ahead (less than 24 hour requirement)
        now = timezone.now()
        reservation_datetime = now + timedelta(hours=12)
        
        reservation = Reservation.objects.create(
            customer=self.customer,
            restaurant=self.restaurant,
            table=self.table,
            party_size=2,
            reservation_date=reservation_datetime.date(),
            reservation_time=reservation_datetime.time(),
            status='confirmed'
        )
        
        can_cancel, reason = can_cancel_reservation(reservation)
        self.assertFalse(can_cancel)
        self.assertIn('Minimum 24 hours advance notice required', reason)
    
    @override_settings(RESERVATION_CANCELLATION={
        'MINIMUM_ADVANCE_HOURS': 2,
        'ALLOW_SAME_DAY_CANCELLATION': False,
        'EMERGENCY_CONTACT_INFO': 'Call restaurant'
    })
    def test_cannot_cancel_same_day_when_disabled(self):
        """Test that same-day cancellation is blocked when disabled"""
        # Create reservation for today but with sufficient hours notice
        now = timezone.now()
        reservation_time = (now + timedelta(hours=4)).time()
        
        reservation = Reservation.objects.create(
            customer=self.customer,
            restaurant=self.restaurant,
            table=self.table,
            party_size=2,
            reservation_date=now.date(),
            reservation_time=reservation_time,
            status='confirmed'
        )
        
        can_cancel, reason = can_cancel_reservation(reservation)
        self.assertFalse(can_cancel)
        self.assertIn('Same-day cancellations are not allowed', reason)
    
    @override_settings(RESERVATION_CANCELLATION={
        'MINIMUM_ADVANCE_HOURS': 2,
        'ALLOW_SAME_DAY_CANCELLATION': True,
        'EMERGENCY_CONTACT_INFO': 'Call restaurant'
    })
    def test_can_cancel_same_day_when_enabled(self):
        """Test that same-day cancellation works when enabled"""
        # Create reservation for today with sufficient hours notice
        now = timezone.now()
        reservation_time = (now + timedelta(hours=4)).time()
        
        reservation = Reservation.objects.create(
            customer=self.customer,
            restaurant=self.restaurant,
            table=self.table,
            party_size=2,
            reservation_date=now.date(),
            reservation_time=reservation_time,
            status='confirmed'
        )
        
        can_cancel, reason = can_cancel_reservation(reservation)
        self.assertTrue(can_cancel)
        self.assertEqual(reason, 'Reservation can be cancelled')
    
    def test_cannot_cancel_already_cancelled(self):
        """Test that already cancelled reservations cannot be cancelled again"""
        reservation = self.create_reservation(days_ahead=2)
        reservation.status = 'cancelled'
        reservation.save()
        
        can_cancel, reason = can_cancel_reservation(reservation)
        self.assertFalse(can_cancel)
        self.assertEqual(reason, 'Reservation is already cancelled')
    
    def test_cannot_cancel_completed(self):
        """Test that completed reservations cannot be cancelled"""
        reservation = self.create_reservation(days_ahead=2)
        reservation.status = 'completed'
        reservation.save()
        
        can_cancel, reason = can_cancel_reservation(reservation)
        self.assertFalse(can_cancel)
        self.assertEqual(reason, 'Cannot cancel completed reservations')
    
    def test_cannot_cancel_past_reservation(self):
        """Test that past reservations cannot be cancelled"""
        # Create reservation in the past
        past_date = (timezone.now() - timedelta(days=1)).date()
        reservation = Reservation.objects.create(
            customer=self.customer,
            restaurant=self.restaurant,
            table=self.table,
            party_size=2,
            reservation_date=past_date,
            reservation_time=time(18, 0),
            status='confirmed'
        )
        
        can_cancel, reason = can_cancel_reservation(reservation)
        self.assertFalse(can_cancel)
        self.assertEqual(reason, 'Cannot cancel past reservations')
    
    @override_settings(RESERVATION_CANCELLATION={
        'MINIMUM_ADVANCE_HOURS': 24,
        'ALLOW_SAME_DAY_CANCELLATION': False,
        'EMERGENCY_CONTACT_INFO': 'Call restaurant'
    })
    def test_cancellation_deadline_calculation(self):
        """Test that cancellation deadline is calculated correctly"""
        # Create reservation 2 days ahead at 6 PM
        future_date = (timezone.now() + timedelta(days=2)).date()
        reservation_time = time(18, 0)
        
        reservation = Reservation.objects.create(
            customer=self.customer,
            restaurant=self.restaurant,
            table=self.table,
            party_size=2,
            reservation_date=future_date,
            reservation_time=reservation_time,
            status='confirmed'
        )
        
        deadline = get_cancellation_deadline(reservation)
        
        # Deadline should be 24 hours before the reservation
        expected_deadline = datetime.combine(future_date, reservation_time) - timedelta(hours=24)
        expected_deadline = timezone.make_aware(expected_deadline)
        
        self.assertEqual(deadline, expected_deadline)