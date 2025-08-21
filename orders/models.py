from django.db import models
from django.conf import settings
from restaurants.models import Restaurant, MenuItem


class Order(models.Model):
    """
    Order model for customer orders
    """
    ORDER_TYPE_CHOICES = (
        ('dine_in', 'Dine In'),
        ('pickup', 'Pickup'),
        ('delivery', 'Delivery'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('digital_wallet', 'Digital Wallet'),
    )
    
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders')
    
    # Can be linked to a reservation for pre-orders with table booking
    reservation = models.ForeignKey('restaurants.Reservation', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Order details
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    special_instructions = models.TextField(blank=True, null=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    estimated_preparation_time = models.IntegerField(null=True, blank=True, help_text="Estimated preparation time in minutes")
    
    # Payment info
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHOD_CHOICES, default='cash')
    
    # For delivery orders
    delivery_address = models.TextField(blank=True, null=True)
    
    # For tracking and chef/waiter assignment
    assigned_chef = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='chef_orders'
    )
    assigned_waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='waiter_orders'
    )
    
    def __str__(self):
        return f"Order #{self.id} - {self.customer} - {self.restaurant.name}"
    
    def calculate_total(self):
        """Calculate the total cost of the order"""
        from decimal import Decimal
        
        self.subtotal = sum(item.item_total for item in self.items.all())
        self.tax = self.subtotal * Decimal('0.1')  # Assuming 10% tax
        self.total = self.subtotal + self.tax + self.delivery_fee
        return self.total
    
    def calculate_preparation_time(self):
        """Calculate the estimated preparation time based on order items"""
        if self.items.exists():
            prep_times = []
            for item in self.items.all():
                # Ensure both values are integers to avoid type conflicts
                prep_time = int(item.menu_item.preparation_time or 0)
                quantity = int(item.quantity or 1)
                prep_times.append(prep_time * quantity)
            
            # The preparation time is the maximum of all items, not the sum
            self.estimated_preparation_time = max(prep_times) if prep_times else 0
            return self.estimated_preparation_time
        return 0


class OrderItem(models.Model):
    """
    Items within an order
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    item_price = models.DecimalField(max_digits=10, decimal_places=2)
    special_instructions = models.TextField(blank=True, null=True)
    
    @property
    def item_total(self):
        from decimal import Decimal
        return self.item_price * Decimal(str(self.quantity))
    
    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} - Order #{self.order.id}"


class OrderStatusUpdate(models.Model):
    """
    Tracks updates to order status
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_updates')
    status = models.CharField(max_length=10, choices=Order.STATUS_CHOICES)
    notes = models.TextField(blank=True, null=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='order_status_updates')
    created_at = models.DateTimeField(auto_now_add=True)
    notification_message = models.TextField(blank=True, null=True)
    is_notified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.order} - {self.status} - {self.created_at}"
