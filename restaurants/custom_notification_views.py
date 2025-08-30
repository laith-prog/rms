"""
Custom notification views for restaurant management
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django import forms
import json

from .models import Restaurant, Reservation, ReservationStatusUpdate, CustomNotificationLog
from orders.models import Order, OrderStatusUpdate
from accounts.models import StaffProfile


class CustomNotificationForm(forms.Form):
    """Form for sending custom notifications"""
    NOTIFICATION_TYPES = [
        ('reservation', 'Reservation'),
        ('order', 'Order'),
        ('general', 'General Message'),
    ]
    
    MESSAGE_TEMPLATES = [
        ('custom', 'Custom Message'),
        ('welcome', 'Welcome Message'),
        ('thank_you', 'Thank You Message'),
        ('special_offer', 'Special Offer'),
        ('event_invitation', 'Event Invitation'),
        ('feedback_request', 'Feedback Request'),
    ]
    
    notification_type = forms.ChoiceField(
        choices=NOTIFICATION_TYPES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_notification_type'})
    )
    
    template_type = forms.ChoiceField(
        choices=MESSAGE_TEMPLATES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_template_type'})
    )
    
    reservation_id = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter reservation ID'})
    )
    
    order_id = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter order ID'})
    )
    
    customer_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter customer phone'})
    )
    
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Notification title'})
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Enter your notification message here...'
        })
    )


def is_manager(user):
    """Check if user is a manager"""
    if user.is_superuser:
        return True
    if user.is_staff_member:
        try:
            staff_profile = user.staff_profile
            return staff_profile.role == 'manager'
        except:
            pass
    return False


@login_required
def custom_notification_view(request):
    """View for sending custom notifications to customers"""
    
    # Check if user is a manager
    if not is_manager(request.user):
        messages.error(request, 'Access denied. Manager privileges required.')
        return redirect('/')
    
    # Get manager's restaurant
    try:
        staff_profile = request.user.staff_profile
        restaurant = staff_profile.restaurant
    except:
        messages.error(request, 'Restaurant information not found.')
        return redirect('/')
    
    if request.method == 'POST':
        form = CustomNotificationForm(request.POST)
        if form.is_valid():
            result = send_custom_notification(request, form, restaurant)
            if result['success']:
                messages.success(request, result['message'])
                return redirect('manager:custom_notification')
            else:
                messages.error(request, result['message'])
    else:
        form = CustomNotificationForm()
    
    # Get recent reservations and orders for quick selection
    recent_reservations = Reservation.objects.filter(
        restaurant=restaurant
    ).order_by('-created_at')[:10]
    
    recent_orders = Order.objects.filter(
        restaurant=restaurant
    ).order_by('-created_at')[:10]
    
    context = {
        'form': form,
        'restaurant': restaurant,
        'recent_reservations': recent_reservations,
        'recent_orders': recent_orders,
        'title': 'Send Custom Notification',
    }
    
    return render(request, 'admin/custom_notification.html', context)


def send_custom_notification(request, form, restaurant):
    """Send custom notification based on form data"""
    try:
        notification_type = form.cleaned_data['notification_type']
        template_type = form.cleaned_data['template_type']
        title = form.cleaned_data['title']
        message = form.cleaned_data['message']
        
        # Determine recipient
        customer = None
        related_object = None
        
        if notification_type == 'reservation':
            reservation_id = form.cleaned_data.get('reservation_id')
            if reservation_id:
                try:
                    reservation = Reservation.objects.get(
                        id=reservation_id,
                        restaurant=restaurant
                    )
                    customer = reservation.customer
                    related_object = reservation
                except Reservation.DoesNotExist:
                    return {'success': False, 'message': 'Reservation not found.'}
        
        elif notification_type == 'order':
            order_id = form.cleaned_data.get('order_id')
            if order_id:
                try:
                    order = Order.objects.get(
                        id=order_id,
                        restaurant=restaurant
                    )
                    customer = order.customer
                    related_object = order
                except Order.DoesNotExist:
                    return {'success': False, 'message': 'Order not found.'}
        
        elif notification_type == 'general':
            customer_phone = form.cleaned_data.get('customer_phone')
            if customer_phone:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    customer = User.objects.get(phone=customer_phone)
                except User.DoesNotExist:
                    return {'success': False, 'message': 'Customer not found.'}
        
        if not customer:
            return {'success': False, 'message': 'Please specify a valid customer.'}
        
        # Apply message template if not custom
        if template_type != 'custom':
            template_message = get_template_message(template_type, customer, restaurant, related_object)
            # Extract title and message from template
            lines = template_message.strip().split('\n', 1)
            if len(lines) > 1:
                title = lines[0].strip()
                message = lines[1].strip()
            else:
                message = template_message
        
        # Send Firebase push notification
        push_result = send_custom_push_notification(customer, title, message, restaurant, related_object)
        
        # Log the notification
        log_custom_notification(
            customer=customer,
            restaurant=restaurant,
            notification_type=notification_type,
            subject=title,
            message=message,
            sent_by=request.user,
            related_object=related_object,
            channels=['push notification'] if push_result else []
        )
        
        if push_result:
            return {
                'success': True,
                'message': f'Push notification sent successfully to {customer.first_name} {customer.last_name}.'
            }
        else:
            return {'success': False, 'message': 'Failed to send push notification. Please check if the customer has a valid FCM token.'}
    
    except Exception as e:
        return {'success': False, 'message': f'Error sending notification: {str(e)}'}


def get_template_message(template_type, customer, restaurant, related_object=None):
    """Get predefined message templates"""
    templates = {
        'welcome': f"""
