import os
import sys

# Add the backend directory to Python path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_path)

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scheduler_config.settings')

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
app = application = get_wsgi_application() 