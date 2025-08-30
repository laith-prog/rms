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
    list_display = ('order_id', 'customer_info', 'restaurant', 'order_type_badge', 'status_badge', 'total_amount', 'created_at', 'action_buttons')
    list_filter = ('status', 'order_type', 'payment_status', 'created_at', 'restaurant')
    search_fields = ('customer__phone', 'customer__first_name', 'customer__last_name', 'restaurant__name', 'special_instructions')
    readonly_fields = ('subtotal', 'tax', 'total', 'created_at', 'updated_at')
    inlines = [OrderItemInline, OrderStatusUpdateInline]
    date_hierarchy = 'created_at'
    actions = ['approve_orders', 'reject_orders', 'mark_as_preparing', 'mark_as_ready', 'mark_as_completed']
    
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
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def order_id(self, obj):
        """Display order ID with formatting"""
        return f"#{obj.id}"
    order_id.short_description = 'Order ID'
    
    def customer_info(self, obj):
        """Display customer information with phone"""
        from django.utils.html import format_html
        name = f"{obj.customer.first_name} {obj.customer.last_name}".strip()
        if not name:
            name = "Customer"
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            name,
            obj.customer.phone
        )
    customer_info.short_description = 'Customer'
    
    def order_type_badge(self, obj):
        """Display order type with color coding"""
        from django.utils.html import format_html
        colors = {
            'dine_in': '#17a2b8',  # Blue
            'pickup': '#ffc107',   # Yellow
            'delivery': '#28a745', # Green
        }
        color = colors.get(obj.order_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold;">{}</span>',
            color,
            obj.get_order_type_display().upper()
        )
    order_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        """Display status with color coding"""
        from django.utils.html import format_html
        colors = {
            'pending': '#ffc107',    # Yellow
            'approved': '#28a745',   # Green
            'rejected': '#dc3545',   # Red
            'preparing': '#fd7e14',  # Orange
            'ready': '#20c997',      # Teal
            'completed': '#6c757d',  # Gray
            'cancelled': '#dc3545',  # Red
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    
    def total_amount(self, obj):
        """Display total with currency formatting"""
        return f"${obj.total:.2f}"
    total_amount.short_description = 'Total'
    
    def action_buttons(self, obj):
        """Display quick action buttons"""
        from django.utils.html import format_html
        from django.urls import reverse
        
        if obj.status == 'pending':
            return format_html(
                '<a class="button" href="{}?action=approve" style="background-color: #28a745; color: white; margin-right: 5px; font-size: 11px; padding: 2px 6px;">Approve</a>'
                '<a class="button" href="{}?action=reject" style="background-color: #dc3545; color: white; font-size: 11px; padding: 2px 6px;">Reject</a>',
                reverse('admin:orders_order_change', args=[obj.pk]),
                reverse('admin:orders_order_change', args=[obj.pk])
            )
        elif obj.status == 'approved':
            return format_html(
                '<a class="button" href="{}?action=preparing" style="background-color: #fd7e14; color: white; font-size: 11px; padding: 2px 6px;">Start Preparing</a>',
                reverse('admin:orders_order_change', args=[obj.pk])
            )
        elif obj.status == 'preparing':
            return format_html(
                '<a class="button" href="{}?action=ready" style="background-color: #20c997; color: white; font-size: 11px; padding: 2px 6px;">Mark Ready</a>',
                reverse('admin:orders_order_change', args=[obj.pk])
            )
        elif obj.status == 'ready':
            return format_html(
                '<a class="button" href="{}?action=complete" style="background-color: #6c757d; color: white; font-size: 11px; padding: 2px 6px;">Complete</a>',
                reverse('admin:orders_order_change', args=[obj.pk])
            )
        return '-'
    action_buttons.short_description = 'Quick Actions'
    action_buttons.allow_tags = True
    
    def approve_orders(self, request, queryset):
        """Bulk approve orders"""
        updated = 0
        for order in queryset.filter(status='pending'):
            order.status = 'approved'
            order.save()
            
            # Create status update record
            OrderStatusUpdate.objects.create(
                order=order,
                status='approved',
                notes='Approved by admin',
                updated_by=request.user
            )
            updated += 1
        
        self.message_user(request, f'{updated} orders approved successfully.')
    approve_orders.short_description = "Approve selected orders"
    
    def reject_orders(self, request, queryset):
        """Bulk reject orders"""
        updated = 0
        for order in queryset.filter(status='pending'):
            order.status = 'rejected'
            order.save()
            
            # Create status update record
            OrderStatusUpdate.objects.create(
                order=order,
                status='rejected',
                notes='Rejected by admin',
                updated_by=request.user
            )
            updated += 1
        
        self.message_user(request, f'{updated} orders rejected successfully.')
    reject_orders.short_description = "Reject selected orders"
    
    def mark_as_preparing(self, request, queryset):
        """Mark orders as preparing"""
        updated = 0
        for order in queryset.filter(status='approved'):
            order.status = 'preparing'
            order.save()
            
            # Create status update record
            OrderStatusUpdate.objects.create(
                order=order,
                status='preparing',
                notes='Started preparation',
                updated_by=request.user
            )
            updated += 1
        
        self.message_user(request, f'{updated} orders marked as preparing.')
    mark_as_preparing.short_description = "Mark selected orders as preparing"
    
    def mark_as_ready(self, request, queryset):
        """Mark orders as ready"""
        updated = 0
        for order in queryset.filter(status='preparing'):
            order.status = 'ready'
            order.save()
            
            # Create status update record
            OrderStatusUpdate.objects.create(
                order=order,
                status='ready',
                notes='Order ready for pickup/delivery',
                updated_by=request.user
            )
            updated += 1
        
        self.message_user(request, f'{updated} orders marked as ready.')
    mark_as_ready.short_description = "Mark selected orders as ready"
    
    def mark_as_completed(self, request, queryset):
        """Mark orders as completed"""
        updated = 0
        for order in queryset.filter(status='ready'):
            order.status = 'completed'
            order.save()
            
            # Create status update record
            OrderStatusUpdate.objects.create(
                order=order,
                status='completed',
                notes='Order completed',
                updated_by=request.user
            )
            updated += 1
        
        self.message_user(request, f'{updated} orders marked as completed.')
    mark_as_completed.short_description = "Mark selected orders as completed"
    
    def response_change(self, request, obj):
        """Handle quick actions from URL parameters"""
        from django.contrib import messages
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        action = request.GET.get('action')
        if action:
            if action == 'approve' and obj.status == 'pending':
                obj.status = 'approved'
                obj.save()
                OrderStatusUpdate.objects.create(
                    order=obj,
                    status='approved',
                    notes='Approved by admin',
                    updated_by=request.user
                )
                messages.success(request, f'Order #{obj.id} approved successfully.')
                return HttpResponseRedirect(reverse('admin:orders_order_changelist'))
            elif action == 'reject' and obj.status == 'pending':
                obj.status = 'rejected'
                obj.save()
                OrderStatusUpdate.objects.create(
                    order=obj,
                    status='rejected',
                    notes='Rejected by admin',
                    updated_by=request.user
                )
                messages.success(request, f'Order #{obj.id} rejected successfully.')
                return HttpResponseRedirect(reverse('admin:orders_order_changelist'))
            elif action == 'preparing' and obj.status == 'approved':
                obj.status = 'preparing'
                obj.save()
                OrderStatusUpdate.objects.create(
                    order=obj,
                    status='preparing',
                    notes='Started preparation',
                    updated_by=request.user
                )
                messages.success(request, f'Order #{obj.id} marked as preparing.')
                return HttpResponseRedirect(reverse('admin:orders_order_changelist'))
            elif action == 'ready' and obj.status == 'preparing':
                obj.status = 'ready'
                obj.save()
                OrderStatusUpdate.objects.create(
                    order=obj,
                    status='ready',
                    notes='Order ready for pickup/delivery',
                    updated_by=request.user
                )
                messages.success(request, f'Order #{obj.id} marked as ready.')
                return HttpResponseRedirect(reverse('admin:orders_order_changelist'))
            elif action == 'complete' and obj.status == 'ready':
                obj.status = 'completed'
                obj.save()
                OrderStatusUpdate.objects.create(
                    order=obj,
                    status='completed',
                    notes='Order completed',
                    updated_by=request.user
                )
                messages.success(request, f'Order #{obj.id} completed successfully.')
                return HttpResponseRedirect(reverse('admin:orders_order_changelist'))
        
        return super().response_change(request, obj)


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
