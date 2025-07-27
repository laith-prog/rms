# Database Seeder

This Django management command populates the database with test data for development and testing purposes.

## What it creates:

1. **Superuser** - Admin account with phone: 0953241659, password: admin123
2. **Customers** - 10 customer accounts with profiles
3. **Restaurants** - 10 restaurants with:
   - Managers (1 per restaurant)
   - Staff (2 waiters and 2 chefs per restaurant)
   - Categories (Appetizers, Main Course, Desserts, Drinks)
   - Menu items (20 items per restaurant)
   - Tables (10 tables per restaurant)
4. **Orders** - 20 sample orders with order items

## How to use:

Run the following command to populate the database:

```bash
# Clear all data (except superusers) and create new test data
python manage.py seed_data

# Preserve existing user data while refreshing restaurant and order data
python manage.py seed_data --preserve-users
```

## Notes:

- The seeder **clears existing data** before creating new data (except superusers)
- Use the `--preserve-users` flag to keep existing user accounts
- All users are created with verified phone numbers
- Random data is generated for addresses, allergies, dietary preferences, etc.
- Passwords:
  - Superuser: admin123
  - Customers: password123
  - Managers: manager123
  - Staff: staff123 