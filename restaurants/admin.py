from django.contrib import admin
from .models import Category, Restaurant, RestaurantImage, MenuItem, Table, Reservation, Review


class RestaurantImageInline(admin.TabularInline):
    model = RestaurantImage
    extra = 3


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1


class TableInline(admin.TabularInline):
    model = Table
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'average_rating', 'is_active', 'offers_dine_in', 'offers_takeaway', 'offers_delivery')
    list_filter = ('is_active', 'offers_dine_in', 'offers_takeaway', 'offers_delivery', 'categories')
    search_fields = ('name', 'address', 'phone', 'email')
    filter_horizontal = ('categories',)
    inlines = [RestaurantImageInline, MenuItemInline, TableInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'price', 'is_active', 'is_vegetarian', 'is_vegan')
    list_filter = ('is_active', 'is_vegetarian', 'is_vegan', 'is_gluten_free', 'contains_nuts', 'contains_dairy', 'is_spicy')
    search_fields = ('name', 'description')


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'table_number', 'capacity', 'is_active', 'is_reserved')
    list_filter = ('is_active', 'is_reserved', 'restaurant')
    search_fields = ('table_number',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('customer', 'restaurant', 'table', 'party_size', 'reservation_date', 'reservation_time', 'status')
    list_filter = ('status', 'reservation_date', 'restaurant')
    search_fields = ('customer__phone', 'restaurant__name', 'special_requests')
    date_hierarchy = 'reservation_date'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('customer', 'restaurant', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('customer__phone', 'restaurant__name', 'comment')
