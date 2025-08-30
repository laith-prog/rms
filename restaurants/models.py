from django.db import models
from django.conf import settings


class Category(models.Model):
    """
    Food categories such as Italian, Fast Food, Vegan, etc.
    """
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Restaurant(models.Model):
    """
    Restaurant information
    """
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    logo = models.ImageField(upload_to='restaurants/logos/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='restaurants/covers/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    categories = models.ManyToManyField(Category, related_name='restaurants')
    is_active = models.BooleanField(default=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Services offered
    offers_dine_in = models.BooleanField(default=True)
    offers_takeaway = models.BooleanField(default=True)
    offers_delivery = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name


class RestaurantImage(models.Model):
    """
    Additional images for restaurants
    """
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='restaurants/images/')
    caption = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.restaurant.name} - Image {self.id}"


class MenuItem(models.Model):
    """
    Menu items for restaurants
    """
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    food_category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='food_items')
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    contains_nuts = models.BooleanField(default=False)
    contains_dairy = models.BooleanField(default=False)
    is_spicy = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    preparation_time = models.IntegerField(help_text="Preparation time in minutes", default=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"


class Table(models.Model):
    """
    Tables in restaurants for reservations
    """
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
    table_number = models.CharField(max_length=10)
    capacity = models.IntegerField()
    is_active = models.BooleanField(default=True)
    is_reserved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.restaurant.name} - Table {self.table_number}"


class Reservation(models.Model):
    """
    Table reservations
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )
    
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reservations')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reservations')
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='reservations')
    party_size = models.IntegerField()
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    duration_hours = models.IntegerField(default=1, help_text="Duration of reservation in hours")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    special_requests = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def end_time(self):
        """Calculate the end time of the reservation"""
        from datetime import datetime, timedelta
        start_datetime = datetime.combine(self.reservation_date, self.reservation_time)
        end_datetime = start_datetime + timedelta(hours=self.duration_hours)
        return end_datetime.time()
    
    def __str__(self):
        return f"{self.customer} - {self.restaurant.name} - {self.reservation_date} {self.reservation_time}"


class ReservationStatusUpdate(models.Model):
    """
    Tracks updates to reservation status for notifications
    """
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='status_updates')
    status = models.CharField(max_length=20, choices=Reservation.STATUS_CHOICES)
    notes = models.TextField(blank=True, null=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='reservation_status_updates')
    created_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.reservation} - {self.status} - {self.created_at}"


class CustomNotificationLog(models.Model):
    """Log of custom notifications sent to customers"""
    NOTIFICATION_TYPES = [
        ('reservation', 'Reservation'),
        ('order', 'Order'),
        ('general', 'General Message'),
    ]
    
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_notifications')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    
    # Optional related objects
    reservation = models.ForeignKey(Reservation, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Delivery channels
    channels = models.CharField(max_length=100, help_text="Comma-separated list of channels (email, SMS)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Custom Notification Log'
        verbose_name_plural = 'Custom Notification Logs'
    
    def __str__(self):
        return f"Notification to {self.customer.first_name} {self.customer.last_name} - {self.subject}"
    
    def get_channels_list(self):
        """Return list of delivery channels"""
        return [channel.strip() for channel in self.channels.split(',') if channel.strip()]


class Review(models.Model):
    """
    Restaurant reviews
    """
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 stars
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.customer} - {self.restaurant.name} - {self.rating} stars"
