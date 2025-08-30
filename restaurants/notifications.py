"""
Notification utilities for reservation and order status updates
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_reservation_status_notification(reservation, status, notes=None):
    """
    Send notification to customer about reservation status change
    """
    customer = reservation.customer
    restaurant = reservation.restaurant
    
    # Email subject based on status
    subject_map = {
        'confirmed': f'Reservation Confirmed - {restaurant.name}',
        'cancelled': f'Reservation Cancelled - {restaurant.name}',
        'completed': f'Thank you for dining with us - {restaurant.name}',
    }
    
    subject = subject_map.get(status, f'Reservation Update - {restaurant.name}')
    
    # Email context
    context = {
        'customer': customer,
        'reservation': reservation,
        'restaurant': restaurant,
        'status': status,
        'notes': notes,
    }
    
    # Render email template
    html_message = render_to_string('emails/reservation_status_update.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email if customer has email
    if customer.email:
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[customer.email],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send reservation notification email: {e}")
    
    # TODO: Add SMS notification using Twilio if phone number is available
    # This would require Twilio configuration
    
    return True


def send_order_status_notification(order, status, notes=None):
    """
    Send notification to customer about order status change
    """
    customer = order.customer
    restaurant = order.restaurant
    
    # Email subject based on status
    subject_map = {
        'approved': f'Order Approved - {restaurant.name}',
        'rejected': f'Order Rejected - {restaurant.name}',
        'preparing': f'Your order is being prepared - {restaurant.name}',
        'ready': f'Your order is ready - {restaurant.name}',
        'completed': f'Order completed - {restaurant.name}',
    }
    
    subject = subject_map.get(status, f'Order Update - {restaurant.name}')
    
    # Email context
    context = {
        'customer': customer,
        'order': order,
        'restaurant': restaurant,
        'status': status,
        'notes': notes,
    }
    
    # Render email template
    html_message = render_to_string('emails/order_status_update.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email if customer has email
    if customer.email:
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[customer.email],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send order notification email: {e}")
    
    # TODO: Add SMS notification using Twilio if phone number is available
    
    return True


def get_notification_preferences(user):
    """
    Get user's notification preferences
    TODO: Implement user notification preferences model
    """
    return {
        'email': True,  # Default to email notifications
        'sms': False,   # Default to no SMS (requires setup)
        'push': False,  # Default to no push notifications
    }