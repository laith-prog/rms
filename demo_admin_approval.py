#!/usr/bin/env python
"""
Demo script to show the admin approval system functionality
Run this script to create sample data and demonstrate the approval workflow
"""
import os
import sys
import django
from datetime import datetime, timedelta, date, time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rms.settings')
django.setup()

from django.contrib.auth import get_user_model
from restaurants.models import Restaurant, Table, Reservation
from orders.models import Order, OrderItem, MenuItem
from accounts.models import StaffProfile

User = get_user_model()

def create_demo_data():
    """Create demo data for testing the approval system"""
    print("🏗️  Creating demo data...")
    
    # Create a customer
    customer, created = User.objects.get_or_create(
        phone='+1234567890',
        defaults={
            'password': 'pbkdf2_sha256$600000$test$test',  # Dummy hash
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'is_customer': True
        }
    )
    if created:
        print(f"✅ Created customer: {customer.first_name} {customer.last_name}")
    
    # Create a restaurant
    restaurant, created = Restaurant.objects.get_or_create(
        name='Demo Restaurant',
        defaults={
            'address': '123 Demo Street, Demo City',
            'phone': '+1987654321',
            'email': 'info@demorestaurant.com',
            'description': 'A demo restaurant for testing the approval system',
            'opening_time': time(9, 0),
            'closing_time': time(22, 0)
        }
    )
    if created:
        print(f"✅ Created restaurant: {restaurant.name}")
    
    # Create a manager
    manager_user, created = User.objects.get_or_create(
        phone='+1111111111',
        defaults={
            'password': 'pbkdf2_sha256$600000$manager123$test',  # You should set a real password
            'first_name': 'Manager',
            'last_name': 'Smith',
            'email': 'manager@demorestaurant.com',
            'is_staff_member': True,
            'is_staff': True
        }
    )
    if created:
        print(f"✅ Created manager user: {manager_user.first_name} {manager_user.last_name}")
        # Set a proper password
        manager_user.set_password('manager123')
        manager_user.save()
    
    # Create manager profile
    manager_profile, created = StaffProfile.objects.get_or_create(
        user=manager_user,
        defaults={
            'role': 'manager',
            'restaurant': restaurant
        }
    )
    if created:
        print(f"✅ Created manager profile for {restaurant.name}")
    
    # Create tables
    table1, created = Table.objects.get_or_create(
        restaurant=restaurant,
        table_number='T1',
        defaults={'capacity': 4}
    )
    if created:
        print(f"✅ Created table: {table1.table_number}")
    
    table2, created = Table.objects.get_or_create(
        restaurant=restaurant,
        table_number='T2',
        defaults={'capacity': 2}
    )
    if created:
        print(f"✅ Created table: {table2.table_number}")
    
    # Create menu items
    menu_item1, created = MenuItem.objects.get_or_create(
        restaurant=restaurant,
        name='Demo Burger',
        defaults={
            'description': 'A delicious demo burger',
            'price': 15.99,
            'is_active': True
        }
    )
    if created:
        print(f"✅ Created menu item: {menu_item1.name}")
    
    menu_item2, created = MenuItem.objects.get_or_create(
        restaurant=restaurant,
        name='Demo Pizza',
        defaults={
            'description': 'A tasty demo pizza',
            'price': 18.99,
            'is_active': True
        }
    )
    if created:
        print(f"✅ Created menu item: {menu_item2.name}")
    
    # Create pending reservations
    reservation1, created = Reservation.objects.get_or_create(
        customer=customer,
        restaurant=restaurant,
        table=table1,
        reservation_date=(datetime.now() + timedelta(days=1)).date(),
        reservation_time=time(18, 0),
        defaults={
            'party_size': 2,
            'status': 'pending',
            'special_requests': 'Window seat preferred'
        }
    )
    if created:
        print(f"✅ Created pending reservation: #{reservation1.id}")
    
    reservation2, created = Reservation.objects.get_or_create(
        customer=customer,
        restaurant=restaurant,
        table=table2,
        reservation_date=(datetime.now() + timedelta(days=2)).date(),
        reservation_time=time(19, 30),
        defaults={
            'party_size': 4,
            'status': 'pending',
            'special_requests': 'Birthday celebration'
        }
    )
    if created:
        print(f"✅ Created pending reservation: #{reservation2.id}")
    
    # Create pending orders
    order1, created = Order.objects.get_or_create(
        customer=customer,
        restaurant=restaurant,
        defaults={
            'order_type': 'dine_in',
            'status': 'pending',
            'subtotal': 15.99,
            'tax': 1.60,
            'total': 17.59,
            'special_instructions': 'No onions please'
        }
    )
    if created:
        print(f"✅ Created pending order: #{order1.id}")
        # Add order items
        OrderItem.objects.create(
            order=order1,
            menu_item=menu_item1,
            quantity=1,
            item_price=15.99
        )
    
    order2, created = Order.objects.get_or_create(
        customer=customer,
        restaurant=restaurant,
        defaults={
            'order_type': 'pickup',
            'status': 'pending',
            'subtotal': 18.99,
            'tax': 1.90,
            'total': 20.89,
            'special_instructions': 'Extra cheese'
        }
    )
    if created:
        print(f"✅ Created pending order: #{order2.id}")
        # Add order items
        OrderItem.objects.create(
            order=order2,
            menu_item=menu_item2,
            quantity=1,
            item_price=18.99
        )
    
    return {
        'customer': customer,
        'restaurant': restaurant,
        'manager_user': manager_user,
        'reservations': [reservation1, reservation2],
        'orders': [order1, order2]
    }

