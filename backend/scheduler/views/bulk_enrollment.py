from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.cache import cache
from ..models import Course, User
from ..decorators import handle_exceptions, log_execution_time
import json
import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class BulkCourseRegistrationView(View):
    """Handle bulk registration of students into core courses"""
    
    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def post(self, request):
        """
        Register students in core courses for their grade level
        
        Expected POST data:
        {
            "grade_levels": [6, 7, ...],  # List of grade levels to process
            "clear_existing": false  # Optional: whether to clear existing registrations
        }
        """
        try:
            data = json.loads(request.body)
            grade_levels = data.get('grade_levels', [])
            clear_existing = data.get('clear_existing', False)
            
            if not grade_levels:
                return JsonResponse({
                    'error': 'No grade levels specified'
                }, status=400)
            
            results = {
                'success': True,
                'registrations': {},
                'errors': []
            }
            
            # Process each grade level
            for grade in grade_levels:
                grade_results = {
                    'students_processed': 0,
                    'courses_processed': 0,
                    'total_registrations': 0
                }
                
                # Get all students in this grade
                students = User.objects.filter(
                    role='STUDENT',
                    grade_level=grade
                )
                
                if not students.exists():
                    results['errors'].append(f'No students found for grade {grade}')
                    continue
                
                # Get all core courses for this grade
                core_courses = Course.objects.filter(
                    grade_level=grade,
                    course_type='CORE'
                )
                
                if not core_courses.exists():
                    results['errors'].append(f'No core courses found for grade {grade}')
                    continue
                
                # Clear existing registrations if requested
                if clear_existing:
                    for course in core_courses:
                        course.students.clear()
                
                # Register each student in all core courses
                for student in students:
                    for course in core_courses:
                        course.students.add(student)
                        grade_results['total_registrations'] += 1
                
                grade_results['students_processed'] = students.count()
                grade_results['courses_processed'] = core_courses.count()
                results['registrations'][grade] = grade_results
                
                # Clear relevant caches
                for course in core_courses:
                    cache.delete(f'course_with_students_{course.id}')
                    cache.delete(f'available_students_{course.id}')
            
            return JsonResponse(results)
            
        except Exception as e:
            logger.error(f"Error in bulk registration: {str(e)}")
            return JsonResponse({
                'error': str(e)
            }, status=500) 