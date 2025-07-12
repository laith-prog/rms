from django.contrib import admin
from .models import Order, OrderItem, OrderStatusUpdate


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


class OrderStatusUpdateInline(admin.TabularInline):
    model = OrderStatusUpdate
    extra = 1
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'restaurant', 'order_type', 'status', 'total', 'created_at')
    list_filter = ('status', 'order_type', 'payment_status', 'created_at', 'restaurant')
    search_fields = ('customer__phone', 'restaurant__name', 'special_instructions')
    readonly_fields = ('subtotal', 'tax', 'total')
    inlines = [OrderItemInline, OrderStatusUpdateInline]
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('customer', 'restaurant', 'reservation', 'order_type', 'status')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax', 'delivery_fee', 'total', 'payment_status', 'payment_method')
        }),
        ('Order Details', {
            'fields': ('special_instructions', 'delivery_address', 'estimated_preparation_time')
        }),
        ('Staff Assignment', {
            'fields': ('assigned_chef', 'assigned_waiter')
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'menu_item', 'quantity', 'item_price', 'item_total')
    search_fields = ('order__id', 'menu_item__name', 'special_instructions')
    list_filter = ('order__status',)
    
    def item_total(self, obj):
        return obj.item_price * obj.quantity
    
    item_total.short_description = 'Total'


@admin.register(OrderStatusUpdate)
class OrderStatusUpdateAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'updated_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__id', 'notes')
    readonly_fields = ('created_at',)
