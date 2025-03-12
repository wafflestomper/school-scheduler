#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Setting up directories..."
mkdir -p logs
mkdir -p staticfiles

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setting up environment..."
export PYTHONPATH=/opt/render/project/src/backend:$PYTHONPATH
export DJANGO_SETTINGS_MODULE=scheduler_config.settings

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Build completed." 