from __future__ import annotations
from typing import Dict, Any, List, Optional
from django.http import JsonResponse, HttpRequest
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Prefetch
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Schedule, StudentPreference, Course, User, Period, Room, Section
import json
import logging
from functools import wraps
from time import time
from ..scheduling.basic_scheduler import distribute_pe6_students

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
        except (Schedule.DoesNotExist, StudentPreference.DoesNotExist):
            logger.warning("Schedule/Preference not found", extra={'id': kwargs.get('id')})
            return JsonResponse({'error': 'Schedule/Preference not found'}, status=404)
        except ValidationError as e:
            logger.warning(
                "Validation error",
                extra={'errors': str(e), 'id': kwargs.get('id')}
            )
            return JsonResponse({'error': str(e)}, status=400)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON data received")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(
                f"Unexpected error: {str(e)}",
                exc_info=True,
                extra={'id': kwargs.get('id')}
            )
            return JsonResponse(
                {'error': 'An unexpected error occurred'},
                status=500
            )
    return wrapper

@method_decorator(csrf_exempt, name='dispatch')
class ScheduleView(View):
    def get_schedule_with_related(self, schedule_id: int) -> Schedule:
        """Get schedule with all related data prefetched"""
        cache_key = f'schedule_with_related_{schedule_id}'
        schedule = cache.get(cache_key)
        
        if schedule is None:
            schedule = Schedule.objects.select_related(
                'course', 'period', 'room', 'configuration'
            ).prefetch_related(
                Prefetch(
                    'students',
                    queryset=User.objects.only(
                        'id', 'first_name', 'last_name', 'grade_level'
                    )
                )
            ).get(id=schedule_id)
            cache.set(cache_key, schedule, CACHE_TIMEOUT)
        
        return schedule

    @handle_exceptions
    @log_execution_time
    def get(self, request: HttpRequest, schedule_id: int) -> JsonResponse:
        """Handle GET requests for schedule details"""
        schedule = self.get_schedule_with_related(schedule_id)
        
        # Get student data
        students_data = list(schedule.students.values(
            'id', 'first_name', 'last_name', 'grade_level'
        ))
        
        response_data = {
            'id': schedule.id,
            'course': {
                'id': schedule.course.id,
                'name': schedule.course.name,
                'code': schedule.course.code
            },
            'period': {
                'id': schedule.period.id,
                'name': schedule.period.name,
                'start_time': schedule.period.start_time.strftime('%H:%M'),
                'end_time': schedule.period.end_time.strftime('%H:%M')
            },
            'room': {
                'id': schedule.room.id,
                'name': schedule.room.name,
                'capacity': schedule.room.capacity
            },
            'semester': schedule.semester,
            'year': schedule.year,
            'students': students_data,
            'is_at_capacity': schedule.is_at_capacity(),
            'configuration': {
                'id': schedule.configuration.id,
                'name': schedule.configuration.name,
                'max_class_size': schedule.configuration.max_class_size
            } if schedule.configuration else None
        }
        
        return JsonResponse(response_data)

    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def post(self, request: HttpRequest, schedule_id: int) -> JsonResponse:
        """Handle POST requests for modifying schedule details"""
        schedule = self.get_schedule_with_related(schedule_id)
        data = json.loads(request.body)
        
        # Update fields if provided
        if 'period_id' in data:
            period = get_object_or_404(Period, id=data['period_id'])
            
            # Check for conflicts
            if Schedule.objects.filter(
                Q(room=schedule.room) | Q(course=schedule.course),
                period=period,
                semester=schedule.semester,
                year=schedule.year
            ).exclude(id=schedule.id).exists():
                return JsonResponse(
                    {'error': 'Schedule conflict detected'},
                    status=400
                )
            
            schedule.period = period
        
        if 'room_id' in data:
            room = get_object_or_404(Room, id=data['room_id'])
            
            # Check room capacity
            if room.capacity < schedule.students.count():
                return JsonResponse(
                    {'error': 'Room capacity is less than current student count'},
                    status=400
                )
            
            # Check for conflicts
            if Schedule.objects.filter(
                room=room,
                period=schedule.period,
                semester=schedule.semester,
                year=schedule.year
            ).exclude(id=schedule.id).exists():
                return JsonResponse(
                    {'error': 'Room is already scheduled for this period'},
                    status=400
                )
            
            schedule.room = room
        
        if 'student_ids' in data:
            students = User.objects.filter(
                id__in=data['student_ids'],
                role='STUDENT'
            )
            
            # Check capacity
            if len(students) > schedule.configuration.max_class_size:
                return JsonResponse(
                    {'error': 'Adding these students would exceed class capacity'},
                    status=400
                )
            
            schedule.students.set(students)
        
        # Validate and save
        try:
            schedule.full_clean()
            schedule.save()
            
            # Clear cache
            cache.delete(f'schedule_with_related_{schedule_id}')
            cache.delete('all_schedules_list')
            
            logger.info(
                f"Updated schedule: {schedule}",
                extra={'schedule_id': schedule.id}
            )
            
            return JsonResponse({'status': 'success'})
            
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class ScheduleListView(View):
    @handle_exceptions
    @log_execution_time
    def get(self, request: HttpRequest) -> JsonResponse:
        """Handle GET requests for schedule lists"""
        cache_key = 'all_schedules_list'
        schedules_data = cache.get(cache_key)
        
        if schedules_data is None:
            schedules = Schedule.objects.select_related(
                'course', 'period', 'room', 'configuration'
            ).prefetch_related(
                Prefetch(
                    'students',
                    queryset=User.objects.only('id')
                )
            ).annotate(
                student_count=Count('students')
            )
            
            schedules_data = []
            for schedule in schedules:
                schedules_data.append({
                    'id': schedule.id,
                    'course': {
                        'id': schedule.course.id,
                        'name': schedule.course.name,
                        'code': schedule.course.code
                    },
                    'period': {
                        'id': schedule.period.id,
                        'name': schedule.period.name
                    },
                    'room': {
                        'id': schedule.room.id,
                        'name': schedule.room.name,
                        'capacity': schedule.room.capacity
                    },
                    'semester': schedule.semester,
                    'year': schedule.year,
                    'student_count': schedule.student_count,
                    'is_at_capacity': schedule.is_at_capacity()
                })
            
            cache.set(cache_key, schedules_data, CACHE_TIMEOUT)
        
        return JsonResponse({'schedules': schedules_data})

    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def post(self, request: HttpRequest) -> JsonResponse:
        """Handle POST requests for creating new schedules"""
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['course_id', 'period_id', 'room_id', 'semester', 'year']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return JsonResponse(
                {'error': f'Missing required fields: {", ".join(missing_fields)}'},
                status=400
            )
        
        # Get related objects
        course = get_object_or_404(Course, id=data['course_id'])
        period = get_object_or_404(Period, id=data['period_id'])
        room = get_object_or_404(Room, id=data['room_id'])
        
        # Check for conflicts
        if Schedule.objects.filter(
            Q(room=room) | Q(course=course),
            period=period,
            semester=data['semester'],
            year=data['year']
        ).exists():
            return JsonResponse(
                {'error': 'Schedule conflict detected'},
                status=400
            )
        
        # Create schedule
        try:
            schedule = Schedule.objects.create(
                course=course,
                period=period,
                room=room,
                semester=data['semester'],
                year=data['year']
            )
            
            # Add students if provided
            if 'student_ids' in data:
                students = User.objects.filter(
                    id__in=data['student_ids'],
                    role='STUDENT'
                )
                schedule.students.set(students)
            
            # Clear cache
            cache.delete('all_schedules_list')
            
            logger.info(
                f"Created new schedule: {schedule}",
                extra={'schedule_id': schedule.id}
            )
            
            return JsonResponse({
                'status': 'success',
                'schedule_id': schedule.id
            })
            
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class StudentPreferenceView(View):
    @handle_exceptions
    @log_execution_time
    def get(self, request: HttpRequest, student_id: int) -> JsonResponse:
        """Handle GET requests for student preferences"""
        cache_key = f'student_preferences_{student_id}'
        preferences_data = cache.get(cache_key)
        
        if preferences_data is None:
            preferences = StudentPreference.objects.filter(
                student_id=student_id
            ).select_related('course').order_by('preference_level')
            
            preferences_data = []
            for pref in preferences:
                preferences_data.append({
                    'id': pref.id,
                    'course': {
                        'id': pref.course.id,
                        'name': pref.course.name,
                        'code': pref.course.code
                    },
                    'preference_level': pref.preference_level,
                    'semester': pref.semester,
                    'year': pref.year
                })
            
            cache.set(cache_key, preferences_data, CACHE_TIMEOUT)
        
        return JsonResponse({'preferences': preferences_data})

    @transaction.atomic
    @handle_exceptions
    @log_execution_time
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
        
        try:
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
                'preference_id': preference.id,
                'created': created
            })
            
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class PE6DistributionView(View):
    def post(self, request):
        """
        Endpoint to trigger PE6 student distribution across sections.
        """
        try:
            results = distribute_pe6_students()
            return JsonResponse(results)
        except Exception as e:
            logger.error(f"Error in PE6DistributionView: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def get(self, request):
        """
        Returns current PE6 distribution status.
        """
        try:
            pe6_course = Course.objects.filter(code='PE6').first()
            if not pe6_course:
                return JsonResponse({'error': 'PE6 course not found'}, status=404)

            sections = Section.objects.filter(course=pe6_course)
            distribution = [
                {
                    'section_name': section.name,
                    'student_count': section.students.count(),
                    'students': list(section.students.values('id', 'first_name', 'last_name'))
                }
                for section in sections
            ]

            return JsonResponse({
                'course_name': pe6_course.name,
                'total_students': pe6_course.students.count(),
                'num_sections': sections.count(),
                'distribution': distribution
            })

        except Exception as e:
            logger.error(f"Error in PE6DistributionView GET: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500) 