"""
WSGI config for school scheduler project.
"""

import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'school_scheduler'))

from scheduler_config.wsgi import application 