from django.contrib import admin
from ..models import SiblingGroup, StudentGroup

@admin.register(SiblingGroup)
class SiblingGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_student_count')
    search_fields = ('name', 'students__username', 'students__first_name', 'students__last_name')
    filter_horizontal = ('students',)

    def get_student_count(self, obj):
        return obj.students.count()
    get_student_count.short_description = 'Number of Siblings'

@admin.register(StudentGroup)
class StudentGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority', 'get_student_count')
    list_filter = ('priority',)
    search_fields = ('name', 'description', 'students__username',
                    'students__first_name', 'students__last_name')
    filter_horizontal = ('students',)

    def get_student_count(self, obj):
        return obj.students.count()
    get_student_count.short_description = 'Number of Students' 