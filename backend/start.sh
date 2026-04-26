#!/bin/bash
set -e

# Start Celery worker in the background
celery -A config worker -l info --concurrency=1 -B &

# Start Gunicorn server
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2
