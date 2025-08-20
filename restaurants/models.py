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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    special_requests = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
