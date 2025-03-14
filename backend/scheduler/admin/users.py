from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from ..models import User, Period, Section

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'user_id', 'email', 'first_name', 'last_name', 'role', 'grade_level', 'gender')
    list_filter = ('role', 'grade_level', 'gender', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'gender')}),
        ('School info', {'fields': ('role', 'user_id', 'grade_level')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                  'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email', 'role', 'user_id', 'grade_level', 'gender'),
        }),
    )
    search_fields = ('username', 'user_id', 'first_name', 'last_name', 'email')
    ordering = ('username',)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        user = self.get_object(request, object_id)
        
        if user and user.role == 'STUDENT':
            # Get all periods
            periods = Period.objects.all().order_by('start_time')
            
            # Get student's sections grouped by period
            student_sections = {}
            student_sections_qs = Section.objects.filter(
                students=user
            ).select_related(
                'course', 'teacher', 'room', 'period'
            )
            
            for section in student_sections_qs:
                if section.period_id not in student_sections:
                    student_sections[section.period_id] = []
                student_sections[section.period_id].append(section)
            
            extra_context.update({
                'periods': periods,
                'student_sections': student_sections,
            })
        
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        ) 