from django.contrib import admin
from ..models import (
    SchedulingConfiguration, SiblingConfiguration,
    StudentGroupConfiguration, ElectiveConfiguration,
    CourseTypeConfiguration
)

@admin.register(SchedulingConfiguration)
class SchedulingConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'max_class_size', 'max_consecutive_periods',
                   'min_prep_periods', 'prioritize_specialized_rooms')
    list_filter = ('active',)
    search_fields = ('name',)

@admin.register(SiblingConfiguration)
class SiblingConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'keep_siblings_together', 'priority')
    list_filter = ('active',)
    search_fields = ('name',)

@admin.register(StudentGroupConfiguration)
class StudentGroupConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'respect_separation_groups',
                   'respect_grouping_preferences', 'priority')
    list_filter = ('active',)
    search_fields = ('name',)

@admin.register(ElectiveConfiguration)
class ElectiveConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'max_electives_per_student',
                   'prioritize_grade_level', 'allow_mixed_grades')
    list_filter = ('active',)
    search_fields = ('name',)

@admin.register(CourseTypeConfiguration)
class CourseTypeConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'enforce_grade_levels',
                   'allow_mixed_levels', 'respect_prerequisites')
    list_filter = ('active',)
    search_fields = ('name',) 