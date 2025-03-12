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

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate --no-input

echo "Build completed." 