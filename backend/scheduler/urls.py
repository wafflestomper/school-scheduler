from django.urls import path
from .views.user_views import bulk_upload_users

app_name = 'api'

urlpatterns = [
    path('bulk-upload-users/', bulk_upload_users, name='bulk_upload_users'),
]
