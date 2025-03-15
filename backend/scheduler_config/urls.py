"""
URL configuration for scheduler_config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from scheduler.views.bulk_upload_views import BulkUserUploadView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.http import HttpResponse, Http404
import os
import mimetypes

def serve_csv(request, filename):
    """Serve CSV files with proper content type"""
    if not filename.endswith('.csv'):
        raise Http404("File not found")
        
    # Look in both possible locations for the file
    possible_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'example_data', filename),
        os.path.join(settings.BASE_DIR, 'example_data', filename)
    ]
    
    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break
            
    if not file_path:
        raise Http404(f"File not found: {filename}")
        
    try:
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read())
            response['Content-Type'] = 'text/csv'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    except IOError:
        raise Http404(f"Error reading file: {filename}")

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=True)),  # Redirect root to admin
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),  # For REST framework browsable API auth
    path('scheduler/', include('scheduler.urls')),  # Include scheduler URLs with prefix
    path('bulk-upload/users/', BulkUserUploadView.as_view(), name='bulk-user-upload'),
    path('download/csv/<str:filename>', serve_csv, name='serve_csv'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
