import os
import sys

# Add the backend directory to Python path
backend_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scheduler_config.settings')

from django.core.wsgi import get_wsgi_application
app = get_wsgi_application() 