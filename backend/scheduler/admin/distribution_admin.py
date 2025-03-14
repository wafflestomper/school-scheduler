from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from ..models import Course, Section
from ..scheduling.course_distributor import (
    distribute_course_students,
    distribute_all_courses,
    clear_course_distribution,
    clear_all_distributions,
    get_course_distribution_status
)
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class CourseDistributionMixin:
    change_list_template = 'admin/scheduler/course_distribution.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('distribution/', self.admin_site.admin_view(self.distribution_view), name='course_distribution'),
            path('api/distribute/<int:course_id>/', self.admin_site.admin_view(self.distribute_course), name='distribute_course'),
            path('api/distribute-all/', self.admin_site.admin_view(self.distribute_all), name='distribute_all'),
            path('api/clear-distribution/<int:course_id>/', self.admin_site.admin_view(self.clear_distribution), name='clear_distribution'),
            path('api/clear-all-distributions/', self.admin_site.admin_view(self.clear_all), name='clear_all'),
            path('api/course-distribution/<int:course_id>/', self.admin_site.admin_view(self.get_distribution), name='get_distribution'),
        ]
        return custom_urls + urls

    def distribution_view(self, request):
        """Main view for course distribution management"""
        courses = Course.objects.all()
        course_data = []
        
        for course in courses:
            status = get_course_distribution_status(course.id)
            course_data.append({
                'id': course.id,
                'name': course.name,
                'code': course.code,
                'grade_level': course.grade_level,
                'total_students': status['total_students'],
                'num_sections': status['num_sections'],
                'created_sections': status['created_sections'],
                'is_distributed': status['is_distributed']
            })
        
        context = {
            'courses': course_data,
            **self.admin_site.each_context(request),
        }
        
        return render(request, 'admin/scheduler/course_distribution.html', context)

    @method_decorator(csrf_exempt)
    def distribute_course(self, request, course_id):
        """API endpoint to distribute students for a specific course"""
        if request.method == 'POST':
            result = distribute_course_students(course_id)
            return JsonResponse(result)
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    @method_decorator(csrf_exempt)
    def distribute_all(self, request):
        """API endpoint to distribute students for all courses"""
        if request.method == 'POST':
            result = distribute_all_courses()
            return JsonResponse(result)
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    @method_decorator(csrf_exempt)
    def clear_distribution(self, request, course_id):
        """API endpoint to clear distribution for a specific course"""
        if request.method == 'POST':
            result = clear_course_distribution(course_id)
            return JsonResponse(result)
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    @method_decorator(csrf_exempt)
    def clear_all(self, request):
        """API endpoint to clear all course distributions"""
        if request.method == 'POST':
            result = clear_all_distributions()
            return JsonResponse(result)
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    def get_distribution(self, request, course_id):
        """API endpoint to get distribution status for a course"""
        result = get_course_distribution_status(course_id)
        return JsonResponse(result)

def get_course_distribution_status(course_id: int) -> Dict[str, any]:
    """
    Get the current distribution status for a course.
    """
    try:
        course = Course.objects.get(id=course_id)
        sections = Section.objects.filter(course=course)
        created_sections = sections.count()
        
        return {
            'success': True,
            'course_name': course.name,
            'course_code': course.code,
            'total_students': course.students.count(),
            'num_sections': course.num_sections,
            'created_sections': created_sections,
            'is_distributed': sections.filter(students__isnull=False).exists(),
            'distribution': [
                {
                    'section_name': section.name,
                    'student_count': section.students.count(),
                    'period': section.period.name if section.period else None,
                    'students': list(section.students.values('id', 'first_name', 'last_name', 'grade_level'))
                }
                for section in sections
            ]
        }
    except Course.DoesNotExist:
        return {'success': False, 'error': f'Course with id {course_id} not found'}
    except Exception as e:
        logger.error(f"Error getting course distribution status: {str(e)}")
        return {'success': False, 'error': str(e)} 