def show_admin_urls():
    """Show the admin URLs for accessing the approval system"""
    print("\n🌐 Admin Panel URLs:")
    print("=" * 50)
    print("🔧 Manager Admin Panel:")
    print("   URL: http://localhost:8000/manager/")
    print("   Login: +1111111111 / manager123")
    print("   Features:")
    print("   - Dashboard with pending counts")
    print("   - Reservation approval/rejection")
    print("   - Order approval and workflow management")
    print("   - Email notifications to customers")
    print()
    print("🔧 Super Admin Panel:")
    print("   URL: http://localhost:8000/superadmin/")
    print("   Login: Create superuser with 'python manage.py createsuperuser'")
    print("   Features:")
    print("   - System-wide access")
    print("   - All restaurants and data")
    print()
    print("📊 Direct Links (after logging in as manager):")
    print("   - Pending Reservations: http://localhost:8000/manager/restaurants/reservation/?status__exact=pending")
    print("   - Pending Orders: http://localhost:8000/manager/orders/order/?status__exact=pending")
    print("   - All Reservations: http://localhost:8000/manager/restaurants/reservation/")
    print("   - All Orders: http://localhost:8000/manager/orders/order/")

def show_workflow_examples():
    """Show examples of the approval workflows"""
    print("\n🔄 Approval Workflows:")
    print("=" * 50)
    print("📅 Reservation Workflow:")
    print("   1. Customer creates reservation → Status: PENDING")
    print("   2. Manager reviews in admin panel")
    print("   3. Manager clicks 'Approve' → Status: CONFIRMED")
    print("   4. Customer receives confirmation email")
    print("   5. After dining → Manager marks as COMPLETED")
    print()
    print("🍽️ Order Workflow:")
    print("   1. Customer places order → Status: PENDING")
    print("   2. Manager reviews and approves → Status: APPROVED")
    print("   3. Chef starts preparation → Status: PREPARING")
    print("   4. Order ready → Status: READY")
    print("   5. Customer receives/picks up → Status: COMPLETED")
    print()
    print("📧 Email Notifications:")
    print("   - Customers receive emails for all status changes")
    print("   - Professional HTML templates with restaurant branding")
    print("   - Different messages for each status (approved, rejected, etc.)")

def show_features():
    """Show the key features of the approval system"""
    print("\n✨ Key Features:")
    print("=" * 50)
    print("🎯 Enhanced Admin Interface:")
    print("   ✅ Visual status badges with color coding")
    print("   ✅ Customer information display")
    print("   ✅ Quick action buttons (one-click approve/reject)")
    print("   ✅ Bulk actions for multiple items")
    print("   ✅ Enhanced search and filtering")
    print()
    print("📊 Manager Dashboard:")
    print("   ✅ Real-time statistics (pending counts)")
    print("   ✅ Quick access links to pending items")
    print("   ✅ Recent activity overview")
    print("   ✅ Visual indicators and metrics")
    print()
    print("🔔 Notification System:")
    print("   ✅ Automatic email notifications")
    print("   ✅ Professional HTML templates")
    print("   ✅ Status-specific messages")
    print("   ✅ Restaurant branding integration")
    print()
    print("🔒 Security & Permissions:")
    print("   ✅ Role-based access control")
    print("   ✅ Managers only see their restaurant's data")
    print("   ✅ Secure status transitions")
    print("   ✅ Audit trail for all changes")

def main():
    """Main demo function"""
    print("🎉 Restaurant Management System - Admin Approval Demo")
    print("=" * 60)
    
    try:
        # Create demo data
        data = create_demo_data()
        
        print(f"\n📊 Demo Data Summary:")
        print(f"   Restaurant: {data['restaurant'].name}")
        print(f"   Manager: {data['manager_user'].first_name} {data['manager_user'].last_name}")
        print(f"   Customer: {data['customer'].first_name} {data['customer'].last_name}")
        print(f"   Pending Reservations: {len(data['reservations'])}")
        print(f"   Pending Orders: {len(data['orders'])}")
        
        # Show admin URLs
        show_admin_urls()
        
        # Show workflow examples
        show_workflow_examples()
        
        # Show features
        show_features()
        
        print("\n🚀 Next Steps:")
        print("=" * 50)
        print("1. Start the development server:")
        print("   python manage.py runserver")
        print()
        print("2. Access the manager admin panel:")
        print("   http://localhost:8000/manager/")
        print("   Login: +1111111111 / manager123")
        print()
        print("3. Try the approval workflow:")
        print("   - View pending reservations and orders")
        print("   - Click approve/reject buttons")
        print("   - Check email notifications (if configured)")
        print("   - Use bulk actions for multiple items")
        print()
        print("4. Explore the dashboard:")
        print("   - View real-time statistics")
        print("   - Use quick action links")
        print("   - Check recent activity")
        
        print("\n✅ Demo setup complete! The admin approval system is ready to use.")
        
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()