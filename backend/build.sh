#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Setting up directories..."
mkdir -p logs
mkdir -p staticfiles

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setting up environment..."
export DJANGO_SETTINGS_MODULE=scheduler_config.settings
export PYTHONPATH=/opt/render/project/src/backend:$PYTHONPATH

echo "Verifying environment..."
python -c "
import os
import sys
print('Environment variables:')
print('RENDER:', 'RENDER' in os.environ)
print('DATABASE_URL:', bool(os.environ.get('DATABASE_URL')))
print('DJANGO_SETTINGS_MODULE:', os.environ.get('DJANGO_SETTINGS_MODULE'))
print('PYTHONPATH:', os.environ.get('PYTHONPATH'))
print('\nPython sys.path:')
for p in sys.path:
    print(f'  {p}')
"

echo "Running migrations..."
python manage.py migrate --no-input

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Build completed." 