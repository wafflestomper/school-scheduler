from django.urls import path
from .views.user_views import bulk_upload_users, download_user_template

app_name = 'api'

urlpatterns = [
    path('bulk-upload/users/', bulk_upload_users, name='bulk_upload_users'),
    path('bulk-upload/template/', download_user_template, name='download_user_template'),
]
