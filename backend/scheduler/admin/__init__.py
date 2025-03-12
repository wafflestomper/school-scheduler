from django.contrib import admin
from django.contrib.admin import AdminSite
from .base import TeacherFilterMixin
from .course import CourseAdmin
from .section_admin import SectionAdmin
from .period_admin import PeriodAdmin
from .users import UserAdmin
from .facilities import RoomAdmin
from .groups import StudentGroupAdmin, SiblingGroupAdmin
from .configuration import (
    SchedulingConfigurationAdmin,
    SiblingConfigurationAdmin,
    StudentGroupConfigurationAdmin,
    ElectiveConfigurationAdmin,
    CourseTypeConfigurationAdmin
)
from ..models import (
    User, Course, Period, Section, Room,
    StudentGroup, SiblingGroup,
    SchedulingConfiguration, SiblingConfiguration,
    StudentGroupConfiguration, ElectiveConfiguration,
    CourseTypeConfiguration
)

class CustomAdminSite(AdminSite):
    def each_context(self, request):
        context = super().each_context(request)
        context['extra_css'] = ['admin/css/custom_admin.css']
        return context

# Replace the default admin site with our custom one
admin.site = CustomAdminSite()

# Register all models with the custom admin site
admin.site.register(User, UserAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(Period, PeriodAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(StudentGroup, StudentGroupAdmin)
admin.site.register(SiblingGroup, SiblingGroupAdmin)
admin.site.register(SchedulingConfiguration, SchedulingConfigurationAdmin)
admin.site.register(SiblingConfiguration, SiblingConfigurationAdmin)
admin.site.register(StudentGroupConfiguration, StudentGroupConfigurationAdmin)
admin.site.register(ElectiveConfiguration, ElectiveConfigurationAdmin)
admin.site.register(CourseTypeConfiguration, CourseTypeConfigurationAdmin)

__all__ = [
    'TeacherFilterMixin',
    'CourseAdmin',
    'SectionAdmin',
    'PeriodAdmin',
    'UserAdmin',
    'RoomAdmin',
    'StudentGroupAdmin',
    'SiblingGroupAdmin',
    'SchedulingConfigurationAdmin',
    'SiblingConfigurationAdmin',
    'StudentGroupConfigurationAdmin',
    'ElectiveConfigurationAdmin',
    'CourseTypeConfigurationAdmin'
] 