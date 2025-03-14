from django.contrib import admin
from django.contrib.admin import AdminSite
from .base import TeacherFilterMixin
from .users import UserAdmin
from .course_admin import CourseAdmin, LanguageGroupAdmin
from .section_admin import SectionAdmin
from .period_admin import PeriodAdmin
from .facilities import RoomAdmin
from .configuration import (
    SchedulingConfigurationAdmin,
    CourseTypeConfigurationAdmin
)
from ..models import (
    User,
    Course,
    Section,
    Period,
    Room,
    SchedulingConfiguration,
    CourseTypeConfiguration,
    LanguageGroup
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
admin.site.register(SchedulingConfiguration, SchedulingConfigurationAdmin)
admin.site.register(CourseTypeConfiguration, CourseTypeConfigurationAdmin)
admin.site.register(LanguageGroup, LanguageGroupAdmin)

__all__ = [
    'TeacherFilterMixin',
    'CourseAdmin',
    'SectionAdmin',
    'PeriodAdmin',
    'UserAdmin',
    'RoomAdmin',
    'SchedulingConfigurationAdmin',
    'CourseTypeConfigurationAdmin',
    'LanguageGroupAdmin'
] 