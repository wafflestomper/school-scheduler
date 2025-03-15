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
from ..models import Course, User, CourseTypeConfiguration, CourseGroup
import json
import logging
from functools import wraps
from time import time
from ..decorators import handle_exceptions, log_execution_time
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

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
class CourseStudentView(APIView):
    permission_classes = [AllowAny]
    
    def get_course_with_students(self, course_id: int) -> Course:
        """Get a course with its students, using cache if available"""
        cache_key = f'course_with_students_{course_id}'
        course = cache.get(cache_key)
        
        if course is None:
            course = get_object_or_404(
                Course.objects.prefetch_related('students', 'sections__students'),
                id=course_id
            )
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
        
        # Check if this is an "add filtered students" request
        if data.get('add_filtered_students'):
            grade_level = data.get('grade_level')
            search_query = data.get('search_query', '').strip()
            
            # Start with all available students
            students_query = User.objects.filter(role='STUDENT')
            
            # Exclude already registered students
            registered_ids = set(course.students.values_list('id', flat=True))
            if registered_ids:
                students_query = students_query.exclude(id__in=registered_ids)
            
            # Apply grade level filter if specified
            if grade_level:
                students_query = students_query.filter(grade_level=grade_level)
            elif config and config.enforce_grade_levels and not config.allow_mixed_levels:
                students_query = students_query.filter(grade_level=course.grade_level)
            
            # Apply search filter if specified
            if search_query:
                students_query = students_query.filter(
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query)
                )
            
            students = students_query.all()
            
            # Get available space
            available_space = course.get_available_space()
            total_students = students.count()
            
            # Add all students to the course (they will be registered but not enrolled)
            course.students.add(*students)
            
            # Clear relevant caches
            cache.delete(f'course_with_students_{course_id}')
            cache.delete(f'available_students_{course_id}')
            
            logger.info(
                f"Added {total_students} students to course {course_id} (registered)",
                extra={
                    'grade_level': grade_level,
                    'search_query': search_query,
                    'student_count': total_students,
                    'available_space': available_space
                }
            )
            
            return JsonResponse({
                'status': 'success',
                'added_count': total_students,
                'message': f'Registered {total_students} students. Note: Only {available_space} spots available for enrollment.'
            })
        
        # Regular add students request
        student_ids = data.get('student_ids', [])
        
        if not student_ids:
            return JsonResponse({'error': 'No students specified'}, status=400)
        
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
class CourseListView(APIView):
    permission_classes = [AllowAny]
    
    @handle_exceptions
    @log_execution_time
    def get(self, request: HttpRequest) -> JsonResponse:
        """Handle GET requests for course listing"""
        print("\n=== CourseListView GET Request ===")
        print("Headers:", request.headers)
        print("Path:", request.path)
        print("Method:", request.method)
        print("=== End Request Info ===\n")
        
        cache_key = 'all_courses'
        courses_data = cache.get(cache_key)
        
        if courses_data is None:
            print("Cache miss - fetching courses from database")
            courses = Course.objects.all().order_by('code')
            courses_data = list(courses.values(
                'id', 'name', 'code', 'description', 'grade_level',
                'course_type', 'num_sections', 'max_students_per_section'
            ))
            cache.set(cache_key, courses_data, CACHE_TIMEOUT)
        else:
            print("Cache hit - using cached courses data")
        
        print(f"Retrieved {len(courses_data)} courses")
        response = JsonResponse({'courses': courses_data})
        response['Content-Type'] = 'application/json'
        print("\n=== Sending Response ===")
        print("Status: 200 OK")
        print("Content-Type:", response['Content-Type'])
        print("Data length:", len(courses_data))
        print("=== End Response Info ===\n")
        return response

    @handle_exceptions
    @log_execution_time
    def post(self, request: HttpRequest) -> JsonResponse:
        """Handle POST requests for creating new courses"""
        print("\n=== CourseListView POST Request ===")
        print("Headers:", request.headers)
        print("Path:", request.path)
        print("Method:", request.method)
        print("=== End Request Info ===\n")
        
        data = json.loads(request.body)
        
        try:
            course = Course.objects.create(
                name=data['name'],
                code=data['code'],
                description=data.get('description', ''),
                grade_level=data['grade_level'],
                course_type=data['course_type'],
                num_sections=data['num_sections'],
                max_students_per_section=data['max_students_per_section']
            )
            
            # Clear the cache
            cache.delete('all_courses')
            
            print(f"Created new course: {course.code}")
            response_data = {
                'id': course.id,
                'name': course.name,
                'code': course.code,
                'description': course.description,
                'grade_level': course.grade_level,
                'course_type': course.course_type,
                'num_sections': course.num_sections,
                'max_students_per_section': course.max_students_per_section
            }
            
            print("\n=== Sending Response ===")
            print("Status: 201 Created")
            print("Content-Type: application/json")
            print("Response data:", response_data)
            print("=== End Response Info ===\n")
            
            return JsonResponse(response_data, status=201)
            
        except KeyError as e:
            error_msg = f'Missing required field: {str(e)}'
            print("\n=== Error Response ===")
            print("Status: 400 Bad Request")
            print("Error:", error_msg)
            print("=== End Error Info ===\n")
            return JsonResponse({'error': error_msg}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class CourseGroupView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, group_id=None, *args, **kwargs):
        print("DEBUG: Received GET request for course groups")  # Debug log
        try:
            if group_id is not None:
                group = CourseGroup.objects.get(id=group_id)
                return JsonResponse({
                    'group': {
                        'id': group.id,
                        'name': group.name,
                        'courses': [
                            {
                                'id': course.id,
                                'name': course.name,
                                'code': course.code,
                                'grade_level': course.grade_level
                            }
                            for course in group.courses.all()
                        ]
                    }
                })
            else:
                groups = CourseGroup.objects.prefetch_related('courses').all()
                print(f"DEBUG: Found {groups.count()} groups")  # Debug log
                return JsonResponse({
                    'groups': [
                        {
                            'id': group.id,
                            'name': group.name,
                            'courses': [
                                {
                                    'id': course.id,
                                    'name': course.name,
                                    'code': course.code,
                                    'grade_level': course.grade_level
                                }
                                for course in group.courses.all()
                            ]
                        }
                        for group in groups
                    ]
                })
        except CourseGroup.DoesNotExist:
            return JsonResponse({'error': 'Group not found'}, status=404)
        except Exception as e:
            print(f"DEBUG: Error in CourseGroupView: {str(e)}")  # Debug log
            return JsonResponse({'error': str(e)}, status=500)

    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def post(self, request, group_id=None):
        data = json.loads(request.body)
        
        # Check if this is an "add filtered courses" request
        if data.get('add_filtered_students'):
            if not group_id:
                return JsonResponse({'error': 'Group ID is required'}, status=400)
            
            group = get_object_or_404(CourseGroup, id=group_id)
            grade_level = data.get('grade_level')
            search_query = data.get('search_query', '').strip()
            
            # Start with all available courses
            courses_query = Course.objects.all()
            
            # Exclude already added courses
            existing_course_ids = set(group.courses.values_list('id', flat=True))
            if existing_course_ids:
                courses_query = courses_query.exclude(id__in=existing_course_ids)
            
            # Apply grade level filter if specified
            if grade_level:
                courses_query = courses_query.filter(grade_level=grade_level)
            
            # Apply search filter if specified
            if search_query:
                courses_query = courses_query.filter(
                    Q(name__icontains=search_query) |
                    Q(code__icontains=search_query)
                )
            
            courses = courses_query.all()
            
            # Add the filtered courses to the group
            group.courses.add(*courses)
            
            logger.info(
                f"Added {courses.count()} filtered courses to group {group_id}",
                extra={
                    'grade_level': grade_level,
                    'search_query': search_query,
                    'course_count': courses.count()
                }
            )
            
            return JsonResponse({
                'status': 'success',
                'added_count': courses.count()
            })
        
        # Regular group update/create request
        if group_id:
            group = CourseGroup.objects.get(id=group_id)
            if 'name' in data:
                group.name = data['name']
            if 'course_ids' in data:
                group.courses.set(Course.objects.filter(id__in=data['course_ids']))
            group.save()
        else:
            group = CourseGroup.objects.create(name=data['name'])
            if 'course_ids' in data:
                group.courses.set(Course.objects.filter(id__in=data['course_ids']))
        
        return JsonResponse({
            'id': group.id,
            'name': group.name,
            'courses': [{
                'id': course.id,
                'name': course.name,
                'code': course.code,
                'grade_level': course.grade_level
            } for course in group.courses.all()]
        })

    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def delete(self, request, group_id):
        group = CourseGroup.objects.get(id=group_id)
        group.delete()
        return JsonResponse({'status': 'success'}) 