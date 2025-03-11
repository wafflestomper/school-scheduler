from django.contrib import admin
from ..models import TeacherConfiguration, RoomConfiguration, StudentConfiguration

@admin.register(TeacherConfiguration)
class TeacherConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'max_consecutive_periods', 'min_prep_periods',
                   'respect_subject_preferences')
    list_filter = ('active',)
    search_fields = ('name',)

@admin.register(RoomConfiguration)
class RoomConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'prioritize_specialized_rooms',
                   'allow_room_sharing', 'max_room_utilization')
    list_filter = ('active',)
    search_fields = ('name',)

@admin.register(StudentConfiguration)
class StudentConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'max_class_size', 'respect_student_preferences',
                   'enforce_grade_levels', 'respect_separation_groups',
                   'keep_siblings_together')
    list_filter = ('active',)
    search_fields = ('name',) 