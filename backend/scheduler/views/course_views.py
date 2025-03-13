from __future__ import annotations
from typing import Dict, Any, List, Optional
from django.http import JsonResponse, HttpRequest
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db.models import Q, Prefetch, Count
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Course, User, CourseTypeConfiguration
import json
import logging
from functools import wraps
from time import time

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = 300  # 5 minutes

def log_execution_time(func):
    """Decorator to log execution time of view methods"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time()
        result = func(*args, **kwargs)
        execution_time = time() - start_time
        logger.info(
            f"{func.__name__} executed in {execution_time:.2f} seconds",
            extra={
                'execution_time': execution_time,
                'view_method': func.__name__
            }
        )
        return result
    return wrapper

def handle_exceptions(func):
    """Decorator to handle common exceptions in view methods"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Course.DoesNotExist:
            logger.warning("Course not found", extra={'course_id': kwargs.get('course_id')})
            return JsonResponse({'error': 'Course not found'}, status=404)
        except ValidationError as e:
            logger.warning(
                "Validation error",
                extra={'errors': str(e), 'course_id': kwargs.get('course_id')}
            )
            return JsonResponse({'error': str(e)}, status=400)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON data received")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(
                f"Unexpected error: {str(e)}",
                exc_info=True,
                extra={'course_id': kwargs.get('course_id')}
            )
            return JsonResponse(
                {'error': 'An unexpected error occurred'},
                status=500
            )
    return wrapper

@method_decorator(csrf_exempt, name='dispatch')
class CourseStudentView(View):
    def get_course_with_students(self, course_id: int) -> Course:
        """Get course with prefetched students"""
        cache_key = f'course_with_students_{course_id}'
        course = cache.get(cache_key)
        
        if course is None:
            course = Course.objects.prefetch_related(
                Prefetch(
                    'students',
                    queryset=User.objects.only(
                        'id', 'first_name', 'last_name', 'grade_level'
                    )
                ),
                Prefetch(
                    'sections',
                    queryset=Course.objects.only('id')
                )
            ).get(id=course_id)
            cache.set(cache_key, course, CACHE_TIMEOUT)
        
        return course

    @handle_exceptions
    @log_execution_time
    def get(self, request: HttpRequest, course_id: int, student_id: Optional[int] = None) -> JsonResponse:
        """Handle GET requests for course students"""
        course = self.get_course_with_students(course_id)
        config = CourseTypeConfiguration.objects.filter(active=True).first()
        
        # Get registered students
        students_data = list(course.students.values(
            'id', 'first_name', 'last_name', 'grade_level'
        ))
        
        response_data = {
            'students': students_data,
            'course_grade': course.grade_level,
            'total_capacity': course.get_total_capacity(),
            'available_space': course.get_available_space(),
            'section_stats': course.get_section_stats()
        }
        
        # If requesting available students
        if 'available-students' in request.path:
            cache_key = f'available_students_{course_id}'
            available_students = cache.get(cache_key)
            
            if available_students is None:
                # Get students not in this course
                registered_ids = set(course.students.values_list('id', flat=True))
                students_query = User.objects.filter(role='STUDENT')
                
                # Apply grade level restrictions if configured
                if config and config.enforce_grade_levels and not config.allow_mixed_levels:
                    students_query = students_query.filter(grade_level=course.grade_level)
                
                # Exclude registered students efficiently
                if registered_ids:
                    students_query = students_query.exclude(id__in=registered_ids)
                
                available_students = list(students_query.values(
                    'id', 'first_name', 'last_name', 'grade_level'
                ))
                cache.set(cache_key, available_students, CACHE_TIMEOUT)
            
            response_data.update({
                'available_students': available_students,
                'enforce_grade_levels': config.enforce_grade_levels if config else False,
                'allow_mixed_levels': config.allow_mixed_levels if config else True
            })
        
        return JsonResponse(response_data)

    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def post(self, request: HttpRequest, course_id: int, student_id: Optional[int] = None) -> JsonResponse:
        """Handle POST requests for adding/removing students"""
        course = get_object_or_404(Course, id=course_id)
        config = CourseTypeConfiguration.objects.filter(active=True).first()
        
        # If URL ends with /remove-all-students/, remove all students
        if 'remove-all-students' in request.path:
            course.students.clear()
            cache.delete(f'course_with_students_{course_id}')
            logger.info(f"Removed all students from course {course_id}")
            return JsonResponse({'status': 'success'})
        
        # If student_id is provided, this is a remove request
        if student_id is not None:
            course.students.remove(student_id)
            cache.delete(f'course_with_students_{course_id}')
            cache.delete(f'available_students_{course_id}')
            logger.info(f"Removed student {student_id} from course {course_id}")
            return JsonResponse({'status': 'success'})
        
        # Otherwise, this is an add request
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        
        if not student_ids:
            return JsonResponse({'error': 'No students specified'}, status=400)
        
        if not course.has_space_for_students(len(student_ids)):
            return JsonResponse(
                {'error': 'Adding these students would exceed course capacity'},
                status=400
            )
        
        # Get students and validate grade levels if configured
        students = User.objects.filter(id__in=student_ids, role='STUDENT')
        
        if not students.exists():
            return JsonResponse({'error': 'No valid students found'}, status=400)
        
        if config and config.enforce_grade_levels and not config.allow_mixed_levels:
            invalid_grade_students = students.exclude(grade_level=course.grade_level)
            if invalid_grade_students.exists():
                return JsonResponse(
                    {'error': 'Some students are not in the correct grade level for this course'},
                    status=400
                )
        
        course.students.add(*students)
        
        # Clear relevant caches
        cache.delete(f'course_with_students_{course_id}')
        cache.delete(f'available_students_{course_id}')
        
        logger.info(
            f"Added {len(students)} students to course {course_id}",
            extra={'student_ids': list(students.values_list('id', flat=True))}
        )
        
        return JsonResponse({'status': 'success'})

