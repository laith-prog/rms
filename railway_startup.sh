#!/bin/bash

# Run migrations
echo "Running database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Create superuser
echo "Creating superuser..."
export DJANGO_SUPERUSER_PHONE=0953241659
export DJANGO_SUPERUSER_EMAIL=admin@example.com
export DJANGO_SUPERUSER_PASSWORD=admin123
export DJANGO_SUPERUSER_FIRST_NAME=Admin
export DJANGO_SUPERUSER_LAST_NAME=User

# Try both methods to create a superuser
python manage.py create_superuser_if_none_exists
python create_superuser.py

# Start Gunicorn
echo "Starting Gunicorn..."
gunicorn rms.wsgi 