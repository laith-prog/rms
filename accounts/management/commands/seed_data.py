from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import CustomerProfile, StaffProfile, TokenVersion
from restaurants.models import Restaurant, Category, MenuItem, Table
from orders.models import Order, OrderItem
import random
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with initial data for testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting database seeding...'))
        
        # Create superuser if it doesn't exist
        if not User.objects.filter(phone='0953241659').exists():
            self.stdout.write('Creating superuser...')
            superuser = User.objects.create_superuser(
                phone='0953241659',
                password='admin123',
                first_name='Admin',
                last_name='User',
                is_phone_verified=True
            )
            TokenVersion.objects.get_or_create(user=superuser)
            self.stdout.write(self.style.SUCCESS('Superuser created successfully'))
        
        # Create customers
        self.stdout.write('Creating customers...')
        customers = []
        for i in range(1, 11):
            phone = f'09{random.randint(10000000, 99999999)}'
            if not User.objects.filter(phone=phone).exists():
                user = User.objects.create_user(
                    phone=phone,
                    password='password123',
                    first_name=f'Customer{i}',
                    last_name=f'User{i}',
                    is_customer=True,
                    is_phone_verified=True
                )
                TokenVersion.objects.get_or_create(user=user)
                profile = CustomerProfile.objects.create(
                    user=user,
                    allergies=random.choice(['None', 'Peanuts', 'Gluten', 'Dairy', '']),
                    dietary_preferences=random.choice(['None', 'Vegetarian', 'Vegan', 'Keto', '']),
                    default_address=f'Address {i}, City'
                )
                customers.append(user)
        self.stdout.write(self.style.SUCCESS(f'Created {len(customers)} customers'))
        
        # Create food categories
        self.stdout.write('Creating food categories...')
        categories = []
        category_names = ['Italian', 'Chinese', 'Japanese', 'American', 'Indian', 'Lebanese', 
                          'Fast Food', 'Desserts', 'Beverages', 'Vegetarian']
        
        for cat_name in category_names:
            category = Category.objects.get_or_create(
                name=cat_name,
                defaults={
                    'description': f'Delicious {cat_name} food',
                    'is_active': True
                }
            )[0]
            categories.append(category)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(categories)} food categories'))
        
        # Create restaurants
        self.stdout.write('Creating restaurants...')
        restaurants = []
        restaurant_names = [
            'Tasty Bites', 'Spice Garden', 'Ocean Delights', 
            'Green Plate', 'Urban Kitchen', 'Flavor Fusion',
            'Golden Dragon', 'Bella Italia', 'Sushi Express',
            'Burger Haven'
        ]
        
        for i, name in enumerate(restaurant_names):
            restaurant = Restaurant.objects.get_or_create(
                name=name,
                defaults={
                    'address': f'{name} Street, City',
                    'phone': f'09{random.randint(10000000, 99999999)}',
                    'description': f'A wonderful {name} restaurant with delicious food.',
                    'opening_time': '09:00',
                    'closing_time': '22:00',
                    'is_active': True,
                    'offers_dine_in': True,
                    'offers_takeaway': True,
                    'offers_delivery': random.choice([True, False])
                }
            )[0]
            
            # Add 2-3 random categories to the restaurant
            selected_categories = random.sample(categories, random.randint(2, 3))
            for category in selected_categories:
                restaurant.categories.add(category)
            
            restaurants.append(restaurant)
            
            # Create manager for restaurant
            manager_phone = f'08{random.randint(10000000, 99999999)}'
            if not User.objects.filter(phone=manager_phone).exists():
                manager = User.objects.create_user(
                    phone=manager_phone,
                    password='manager123',
                    first_name=f'Manager{i}',
                    last_name=f'User{i}',
                    is_staff_member=True,
                    is_staff=True,
                    is_phone_verified=True
                )
                TokenVersion.objects.get_or_create(user=manager)
                StaffProfile.objects.create(
                    user=manager,
                    role='manager',
                    restaurant=restaurant
                )
            
            # Create staff members for restaurant
            for role in ['waiter', 'chef']:
                for j in range(2):  # 2 waiters, 2 chefs per restaurant
                    staff_phone = f'07{random.randint(10000000, 99999999)}'
                    if not User.objects.filter(phone=staff_phone).exists():
                        staff = User.objects.create_user(
                            phone=staff_phone,
                            password='staff123',
                            first_name=f'{role.capitalize()}{j}',
                            last_name=f'Restaurant{i}',
                            is_staff_member=True,
                            is_phone_verified=True
                        )
                        TokenVersion.objects.get_or_create(user=staff)
                        StaffProfile.objects.create(
                            user=staff,
                            role=role,
                            restaurant=restaurant,
                            is_on_shift=random.choice([True, False])
                        )
            
            # Create menu categories for restaurant
            menu_categories = []
            menu_category_names = ['Appetizers', 'Main Course', 'Desserts', 'Drinks']
            for cat_name in menu_category_names:
                menu_category = Category.objects.get_or_create(
                    name=f"{cat_name} - {restaurant.name}",
                    defaults={
                        'description': f'{cat_name} for {restaurant.name}',
                        'is_active': True
                    }
                )[0]
                restaurant.categories.add(menu_category)
                menu_categories.append(menu_category)
            
            # Create menu items for each category
            for menu_category in menu_categories:
                for j in range(5):  # 5 items per category
                    MenuItem.objects.get_or_create(
                        name=f'{menu_category.name.split(" - ")[0][:-1]} {j+1}',
                        restaurant=restaurant,
                        defaults={
                            'description': f'Delicious {menu_category.name.split(" - ")[0].lower()} item',
                            'price': random.randint(5, 50) + 0.99,
                            'food_category': menu_category,
                            'is_vegetarian': random.choice([True, False]),
                            'is_vegan': random.choice([True, False]),
                            'is_gluten_free': random.choice([True, False]),
                            'contains_nuts': random.choice([True, False]),
                            'contains_dairy': random.choice([True, False]),
                            'is_spicy': random.choice([True, False]),
                            'is_active': True,
                            'preparation_time': random.randint(5, 30)
                        }
                    )
            
            # Create tables for restaurant
            for j in range(10):  # 10 tables per restaurant
                Table.objects.get_or_create(
                    restaurant=restaurant,
                    table_number=str(j+1),
                    defaults={
                        'capacity': random.randint(2, 8),
                        'is_active': True,
                        'is_reserved': random.choice([True, False])
                    }
                )
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(restaurants)} restaurants with staff, categories, menu items, and tables'))
        
        # Create orders
        self.stdout.write('Creating orders...')
        order_types = ['dine_in', 'pickup', 'delivery']
        order_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'delivered', 'completed', 'cancelled']
        
        for i in range(20):  # 20 orders
            if not customers:
                break
                
            customer = random.choice(customers)
            restaurant = random.choice(restaurants)
            order_type = random.choice(order_types)
            
            # Get menu items from the restaurant
            menu_items = MenuItem.objects.filter(restaurant=restaurant)
            if not menu_items:
                continue
                
            # Create order
            subtotal = random.randint(20, 100) + 0.99
            tax = subtotal * 0.1  # 10% tax
            delivery_fee = 5.00 if order_type == 'delivery' else 0.00
            total = subtotal + tax + delivery_fee
            
            order = Order.objects.create(
                customer=customer,
                restaurant=restaurant,
                order_type=order_type,
                status=random.choice(order_statuses),
                delivery_address=customer.customer_profile.default_address if order_type == 'delivery' else None,
                created_at=timezone.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23)),
                special_instructions=random.choice(['No spicy', 'Extra sauce', 'No onions', '']),
                subtotal=subtotal,
                tax=tax,
                delivery_fee=delivery_fee,
                total=total,
                payment_status=random.choice(['pending', 'paid']),
                payment_method=random.choice(['cash', 'credit_card', 'digital_wallet'])
            )
            
            # Create order items
            total_amount = 0
            for j in range(random.randint(1, 5)):  # 1-5 items per order
                item = random.choice(menu_items)
                quantity = random.randint(1, 3)
                price = item.price
                OrderItem.objects.create(
                    order=order,
                    menu_item=item,
                    quantity=quantity,
                    item_price=price
                )
                total_amount += price * quantity
            
            # Update order total
            order.total_amount = total_amount
            order.save()
        
        self.stdout.write(self.style.SUCCESS('Orders created successfully'))
        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!')) 