"""
Signals for Orders app to send notifications automatically on status or payment changes.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Order, OrderStatusUpdate
from notifications.helpers import (
    send_order_notification,
    send_payment_notification,
)


@receiver(post_save, sender=OrderStatusUpdate)
def order_status_update_notify(sender, instance: OrderStatusUpdate, created, **kwargs):
    """Send notification when an OrderStatusUpdate is created."""
    if not created:
        return

    order = instance.order

    # Map order model status to notification types used by helpers/templates
    status_to_notification = {
        'pending': 'order_placed',
        'approved': 'order_confirmed',
        'preparing': 'order_preparing',
        'ready': 'order_ready',
        'completed': 'order_delivered',  # Treat completed as delivered for user-facing wording
        'cancelled': 'order_cancelled',
        'rejected': 'order_cancelled',
    }

    notif_type = status_to_notification.get(instance.status)
    if not notif_type:
        return

    # Avoid duplicate sends if someone toggles is_notified manually in future
    if getattr(instance, 'is_notified', False):
        return

    # Build extra context from status update
    extra_context = {}
    if instance.notes:
        extra_context['notes'] = instance.notes

    result = send_order_notification(order, notif_type, **extra_context)

    # Mark as notified on success
    try:
        if isinstance(result, dict) and result.get('success_count', 0) > 0:
            instance.is_notified = True
            instance.notification_message = f"Notification sent: {notif_type}"
            instance.save(update_fields=['is_notified', 'notification_message'])
    except Exception:
        # Do not break signal flow
        pass


@receiver(post_save, sender=Order)
def order_payment_status_notify(sender, instance: Order, created, **kwargs):
    """Notify on payment status transitions (fire only on updates)."""
    if created:
        return

    # We only care about payment_success / payment_failed
    payment_map = {
        'paid': 'payment_success',
        'failed': 'payment_failed',
        'refunded': None,  # no default template; can add if needed
    }

    notif_type = payment_map.get(instance.payment_status)
    if not notif_type:
        return

    # Best-effort: avoid spamming, if latest status update already notified for same type
    # (We don't have a dedicated payment log; rely on NotificationLog dedup at service level)
    try:
        send_payment_notification(instance, notif_type)
    except Exception:
        # Never raise inside signals
        pass