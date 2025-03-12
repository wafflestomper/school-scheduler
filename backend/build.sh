#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Current directory: $(pwd)"
echo "Listing directory contents:"
ls -la

echo "Setting up directories..."
mkdir -p logs
mkdir -p staticfiles

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setting up environment..."
export DJANGO_SETTINGS_MODULE=scheduler_config.settings
export PYTHONPATH=/opt/render/project/src:/opt/render/project/src/backend:$PYTHONPATH

echo "Verifying environment..."
python -c "
import os
import sys
print('Environment variables:')
print('RENDER:', 'RENDER' in os.environ)
print('DATABASE_URL:', bool(os.environ.get('DATABASE_URL')))
print('DJANGO_SETTINGS_MODULE:', os.environ.get('DJANGO_SETTINGS_MODULE'))
print('PYTHONPATH:', os.environ.get('PYTHONPATH'))
print('\nCurrent working directory:', os.getcwd())
print('\nDirectory contents:', os.listdir('.'))
print('\nParent directory contents:', os.listdir('..'))
print('\nPython sys.path:')
for p in sys.path:
    print(f'  {p}')
"

echo "Testing Django configuration..."
python -c "
import django
from django.conf import settings
print('Django version:', django.get_version())
print('DEBUG:', settings.DEBUG)
print('DATABASES:', {k: {**v, 'PASSWORD': '***'} if k == 'default' else v for k, v in settings.DATABASES.items()})
"

echo "Testing WSGI application..."
python -c "
import os, sys
sys.path.insert(0, '/opt/render/project/src')
from app import application
print('WSGI application loaded successfully')
"

echo "Running migrations..."
python manage.py migrate --no-input

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Build completed." 