Dear {customer.first_name},

Welcome to {restaurant.name}! We're delighted to have you as our valued customer.

We look forward to providing you with an exceptional dining experience.

Best regards,
{restaurant.name} Team
        """.strip(),
        
        'thank_you': f"""
Dear {customer.first_name},

Thank you for choosing {restaurant.name}! We hope you enjoyed your experience with us.

Your satisfaction is our priority, and we appreciate your business.

We look forward to serving you again soon!

Best regards,
{restaurant.name} Team
        """.strip(),
        
        'special_offer': f"""
Dear {customer.first_name},

We have a special offer just for you at {restaurant.name}!

As one of our valued customers, you're eligible for exclusive deals and promotions.

Visit us soon to take advantage of these limited-time offers.

Best regards,
{restaurant.name} Team
        """.strip(),
        
        'event_invitation': f"""
Dear {customer.first_name},

You're invited to a special event at {restaurant.name}!

Join us for an unforgettable evening with great food, atmosphere, and company.

Please contact us to reserve your spot as space is limited.

Best regards,
{restaurant.name} Team
        """.strip(),
        
        'feedback_request': f"""
Dear {customer.first_name},

We hope you enjoyed your recent visit to {restaurant.name}.

Your feedback is invaluable to us. Please take a moment to share your experience so we can continue to improve our service.

Thank you for helping us serve you better!

