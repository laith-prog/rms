---
description: Repository Information Overview
alwaysApply: true
---

# Restaurant Management System Information

## Summary
A comprehensive restaurant management system with customer, staff, and admin interfaces. The system enables customers to discover restaurants, book tables, and order food, while providing staff with tools to manage orders and reservations, and administrators with oversight of operations.

## Structure
- **accounts/**: User authentication, profiles, and staff management
- **restaurants/**: Restaurant profiles, menus, tables, and reservations
- **orders/**: Order processing, tracking, and status management
- **rms/**: Main project configuration and settings
- **templates/**: HTML templates for admin and frontend views
- **staticfiles/**: Compiled static assets for production

## Language & Runtime
**Language**: Python
**Version**: 3.11.9 (specified in runtime.txt)
**Framework**: Django 5.2.4, Django REST Framework 3.16.0
**Package Manager**: pip

## Dependencies
**Main Dependencies**:
- Django 5.2.4
- djangorestframework 3.16.0
- djangorestframework-simplejwt 5.3.0
- pillow 11.3.0 (image processing)
- drf-yasg 1.21.10 (API documentation)
- django-cors-headers 4.3.1
- channels 4.0.0 (real-time updates)
- celery 5.3.6 (background tasks)
- redis 5.0.1 (caching and message broker)
- twilio 8.10.0 (phone verification)
- stripe 7.13.0 (payment processing)

**Development Dependencies**:
- pytest 7.4.3
- pytest-django 4.7.0
- django-debug-toolbar 4.2.0

## Build & Installation
```bash
# Set up virtual environment
python -m venv .venv
.venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Apply database migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## Deployment
**Procfile**: `web: python manage.py migrate && python manage.py collectstatic --no-input && gunicorn rms.wsgi`
**Static Files**: Served using WhiteNoise middleware
**Hosting**: Configured for Railway.app deployment (rms-production-7292.up.railway.app)

## Database
**Development**: SQLite3
**Production**: PostgreSQL (commented out in requirements.txt)
**Models**: Custom User model in accounts app, with related models for restaurants and orders

## API Documentation
**Framework**: Swagger/OpenAPI via drf-yasg
**Endpoints**:
- `/swagger/`: Interactive API documentation
- `/redoc/`: Alternative API documentation view
- `/swagger.json`: Raw OpenAPI schema

## Authentication
**System**: Custom token-based authentication with JWT
**Features**: Phone verification, password reset, token blacklisting
**Implementation**: Custom VersionedJWTAuthentication class

## Testing
**Framework**: pytest with pytest-django
**Test Files**: Basic test files in each app (accounts, restaurants, orders)
**Run Command**:
```bash
pytest
```

## Additional Features
**Real-time Updates**: Channels with Redis backend
**Background Tasks**: Celery for asynchronous processing
**Security**: Rate limiting, CORS configuration
**Geolocation**: geopy for location-based services