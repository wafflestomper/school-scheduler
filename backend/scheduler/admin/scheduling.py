from django.contrib import admin
from ..models import Schedule, StudentPreference
from .base import TeacherFilterMixin, PeriodFilterMixin, RoomFilterMixin

@admin.register(Schedule)
class ScheduleAdmin(PeriodFilterMixin, RoomFilterMixin, admin.ModelAdmin):
    list_display = ('course', 'period', 'room', 'semester', 'year', 'get_student_count')
    list_filter = ('semester', 'year', 'course__grade_level')
    search_fields = ('course__name', 'course__code', 'room__name', 'period__name')
    raw_id_fields = ('course', 'period', 'room', 'students')
    filter_horizontal = ('students',)

    def get_student_count(self, obj):
        return obj.students.count()
    get_student_count.short_description = 'Students'

@admin.register(StudentPreference)
class StudentPreferenceAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'preference_level')
    list_filter = ('preference_level',)
    search_fields = ('student__username', 'student__first_name', 'student__last_name',
                    'course__name')
    raw_id_fields = ('student', 'course') 