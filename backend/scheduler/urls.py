from django.urls import path
from .views import user_views
from .views.course_views import CourseStudentView

app_name = 'scheduler'

urlpatterns = [
    path('bulk-upload/', user_views.bulk_upload_users, name='bulk-upload'),
    path('bulk-upload/template/', user_views.download_user_template, name='download-template'),
    
    # Course student management API endpoints
    path('api/courses/<int:course_id>/available-students/',
         CourseStudentView.as_view(),
         name='course-available-students'),
    path('api/courses/<int:course_id>/enrolled-students/',
         CourseStudentView.as_view(),
         name='course-enrolled-students'),
    path('api/courses/<int:course_id>/add-students/',
         CourseStudentView.as_view(),
         name='course-add-students'),
    path('api/courses/<int:course_id>/remove-student/<int:student_id>/',
         CourseStudentView.as_view(),
         name='course-remove-student'),
    path('api/courses/<int:course_id>/remove-all-students/',
         CourseStudentView.as_view(),
         name='course-remove-all-students'),
]
