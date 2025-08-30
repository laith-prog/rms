"""
Signals for Restaurants app to send notifications automatically on reservation changes.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ReservationStatusUpdate
from notifications.helpers import send_reservation_notification


@receiver(post_save, sender=ReservationStatusUpdate)
def reservation_status_update_notify(sender, instance: ReservationStatusUpdate, created, **kwargs):
    """Send notification when a ReservationStatusUpdate is created."""
    if not created:
        return

    reservation = instance.reservation

    mapping = {
        'confirmed': 'reservation_confirmed',
        'cancelled': 'reservation_cancelled',
        # Reminder is usually time-based; signal won’t send reminders automatically.
    }

    notif_type = mapping.get(instance.status)
    if not notif_type:
        return

    # Avoid duplicate sends
    if getattr(instance, 'is_notified', False):
        return

    extra_context = {}
    if instance.notes:
        extra_context['notes'] = instance.notes

    result = send_reservation_notification(reservation, notif_type, **extra_context)

    try:
        if isinstance(result, dict) and result.get('success_count', 0) > 0:
            instance.is_notified = True
            instance.save(update_fields=['is_notified'])
    except Exception:
        pass