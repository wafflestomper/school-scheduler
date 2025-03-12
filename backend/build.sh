#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Setting up directories..."
mkdir -p logs
mkdir -p staticfiles

echo "Installing root dependencies..."
cd ..
pip install -r requirements.txt

echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt

echo "Setting up environment..."
export DJANGO_SETTINGS_MODULE=scheduler_config.settings
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo "Verifying database environment..."
python -c "
import os
print('RENDER:', 'RENDER' in os.environ)
print('POSTGRES_HOST:', bool(os.environ.get('POSTGRES_HOST')))
print('POSTGRES_PASSWORD:', bool(os.environ.get('POSTGRES_PASSWORD')))
"

echo "Running migrations..."
python manage.py migrate --no-input

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Build completed." 