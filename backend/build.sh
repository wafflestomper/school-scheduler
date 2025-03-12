#!/usr/bin/env bash
# exit on error
set -o errexit

# Create logs directory
mkdir -p logs

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Build completed." 