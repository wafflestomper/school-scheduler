from django.contrib import admin
from ..models import Section
from .base import TeacherFilterMixin

@admin.register(Section)
class SectionAdmin(TeacherFilterMixin, admin.ModelAdmin):
    list_display = ('name', 'course', 'get_course_duration', 'trimester', 'teacher', 'period', 'room', 'get_student_count')
    list_filter = ('course__grade_level', 'course__duration', 'trimester', 'period')
    search_fields = ('name', 'course__name', 'course__code', 'teacher__username', 'teacher__first_name', 'teacher__last_name')
    raw_id_fields = ('course', 'teacher', 'period', 'room')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('course', 'section_number', 'name')
        }),
        ('Scheduling', {
            'fields': ('trimester', 'period', 'room')
        }),
        ('Staff', {
            'fields': ('teacher',)
        }),
        ('Capacity', {
            'fields': ('max_students',)
        })
    )
    
    def get_student_count(self, obj):
        return obj.students.count()
    get_student_count.short_description = 'Students'
    
    def get_course_duration(self, obj):
        return obj.course.get_duration_display()
    get_course_duration.short_description = 'Duration'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.course.duration != 'TRIMESTER':
            form.base_fields['trimester'].disabled = True
        return form 