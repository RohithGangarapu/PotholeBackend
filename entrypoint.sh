#!/bin/sh
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating Django superuser (if not exists)..."
python manage.py createsuperuser --noinput || true

echo "Starting Gunicorn..."
exec "$@"
