import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 2

# Logging
accesslog = 'logs/gunicorn.access.log'
errorlog = 'logs/gunicorn.error.log'
loglevel = 'debug'

# Process naming
proc_name = 'school-scheduler'

# Django WSGI application path
wsgi_app = 'scheduler_config.wsgi:application'

# Python path
pythonpath = '/opt/render/project/src/backend' 