@method_decorator(csrf_exempt, name='dispatch')
class CourseListView(View):
    @handle_exceptions
    @log_execution_time
    def get(self, request: HttpRequest) -> JsonResponse:
        """Handle GET requests for course lists"""
        cache_key = 'all_courses_list'
        courses_data = cache.get(cache_key)
        
        if courses_data is None:
            courses = Course.objects.prefetch_related(
                Prefetch(
                    'students',
                    queryset=User.objects.only('id')
                ),
                'sections'
            ).select_related(
                'course_type_config'
            ).annotate(
                student_count=Count('students'),
                section_count=Count('sections')
            )
            
            courses_data = []
            for course in courses:
                courses_data.append({
                    'id': course.id,
                    'name': course.name,
                    'code': course.code,
                    'grade_level': course.grade_level,
                    'duration': course.duration,
                    'course_type': course.course_type,
                    'total_capacity': course.get_total_capacity(),
                    'student_count': course.student_count,
                    'section_count': course.section_count,
                    'available_space': course.get_available_space()
                })
            
            cache.set(cache_key, courses_data, CACHE_TIMEOUT)
        
        return JsonResponse({'courses': courses_data})

    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def post(self, request: HttpRequest) -> JsonResponse:
        """Handle POST requests for creating new courses"""
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['name', 'grade_level']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return JsonResponse(
                {'error': f'Missing required fields: {", ".join(missing_fields)}'},
                status=400
            )
        
        try:
            course = Course.objects.create(
                name=data['name'],
                code=data.get('code'),
                description=data.get('description', ''),
                grade_level=data['grade_level'],
                num_sections=data.get('num_sections', 1),
                max_students_per_section=data.get('max_students_per_section', 30),
                duration=data.get('duration', CourseDurations.TRIMESTER),
                course_type=data.get('course_type', CourseTypes.CORE)
            )
            
            # Clear cache
            cache.delete('all_courses_list')
            
            logger.info(
                f"Created new course: {course.name}",
                extra={'course_id': course.id, 'course_data': data}
            )
            
            return JsonResponse({
                'status': 'success',
                'course_id': course.id
            })
            
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400) 