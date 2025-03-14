from django.urls import path
from scheduler.views import user_views
from .views.course_views import CourseStudentView, CourseListView, CourseGroupView
from .views.upload_views import upload_page, upload_csv
from .views.student_views import StudentScheduleView
from .views.bulk_enrollment import BulkCourseEnrollmentView
from .views import (
    scheduling_views,
    course_views,
    room_views,
    period_views,
    configuration_views
)

app_name = 'scheduler'

urlpatterns = [
    # Course management
    path('courses/', CourseListView.as_view(), name='course-list'),
    path('courses/<int:course_id>/students/', CourseStudentView.as_view(), name='course-students'),
    path('courses/<int:course_id>/available-students/', CourseStudentView.as_view(), name='course-available-students'),
    path('courses/<int:course_id>/students/<int:student_id>/', CourseStudentView.as_view(), name='course-student-detail'),
    path('courses/<int:course_id>/remove-all-students/', CourseStudentView.as_view(), name='course-remove-all-students'),
    path('courses/<int:course_id>/add-students/', CourseStudentView.as_view(), name='course-add-students'),
    
    # Course group management
    path('course-groups/', CourseGroupView.as_view(), name='course-group-list'),
    path('course-groups/<int:group_id>/', CourseGroupView.as_view(), name='course-group-detail'),
    
    # Student management
    path('students/<int:student_id>/schedule/', StudentScheduleView.as_view(), name='student-schedule'),
    
    # Upload routes
    path('upload/', upload_page, name='upload-page'),
    path('api/upload/', upload_csv, name='upload-csv'),
    
    # Scheduling routes
    path('pe6-distribution/', scheduling_views.PE6DistributionView.as_view(), name='pe6_distribution'),
    
    # Bulk enrollment
    path('api/bulk-enroll/', BulkCourseEnrollmentView.as_view(), name='bulk-course-enrollment'),
]
