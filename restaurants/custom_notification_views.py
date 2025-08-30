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
from django.core.mail import send_mail
from django.template.loader import render_to_string
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
    
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email subject'})
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Enter your custom message here...'
        })
    )
    
    send_email = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    send_sms = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
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
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']
        send_email = form.cleaned_data['send_email']
        send_sms = form.cleaned_data['send_sms']
        
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
            message = get_template_message(template_type, customer, restaurant, related_object)
        
        # Send notifications
        notifications_sent = []
        
        if send_email:
            email_result = send_custom_email(customer, subject, message, restaurant, related_object)
            if email_result:
                notifications_sent.append('email')
        
        if send_sms:
            sms_result = send_custom_sms(customer, message, restaurant)
            if sms_result:
                notifications_sent.append('SMS')
        
        # Log the notification
        log_custom_notification(
            customer=customer,
            restaurant=restaurant,
            notification_type=notification_type,
            subject=subject,
            message=message,
            sent_by=request.user,
            related_object=related_object,
            channels=notifications_sent
        )
        
        if notifications_sent:
            channels_str = ' and '.join(notifications_sent)
            return {
                'success': True,
                'message': f'Custom notification sent successfully via {channels_str} to {customer.first_name} {customer.last_name}.'
            }
        else:
            return {'success': False, 'message': 'Failed to send notification. Please check your settings.'}
    
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


def send_custom_email(customer, subject, message, restaurant, related_object=None):
    """Send custom email notification"""
    try:
        # Create HTML email content
        html_content = render_to_string('emails/custom_notification.html', {
            'customer': customer,
            'restaurant': restaurant,
            'subject': subject,
            'message': message,
            'related_object': related_object,
        })
        
        # Send email
        send_mail(
            subject=subject,
            message=message,  # Plain text version
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email] if customer.email else [],
            html_message=html_content,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending custom email: {e}")
        return False


def send_custom_sms(customer, message, restaurant):
    """Send custom SMS notification"""
    try:
        # Import Twilio client if available
        from twilio.rest import Client
        
        # Get Twilio settings
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        from_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        
        if not all([account_sid, auth_token, from_phone]):
            print("Twilio settings not configured")
            return False
        
        client = Client(account_sid, auth_token)
        
        # Send SMS
        message_obj = client.messages.create(
            body=f"{restaurant.name}: {message}",
            from_=from_phone,
            to=customer.phone
        )
        
        return True
    except Exception as e:
        print(f"Error sending custom SMS: {e}")
        return False


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
        
        return JsonResponse({
            'success': True,
            'message': template_message,
            'subject': f"{restaurant.name} - {template_type.replace('_', ' ').title()}"
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)