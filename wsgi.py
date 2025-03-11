"""
WSGI config for school scheduler project.
"""

import os
import sys

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheduler_config.wsgi import application 