from django.core.management.base import BaseCommand
from notifications.models import NotificationTemplate


class Command(BaseCommand):
    help = 'Create default notification templates'

    def handle(self, *args, **options):
        templates = [
            {
                'name': 'Order Placed',
                'notification_type': 'order_placed',
                'title_template': 'Order Confirmed! 🎉',
                'body_template': 'Your order #{order_id} has been placed successfully at {restaurant_name}. Total: ${total_amount}',
                'data_template': {
                    'order_id': '{order_id}',
                    'restaurant_id': '{restaurant_id}',
                    'type': 'order_update'
                }
            },
            {
                'name': 'Order Confirmed',
                'notification_type': 'order_confirmed',
                'title_template': 'Order Confirmed by Restaurant 👨‍🍳',
                'body_template': 'Great news! {restaurant_name} has confirmed your order #{order_id}. Estimated time: {estimated_time} minutes.',
                'data_template': {
                    'order_id': '{order_id}',
                    'restaurant_id': '{restaurant_id}',
                    'type': 'order_update'
                }
            },
            {
                'name': 'Order Preparing',
                'notification_type': 'order_preparing',
                'title_template': 'Your Order is Being Prepared 🍳',
                'body_template': 'The kitchen at {restaurant_name} is now preparing your order #{order_id}. It will be ready soon!',
                'data_template': {
                    'order_id': '{order_id}',
                    'restaurant_id': '{restaurant_id}',
                    'type': 'order_update'
                }
            },
            {
                'name': 'Order Ready',
                'notification_type': 'order_ready',
                'title_template': 'Order Ready for Pickup! 🥘',
                'body_template': 'Your order #{order_id} is ready for pickup at {restaurant_name}. Please collect it within 15 minutes.',
                'data_template': {
                    'order_id': '{order_id}',
                    'restaurant_id': '{restaurant_id}',
                    'type': 'order_update'
                }
            },
            {
                'name': 'Order Delivered',
                'notification_type': 'order_delivered',
                'title_template': 'Order Delivered Successfully! ✅',
                'body_template': 'Your order #{order_id} from {restaurant_name} has been delivered. Enjoy your meal!',
                'data_template': {
                    'order_id': '{order_id}',
                    'restaurant_id': '{restaurant_id}',
                    'type': 'order_update'
                }
            },
            {
                'name': 'Order Cancelled',
                'notification_type': 'order_cancelled',
                'title_template': 'Order Cancelled ❌',
                'body_template': 'Your order #{order_id} from {restaurant_name} has been cancelled. Reason: {cancellation_reason}',
                'data_template': {
                    'order_id': '{order_id}',
                    'restaurant_id': '{restaurant_id}',
                    'type': 'order_update'
                }
            },
            {
                'name': 'Reservation Confirmed',
                'notification_type': 'reservation_confirmed',
                'title_template': 'Reservation Confirmed! 🍽️',
                'body_template': 'Your table reservation at {restaurant_name} for {party_size} people on {date} at {time} has been confirmed.',
                'data_template': {
                    'reservation_id': '{reservation_id}',
                    'restaurant_id': '{restaurant_id}',
                    'type': 'reservation_update'
                }
            },
            {
                'name': 'Reservation Reminder',
                'notification_type': 'reservation_reminder',
                'title_template': 'Reservation Reminder ⏰',
                'body_template': 'Don\'t forget! You have a reservation at {restaurant_name} today at {time} for {party_size} people.',
                'data_template': {
                    'reservation_id': '{reservation_id}',
                    'restaurant_id': '{restaurant_id}',
                    'type': 'reservation_reminder'
                }
            },
            {
                'name': 'Payment Success',
                'notification_type': 'payment_success',
                'title_template': 'Payment Successful! 💳',
                'body_template': 'Your payment of ${amount} for order #{order_id} has been processed successfully.',
                'data_template': {
                    'order_id': '{order_id}',
                    'payment_id': '{payment_id}',
                    'type': 'payment_update'
                }
            },
            {
                'name': 'Payment Failed',
                'notification_type': 'payment_failed',
                'title_template': 'Payment Failed ⚠️',
                'body_template': 'Your payment for order #{order_id} could not be processed. Please try again or use a different payment method.',
                'data_template': {
                    'order_id': '{order_id}',
                    'type': 'payment_update'
                }
            },
            {
                'name': 'Special Promotion',
                'notification_type': 'promotion',
                'title_template': 'Special Offer Just for You! 🎁',
                'body_template': '{promotion_title}: {promotion_description}. Use code: {promo_code}',
                'data_template': {
                    'promotion_id': '{promotion_id}',
                    'promo_code': '{promo_code}',
                    'type': 'promotion'
                }
            }
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = NotificationTemplate.objects.get_or_create(
                name=template_data['name'],
                notification_type=template_data['notification_type'],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.name}')
                )
            else:
                # Update existing template
                for key, value in template_data.items():
                    setattr(template, key, value)
                template.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated template: {template.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Created {created_count} new templates, updated {updated_count} existing templates.'
            )
        )