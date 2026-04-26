#!/usr/bin/env bash
# Render.com build script for Django backend
set -o errexit

echo ">>> Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

echo ">>> Running migrations..."
python manage.py makemigrations payouts --noinput
python manage.py migrate --noinput

echo ">>> Collecting static files..."
python manage.py collectstatic --noinput

echo ">>> Seeding data (if needed)..."
python manage.py seed_data || echo "Seed data already exists or skipped."

echo ">>> Build complete!"
