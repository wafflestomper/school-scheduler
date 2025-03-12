from typing import Dict, Any, List, Optional
from django.http import JsonResponse, HttpRequest
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Prefetch, Count
from django.core.cache import cache
import json
import logging
from functools import wraps
from ..models import StudentPreference, Course, User
from ..choices import PreferenceLevels

logger = logging.getLogger(__name__)
CACHE_TIMEOUT = 300  # 5 minutes

def log_execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(
            f"{func.__name__} took {end_time - start_time:.2f} seconds to execute",
            extra={
                'execution_time': end_time - start_time,
                'view_method': func.__name__
            }
        )
        return result
    return wrapper

def handle_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.error(f"Validation error in {func.__name__}: {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {func.__name__}: {str(e)}")
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return JsonResponse({"error": "Internal server error"}, status=500)
    return wrapper

@method_decorator(csrf_exempt, name='dispatch')
class StudentPreferenceView(View):
    def get_preferences_with_stats(self, student_id: int) -> Dict[str, Any]:
        """Get student preferences with course details and statistics"""
        cache_key = f'student_preferences_{student_id}'
        data = cache.get(cache_key)
        if data is not None:
            return data

        preferences = StudentPreference.objects.filter(
            student_id=student_id
        ).select_related(
            'course'
        ).prefetch_related(
            Prefetch(
                'course__sections',
                queryset=Course.objects.only('id')
            )
        ).order_by('preference_level')

        data = {
            'preferences': [
                {
                    'id': pref.id,
                    'course': {
                        'id': pref.course.id,
                        'name': pref.course.name,
                        'code': pref.course.code,
                        'available_space': pref.course.get_available_space(),
                        'sections_count': pref.course.sections.count()
                    },
                    'preference_level': pref.preference_level,
                    'semester': pref.semester,
                    'year': pref.year
                }
                for pref in preferences
            ],
            'stats': {
                'total_preferences': len(preferences),
                'by_level': {
                    level: preferences.filter(preference_level=level).count()
                    for level, _ in PreferenceLevels.CHOICES
                }
            }
        }

        cache.set(cache_key, data, CACHE_TIMEOUT)
        return data

    @log_execution_time
    @handle_exceptions
    def get(self, request: HttpRequest, student_id: int) -> JsonResponse:
        """Handle GET requests for student preferences"""
        data = self.get_preferences_with_stats(student_id)
        return JsonResponse(data)

    @log_execution_time
    @handle_exceptions
    def post(self, request: HttpRequest, student_id: int) -> JsonResponse:
        """Handle POST requests for updating student preferences"""
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['course_id', 'preference_level', 'semester', 'year']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return JsonResponse(
                {'error': f'Missing required fields: {", ".join(missing_fields)}'},
                status=400
            )

        # Validate preference level
        if data['preference_level'] not in dict(PreferenceLevels.CHOICES):
            return JsonResponse(
                {'error': 'Invalid preference level'},
                status=400
            )

        with transaction.atomic():
            try:
                # Check if student exists and is a student
                student = get_object_or_404(
                    User.objects.filter(role='STUDENT'),
                    id=student_id
                )

                # Check if course exists and has available space
                course = get_object_or_404(Course, id=data['course_id'])
                if course.get_available_space() <= 0:
                    return JsonResponse(
                        {'error': 'Course is at capacity'},
                        status=400
                    )

                # Check if student is in the appropriate grade level
                if student.grade_level != course.grade_level:
                    return JsonResponse(
                        {'error': 'Course is not available for student\'s grade level'},
                        status=400
                    )

                # Update or create preference
                preference, created = StudentPreference.objects.update_or_create(
                    student_id=student_id,
                    course_id=data['course_id'],
                    semester=data['semester'],
                    year=data['year'],
                    defaults={'preference_level': data['preference_level']}
                )

                # Clear cache
                cache.delete(f'student_preferences_{student_id}')

                logger.info(
                    f"{'Created' if created else 'Updated'} student preference",
                    extra={
                        'student_id': student_id,
                        'course_id': data['course_id'],
                        'preference_level': data['preference_level']
                    }
                )

                return JsonResponse({
                    'status': 'success',
                    'message': f"Successfully {'created' if created else 'updated'} preference",
                    'preference': {
                        'id': preference.id,
                        'course': {
                            'id': course.id,
                            'name': course.name,
                            'code': course.code
                        },
                        'preference_level': preference.preference_level,
                        'semester': preference.semester,
                        'year': preference.year
                    }
                })

            except ValidationError as e:
                return JsonResponse({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class StudentPreferenceListView(View):
    @log_execution_time
    @handle_exceptions
    def get(self, request: HttpRequest) -> JsonResponse:
        """Handle GET requests for listing all student preferences"""
        cache_key = 'all_student_preferences'
        data = cache.get(cache_key)

        if data is None:
            preferences = StudentPreference.objects.select_related(
                'student', 'course'
            ).prefetch_related(
                Prefetch(
                    'course__sections',
                    queryset=Course.objects.only('id')
                )
            ).order_by('student__last_name', 'student__first_name', 'preference_level')

            data = {
                'preferences': [
                    {
                        'id': pref.id,
                        'student': {
                            'id': pref.student.id,
                            'name': f"{pref.student.first_name} {pref.student.last_name}",
                            'grade_level': pref.student.grade_level
                        },
                        'course': {
                            'id': pref.course.id,
                            'name': pref.course.name,
                            'code': pref.course.code,
                            'available_space': pref.course.get_available_space(),
                            'sections_count': pref.course.sections.count()
                        },
                        'preference_level': pref.preference_level,
                        'semester': pref.semester,
                        'year': pref.year
                    }
                    for pref in preferences
                ],
                'stats': {
                    'total_preferences': preferences.count(),
                    'by_level': {
                        level: preferences.filter(preference_level=level).count()
                        for level, _ in PreferenceLevels.CHOICES
                    },
                    'by_grade': {
                        grade: preferences.filter(student__grade_level=grade).count()
                        for grade in range(6, 13)  # Grades 6-12
                    }
                }
            }
            cache.set(cache_key, data, CACHE_TIMEOUT)

        return JsonResponse(data)

    @log_execution_time
    @handle_exceptions
    def post(self, request: HttpRequest) -> JsonResponse:
        """Handle POST requests for bulk creating student preferences"""
        data = json.loads(request.body)
        
        if not isinstance(data, list):
            return JsonResponse(
                {'error': 'Expected a list of preferences'},
                status=400
            )

        created_preferences = []
        errors = []

        with transaction.atomic():
            for pref_data in data:
                try:
                    # Validate required fields
                    required_fields = ['student_id', 'course_id', 'preference_level', 'semester', 'year']
                    missing_fields = [field for field in required_fields if field not in pref_data]
                    if missing_fields:
                        errors.append({
                            'data': pref_data,
                            'error': f'Missing required fields: {", ".join(missing_fields)}'
                        })
                        continue

                    # Validate preference level
                    if pref_data['preference_level'] not in dict(PreferenceLevels.CHOICES):
                        errors.append({
                            'data': pref_data,
                            'error': 'Invalid preference level'
                        })
                        continue

                    # Check if student exists and is a student
                    student = get_object_or_404(
                        User.objects.filter(role='STUDENT'),
                        id=pref_data['student_id']
                    )

                    # Check if course exists and has available space
                    course = get_object_or_404(Course, id=pref_data['course_id'])
                    if course.get_available_space() <= 0:
                        errors.append({
                            'data': pref_data,
                            'error': 'Course is at capacity'
                        })
                        continue

                    # Check if student is in the appropriate grade level
                    if student.grade_level != course.grade_level:
                        errors.append({
                            'data': pref_data,
                            'error': 'Course is not available for student\'s grade level'
                        })
                        continue

                    # Create preference
                    preference = StudentPreference.objects.create(
                        student_id=pref_data['student_id'],
                        course_id=pref_data['course_id'],
                        preference_level=pref_data['preference_level'],
                        semester=pref_data['semester'],
                        year=pref_data['year']
                    )

                    created_preferences.append({
                        'id': preference.id,
                        'student_id': student.id,
                        'course_id': course.id,
                        'preference_level': preference.preference_level,
                        'semester': preference.semester,
                        'year': preference.year
                    })

                except ValidationError as e:
                    errors.append({
                        'data': pref_data,
                        'error': str(e)
                    })

        # Clear cache for affected students
        student_ids = {pref['student_id'] for pref in created_preferences}
        for student_id in student_ids:
            cache.delete(f'student_preferences_{student_id}')
        cache.delete('all_student_preferences')

        return JsonResponse({
            'status': 'success',
            'created_count': len(created_preferences),
            'error_count': len(errors),
            'created_preferences': created_preferences,
            'errors': errors
        }) 