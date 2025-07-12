# Restaurant Management System

A comprehensive restaurant management system with customer, staff, and admin interfaces. The system consists of:

1. **User App** - For customers to discover restaurants, book tables, and order food (dine-in/pickup/delivery)
2. **Staff App** - For waiters and chefs to manage orders, reservations, and kitchen workflow
3. **Admin Dashboard** - For managers and employees to oversee operations, staff, and promotions

## Features

### User App Features
- Authentication via phone number verification
- Restaurant discovery and search
- Menu browsing and filtering
- Table reservations
- Food ordering (dine-in, pickup, delivery)
- Order tracking
- User profiles with preferences and history

### Staff App Features
- Waiter features: Table booking, order taking, checkout
- Chef features: Order approval, preparation time estimates, ready notifications
- Real-time order status updates

### Admin Dashboard Features
- Staff management
- Restaurant profile and menu management
- Reservation management
- Analytics and reporting

## Technical Stack

- **Backend**: Django, Django REST Framework
- **Database**: SQLite (development), PostgreSQL (production)
- **Authentication**: Custom token-based authentication with phone verification
- **Image Handling**: Django ImageField with Pillow
- **API Documentation**: Swagger/OpenAPI with drf-yasg

## Setup Instructions

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/rms.git
   cd rms
   ```

2. Set up a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Apply migrations:
   ```
   python manage.py migrate
   ```

5. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

6. Run the development server:
   ```
   python manage.py runserver
   ```

7. Access the admin interface at `http://localhost:8000/admin/`

## API Documentation

The API is documented using Swagger/OpenAPI. Once the server is running, you can access:

- Swagger UI: `http://localhost:8000/swagger/` - Interactive API documentation
- ReDoc: `http://localhost:8000/redoc/` - Alternative API documentation view
- OpenAPI Schema: `http://localhost:8000/swagger.json` - Raw OpenAPI schema

## API Endpoints

### Authentication and User Management
- `POST /api/accounts/send-verification-code/` - Send verification code to phone
- `POST /api/accounts/verify-phone/` - Verify phone with code
- `POST /api/accounts/register/` - Register new user with verified phone
- `POST /api/accounts/login/` - Login user
- `POST /api/accounts/logout/` - Logout user
- `POST /api/accounts/forgot-password/` - Request password reset code
- `POST /api/accounts/verify-reset-code/` - Verify password reset code
- `POST /api/accounts/reset-password/` - Reset password with verified code

### User Profile
- `GET /api/accounts/profile/` - Get user profile
- `PUT /api/accounts/profile/update/` - Update user profile
- `POST /api/accounts/profile/upload-image/` - Upload profile image

### Restaurants
- `GET /api/restaurants/` - List restaurants
- `GET /api/restaurants/categories/` - List food categories
- `GET /api/restaurants/{id}/` - Get restaurant details
- `GET /api/restaurants/{id}/menu/` - Get restaurant menu
- `GET /api/restaurants/{id}/reviews/` - Get restaurant reviews

### Reservations
- `GET /api/restaurants/{id}/tables/` - Get available tables
- `POST /api/restaurants/{id}/reserve/` - Create reservation
- `GET /api/restaurants/reservations/` - List user's reservations
- `GET /api/restaurants/reservations/{id}/` - Get reservation details
- `POST /api/restaurants/reservations/{id}/cancel/` - Cancel reservation

### Orders
- `GET /api/orders/` - List user's orders
- `POST /api/orders/create/` - Create new order
- `GET /api/orders/{id}/` - Get order details
- `POST /api/orders/{id}/cancel/` - Cancel order
- `GET /api/orders/{id}/track/` - Track order status

### Staff Endpoints
- `GET /api/orders/staff/` - List orders for staff
- `POST /api/orders/staff/{id}/update/` - Update order status
- `GET /api/orders/chef/orders/` - Get orders for chef
- `GET /api/orders/waiter/orders/` - Get orders for waiter

## License

This project is licensed under the MIT License - see the LICENSE file for details. 