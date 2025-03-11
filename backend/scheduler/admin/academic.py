from django.contrib import admin
from ..models import Course, Period
from .base import TeacherFilterMixin

@admin.register(Course)
class CourseAdmin(TeacherFilterMixin, admin.ModelAdmin):
    list_display = ('name', 'teacher', 'course_type', 'duration', 'max_students', 'grade_level')
    list_filter = ('course_type', 'duration', 'grade_level')
    search_fields = ('name', 'description', 'teacher__username', 'teacher__first_name', 'teacher__last_name')
    raw_id_fields = ('teacher',)

@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_time', 'end_time', 'duration_minutes')
    list_filter = ('start_time', 'end_time')
    search_fields = ('name',)
    ordering = ('start_time',)

    def duration_minutes(self, obj):
        return obj.duration_minutes() 