from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from scheduler.models import Period, Section

class UserAdmin(BaseUserAdmin):
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