"""
WSGI config for school scheduler project.
"""

import os
import sys

# Add the backend directory to Python path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.append(backend_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scheduler_config.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# For gunicorn
app = application 