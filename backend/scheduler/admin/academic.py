from django.contrib import admin
from ..models import Course, Period, Section
from .base import TeacherFilterMixin

class SectionInline(admin.TabularInline):
    model = Section
    extra = 0
    fields = ('section_number', 'name', 'teacher', 'period', 'room')
    raw_id_fields = ('teacher', 'period', 'room')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'course_type', 'duration', 'num_sections', 'max_students_per_section', 'grade_level')
    list_filter = ('course_type', 'duration', 'grade_level')
    search_fields = ('name', 'code', 'description')
    inlines = [SectionInline]

@admin.register(Section)
class SectionAdmin(TeacherFilterMixin, admin.ModelAdmin):
    list_display = ('name', 'course', 'teacher', 'period', 'room', 'get_student_count')
    list_filter = ('course__grade_level', 'period')
    search_fields = ('name', 'course__name', 'course__code', 'teacher__username', 'teacher__first_name', 'teacher__last_name')
    raw_id_fields = ('course', 'teacher', 'period', 'room')
    filter_horizontal = ('students',)

    def get_student_count(self, obj):
        return obj.students.count()
    get_student_count.short_description = 'Students'

@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_time', 'end_time')
    search_fields = ('name',) 