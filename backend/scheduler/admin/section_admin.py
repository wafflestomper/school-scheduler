from django.contrib import admin
from ..models import Section
from .base import TeacherFilterMixin

@admin.register(Section)
class SectionAdmin(TeacherFilterMixin, admin.ModelAdmin):
    list_display = ('name', 'course', 'teacher', 'period', 'room', 'get_student_count')
    list_filter = ('course__grade_level', 'period')
    search_fields = ('name', 'course__name', 'course__code', 'teacher__username', 'teacher__first_name', 'teacher__last_name')
    raw_id_fields = ('course', 'teacher', 'period', 'room')
    
    def get_student_count(self, obj):
        return obj.students.count()
    get_student_count.short_description = 'Students' 