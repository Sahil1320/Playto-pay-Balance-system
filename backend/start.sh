#!/bin/bash
set -e

# Run database migrations and seed data
echo "Running migrations..."
python manage.py makemigrations payouts --noinput || true
python manage.py migrate --noinput

echo "Seeding data..."
python manage.py seed_data || true

# Start Celery worker in the background
celery -A config worker -l info --concurrency=1 -B &

# Start Gunicorn server
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2
