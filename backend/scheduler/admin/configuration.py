from django.contrib import admin
from ..models import (
    SchedulingConfiguration,
    CourseTypeConfiguration
)

@admin.register(SchedulingConfiguration)
class SchedulingConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')
    list_filter = ('active',)
    search_fields = ('name',)

@admin.register(CourseTypeConfiguration)
class CourseTypeConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'enforce_grade_levels',
                   'allow_mixed_levels', 'respect_prerequisites')
    list_filter = ('active',)
    search_fields = ('name',) 