Best regards,
{restaurant.name} Team
        """.strip(),
    }
    
    return templates.get(template_type, "Custom message")





def log_custom_notification(customer, restaurant, notification_type, subject, message, sent_by, related_object=None, channels=None):
    """Log custom notification for audit trail"""
    try:
        # Create log entry
        log_data = {
            'customer': customer,
            'restaurant': restaurant,
            'notification_type': notification_type,
            'subject': subject,
            'message': message,
            'sent_by': sent_by,
            'channels': ', '.join(channels) if channels else '',
        }
        
        if related_object:
            if hasattr(related_object, 'reservation_date'):  # It's a reservation
                log_data['reservation'] = related_object
            elif hasattr(related_object, 'order_type'):  # It's an order
                log_data['order'] = related_object
        
        # Create the log entry
        CustomNotificationLog.objects.create(**log_data)
        print(f"Custom notification logged successfully for {customer.first_name} {customer.last_name}")
        
    except Exception as e:
        print(f"Error logging custom notification: {e}")


@login_required
@require_POST
def get_customer_info(request):
    """AJAX endpoint to get customer information"""
    if not is_manager(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        lookup_type = data.get('type')
        lookup_id = data.get('id')
        
        staff_profile = request.user.staff_profile
        restaurant = staff_profile.restaurant
        
        customer_info = None
        
        if lookup_type == 'reservation' and lookup_id:
            try:
                reservation = Reservation.objects.get(id=lookup_id, restaurant=restaurant)
                customer_info = {
                    'name': f"{reservation.customer.first_name} {reservation.customer.last_name}",
                    'phone': reservation.customer.phone,
                    'email': reservation.customer.email or '',
                    'details': f"Reservation for {reservation.party_size} on {reservation.reservation_date} at {reservation.reservation_time}"
                }
            except Reservation.DoesNotExist:
                return JsonResponse({'error': 'Reservation not found'}, status=404)
        
        elif lookup_type == 'order' and lookup_id:
            try:
                order = Order.objects.get(id=lookup_id, restaurant=restaurant)
                customer_info = {
                    'name': f"{order.customer.first_name} {order.customer.last_name}",
                    'phone': order.customer.phone,
                    'email': order.customer.email or '',
                    'details': f"Order #{order.id} - {order.get_order_type_display()} - ${order.total:.2f}"
                }
            except Order.DoesNotExist:
                return JsonResponse({'error': 'Order not found'}, status=404)
        
        elif lookup_type == 'phone' and lookup_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                customer = User.objects.get(phone=lookup_id)
                customer_info = {
                    'name': f"{customer.first_name} {customer.last_name}",
                    'phone': customer.phone,
                    'email': customer.email or '',
                    'details': f"Customer since {customer.date_joined.strftime('%B %Y')}"
                }
            except User.DoesNotExist:
                return JsonResponse({'error': 'Customer not found'}, status=404)
        
        if customer_info:
            return JsonResponse({'success': True, 'customer': customer_info})
        else:
            return JsonResponse({'error': 'Invalid request'}, status=400)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def notification_templates(request):
    """AJAX endpoint to get notification templates"""
    if not is_manager(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        template_type = request.GET.get('template')
        
        # Get manager's restaurant
        staff_profile = request.user.staff_profile
        restaurant = staff_profile.restaurant
        
        # Sample customer for template preview
        sample_customer = type('Customer', (), {
            'first_name': '[Customer Name]',
            'last_name': '[Last Name]'
        })()
        
        template_message = get_template_message(template_type, sample_customer, restaurant)
        
        # Extract title and message from template
        lines = template_message.strip().split('\n', 1)
        if len(lines) > 1:
            title = lines[0].strip()
            message = lines[1].strip()
        else:
            title = f"{restaurant.name} - {template_type.replace('_', ' ').title()}"
            message = template_message
        
        return JsonResponse({
            'success': True,
            'title': title,
            'message': message
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def send_custom_push_notification(customer, title, message, restaurant, related_object=None):
    """Send custom push notification using Firebase"""
    try:
        # Import NotificationService
        from notifications.services import NotificationService
        notification_service = NotificationService()
        
        # Prepare notification data
        data = {
            'restaurant_id': str(restaurant.id),
            'restaurant_name': restaurant.name,
            'notification_type': 'custom',
        }
        
        # Add related object data if available
        if related_object:
            if hasattr(related_object, 'reservation_date'):  # It's a reservation
                data.update({
                    'reservation_id': str(related_object.id),
                    'reservation_date': related_object.reservation_date.isoformat(),
                    'party_size': str(related_object.party_size),
                })
            elif hasattr(related_object, 'order_type'):  # It's an order
                data.update({
                    'order_id': str(related_object.id),
                    'order_type': related_object.order_type,
                    'total_amount': str(related_object.total_amount),
                })
        
        # Send push notification
        result = notification_service.send_notification_to_user(
            user=customer,
            title=title,
            body=message,
            data=data,
            notification_type='custom_notification',
            order=related_object if hasattr(related_object, 'order_type') else None,
            reservation=related_object if hasattr(related_object, 'reservation_date') else None
        )
        
        # Check if notification was sent successfully
        success_count = result.get('success_count', 0)
        return success_count > 0
        
    except Exception as e:
        print(f"Error sending custom push notification: {e}")
        return False