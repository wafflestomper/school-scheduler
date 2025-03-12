from django.contrib import admin
from django.contrib.admin import AdminSite
from .users import UserAdmin
from .academic import CourseAdmin, PeriodAdmin, SectionAdmin
from .facilities import RoomAdmin
from .scheduling import ScheduleAdmin, StudentPreferenceAdmin
from .groups import SiblingGroupAdmin, StudentSeparationGroupAdmin
from .configuration import (
    TeacherConfigurationAdmin,
    RoomConfigurationAdmin,
    StudentConfigurationAdmin
)
from ..models import (
    User, Course, Period, Section, Room, Schedule, StudentPreference,
    SiblingGroup, StudentSeparationGroup,
    TeacherConfiguration, RoomConfiguration, StudentConfiguration
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
admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(StudentPreference, StudentPreferenceAdmin)
admin.site.register(SiblingGroup, SiblingGroupAdmin)
admin.site.register(StudentSeparationGroup, StudentSeparationGroupAdmin)
admin.site.register(TeacherConfiguration, TeacherConfigurationAdmin)
admin.site.register(RoomConfiguration, RoomConfigurationAdmin)
admin.site.register(StudentConfiguration, StudentConfigurationAdmin) 