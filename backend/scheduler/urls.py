from django.urls import path
from scheduler.views import user_views
from .views.course_views import CourseStudentView
from .views.upload_views import upload_page, upload_csv
from .views import (
    scheduling_views,
    course_views,
    room_views,
    period_views,
    configuration_views,
    group_views
)

app_name = 'scheduler'

urlpatterns = [
    # Other URLs...
    path('upload/', upload_page, name='upload-page'),
    path('api/upload/', upload_csv, name='upload-csv'),
    path('pe6-distribution/', scheduling_views.PE6DistributionView.as_view(), name='pe6_distribution'),
]
