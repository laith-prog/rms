"""
Helper functions for sending notifications in different contexts
"""
from typing import Optional
from django.contrib.auth import get_user_model
from .services import notification_service

User = get_user_model()


def send_order_notification(order, notification_type: str, **extra_context):
    """
    Send order-related notification
    
    Args:
        order: Order instance
        notification_type: Type of notification (order_placed, order_confirmed, etc.)
        **extra_context: Additional context variables
    """
    # Our Order model uses 'customer' field
    if not getattr(order, 'customer', None):
        return
    
    # Build context from order
    context = {
        'order_id': str(order.id),
        'restaurant_name': order.restaurant.name,
        'restaurant_id': str(order.restaurant.id),
        'total_amount': str(order.total),
        'customer_name': order.customer.get_full_name() or getattr(order.customer, 'phone', ''),
        **extra_context
    }
    
    # Map notification types to template names
    template_mapping = {
        'order_placed': 'Order Placed',
        'order_confirmed': 'Order Confirmed',
        'order_preparing': 'Order Preparing',
        'order_ready': 'Order Ready',
        'order_delivered': 'Order Delivered',
        'order_cancelled': 'Order Cancelled',
    }
    
    template_name = template_mapping.get(notification_type)
    if not template_name:
        return
    
    return notification_service.send_templated_notification(
        template_name=template_name,
        notification_type=notification_type,
        context=context,
        user=order.customer,
        order=order
    )


def send_reservation_notification(reservation, notification_type: str, **extra_context):
    """
    Send reservation-related notification
    
    Args:
        reservation: Reservation instance
        notification_type: Type of notification
        **extra_context: Additional context variables
    """
    # Reservation model uses 'customer'
    if not getattr(reservation, 'customer', None):
        return
    
    # Build context from reservation
    context = {
        'reservation_id': str(reservation.id),
        'restaurant_name': reservation.restaurant.name,
        'restaurant_id': str(reservation.restaurant.id),
        'party_size': str(reservation.party_size),
        'date': reservation.reservation_date.strftime('%B %d, %Y'),
        'time': reservation.reservation_time.strftime('%I:%M %p'),
        'customer_name': reservation.customer.get_full_name() or getattr(reservation.customer, 'phone', ''),
        **extra_context
    }
    
    # Map notification types to template names
    template_mapping = {
        'reservation_confirmed': 'Reservation Confirmed',
        'reservation_reminder': 'Reservation Reminder',
        'reservation_cancelled': 'Reservation Cancelled',
    }
    
    template_name = template_mapping.get(notification_type)
    if not template_name:
        return
    
    return notification_service.send_templated_notification(
        template_name=template_name,
        notification_type=notification_type,
        context=context,
        user=reservation.customer,
        reservation=reservation
    )


def send_payment_notification(order, notification_type: str, payment_id: Optional[str] = None, **extra_context):
    """
    Send payment-related notification
    
    Args:
        order: Order instance
        notification_type: Type of notification (payment_success, payment_failed)
        payment_id: Payment ID if available
        **extra_context: Additional context variables
    """
    if not getattr(order, 'customer', None):
        return
    
    # Build context from order and payment
    context = {
        'order_id': str(order.id),
        'amount': str(order.total),
        'restaurant_name': order.restaurant.name,
        'customer_name': order.customer.get_full_name() or getattr(order.customer, 'phone', ''),
        **extra_context
    }
    
    if payment_id:
        context['payment_id'] = payment_id
    
    # Map notification types to template names
    template_mapping = {
        'payment_success': 'Payment Success',
        'payment_failed': 'Payment Failed',
    }
    
    template_name = template_mapping.get(notification_type)
    if not template_name:
        return
    
    return notification_service.send_templated_notification(
        template_name=template_name,
        notification_type=notification_type,
        context=context,
        user=order.customer,
        order=order
    )


def send_promotion_notification(users, promotion_data: dict):
    """
    Send promotion notification to multiple users
    
    Args:
        users: List of User instances or single User
        promotion_data: Dictionary with promotion details
    """
    context = {
        'promotion_title': promotion_data.get('title', 'Special Offer'),
        'promotion_description': promotion_data.get('description', ''),
        'promo_code': promotion_data.get('promo_code', ''),
        'promotion_id': promotion_data.get('id', ''),
    }
    
    if isinstance(users, list):
        return notification_service.send_templated_notification(
            template_name='Special Promotion',
            notification_type='promotion',
            context=context,
            users=users
        )
    else:
        return notification_service.send_templated_notification(
            template_name='Special Promotion',
            notification_type='promotion',
            context=context,
            user=users
        )


def send_custom_notification(users, title: str, body: str, data: dict = None, image_url: str = None):
    """
    Send custom notification
    
    Args:
        users: List of User instances or single User
        title: Notification title
        body: Notification body
        data: Optional custom data
        image_url: Optional image URL
    """
    if isinstance(users, list):
        return notification_service.send_notification_to_users(
            users=users,
            title=title,
            body=body,
            data=data or {},
            image_url=image_url,
            notification_type='custom'
        )
    else:
        return notification_service.send_notification_to_user(
            user=users,
            title=title,
            body=body,
            data=data or {},
            image_url=image_url,
            notification_type='custom'
        )