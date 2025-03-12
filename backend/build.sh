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

echo "Verifying database connection..."
python -c "
import os
import dj_database_url
print('DATABASE_URL:', bool(os.environ.get('DATABASE_URL')))
config = dj_database_url.config()
print('Database config:', {k: v for k, v in config.items() if k != 'PASSWORD'})
"

echo "Running migrations..."
python manage.py migrate --no-input

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Build completed." 