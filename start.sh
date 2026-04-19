#!/bin/bash

echo "🚀 Starting Deployment Initialisation..."

# 1. Run Migrations
echo "📦 Running Database Migrations..."
cd /app/django_app
python manage.py migrate --noinput

# 2. Collect Static Files
echo "🎨 Collecting Static Files..."
python manage.py collectstatic --noinput

# 3. Start Supervisor
echo "🛰️ Launching Process Manager (Supervisord)..."
cd /app
/usr/bin/supervisord -c /app/supervisord.conf
