"""
Utility functions for restaurant operations
"""
from datetime import datetime
from django.utils import timezone
from django.conf import settings


def can_cancel_reservation(reservation):
    """
    Check if a reservation can be cancelled based on business rules.
    
    Args:
        reservation: Reservation instance
        
    Returns:
        tuple: (can_cancel: bool, reason: str)
    """
    # Check if reservation is in a cancellable state
    if reservation.status == 'cancelled':
        return False, 'Reservation is already cancelled'
    
    if reservation.status == 'completed':
        return False, 'Cannot cancel completed reservations'
    
    # Check if reservation is in the past
    if reservation.reservation_date < timezone.now().date():
        return False, 'Cannot cancel past reservations'
    
    # Get cancellation policy from settings
    cancellation_policy = getattr(settings, 'RESERVATION_CANCELLATION', {})
    minimum_hours = cancellation_policy.get('MINIMUM_ADVANCE_HOURS', 24)
    allow_same_day = cancellation_policy.get('ALLOW_SAME_DAY_CANCELLATION', False)
    emergency_contact = cancellation_policy.get('EMERGENCY_CONTACT_INFO', 'Please contact the restaurant directly')
    
    # Calculate time until reservation
    now = timezone.now()
    reservation_datetime = datetime.combine(reservation.reservation_date, reservation.reservation_time)
    reservation_datetime = timezone.make_aware(reservation_datetime) if timezone.is_naive(reservation_datetime) else reservation_datetime
    time_until_reservation = reservation_datetime - now
    
    # Check minimum advance notice
    if time_until_reservation.total_seconds() < (minimum_hours * 3600):
        hours_remaining = max(0, time_until_reservation.total_seconds() / 3600)
        return False, (
            f'Cannot cancel reservation. Minimum {minimum_hours} hours advance notice required. '
            f'Only {hours_remaining:.1f} hours remaining until your reservation. {emergency_contact}'
        )
    
    # Check same-day cancellation policy
    if not allow_same_day and reservation.reservation_date == now.date():
        return False, f'Same-day cancellations are not allowed. {emergency_contact}'
    
    return True, 'Reservation can be cancelled'


def get_cancellation_deadline(reservation):
    """
    Get the deadline for cancelling a reservation.
    
    Args:
        reservation: Reservation instance
        
    Returns:
        datetime: The latest time the reservation can be cancelled
    """
    cancellation_policy = getattr(settings, 'RESERVATION_CANCELLATION', {})
    minimum_hours = cancellation_policy.get('MINIMUM_ADVANCE_HOURS', 24)
    
    reservation_datetime = datetime.combine(reservation.reservation_date, reservation.reservation_time)
    reservation_datetime = timezone.make_aware(reservation_datetime) if timezone.is_naive(reservation_datetime) else reservation_datetime
    
    from datetime import timedelta
    cancellation_deadline = reservation_datetime - timedelta(hours=minimum_hours)
    
    return cancellation_deadline


def get_reservation_cancellation_info(reservation):
    """
    Get comprehensive cancellation information for a reservation.
    
    Args:
        reservation: Reservation instance
        
    Returns:
        dict: Cancellation information including status, deadline, and policy details
    """
    can_cancel, reason = can_cancel_reservation(reservation)
    cancellation_deadline = get_cancellation_deadline(reservation)
    
    cancellation_policy = getattr(settings, 'RESERVATION_CANCELLATION', {})
    
    return {
        'can_cancel': can_cancel,
        'reason': reason,
        'cancellation_deadline': cancellation_deadline.isoformat() if cancellation_deadline else None,
        'policy': {
            'minimum_advance_hours': cancellation_policy.get('MINIMUM_ADVANCE_HOURS', 24),
            'allow_same_day_cancellation': cancellation_policy.get('ALLOW_SAME_DAY_CANCELLATION', False),
            'emergency_contact_info': cancellation_policy.get('EMERGENCY_CONTACT_INFO', 'Please contact the restaurant directly'),
        }
    }