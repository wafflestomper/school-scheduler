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
from ..models import Section, Course, User, Period, Room
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
        except Section.DoesNotExist:
            logger.warning("Section not found", extra={'section_id': kwargs.get('section_id')})
            return JsonResponse({'error': 'Section not found'}, status=404)
        except ValidationError as e:
            logger.warning(
                "Validation error",
                extra={'errors': str(e), 'section_id': kwargs.get('section_id')}
            )
            return JsonResponse({'error': str(e)}, status=400)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON data received")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(
                f"Unexpected error: {str(e)}",
                exc_info=True,
                extra={'section_id': kwargs.get('section_id')}
            )
            return JsonResponse(
                {'error': 'An unexpected error occurred'},
                status=500
            )
    return wrapper

@method_decorator(csrf_exempt, name='dispatch')
class SectionView(View):
    def get_section_with_related(self, section_id: int) -> Section:
        """Get section with all related data prefetched"""
        cache_key = f'section_with_related_{section_id}'
        section = cache.get(cache_key)
        
        if section is None:
            section = Section.objects.select_related(
                'course', 'teacher', 'period', 'room'
            ).prefetch_related(
                Prefetch(
                    'students',
                    queryset=User.objects.only(
                        'id', 'first_name', 'last_name', 'grade_level'
                    )
                )
            ).get(id=section_id)
            cache.set(cache_key, section, CACHE_TIMEOUT)
        
        return section

    @handle_exceptions
    @log_execution_time
    def get(self, request: HttpRequest, section_id: int) -> JsonResponse:
        """Handle GET requests for section details"""
        section = self.get_section_with_related(section_id)
        
        # Get student data
        students_data = list(section.students.values(
            'id', 'first_name', 'last_name', 'grade_level'
        ))
        
        response_data = {
            'id': section.id,
            'name': section.name,
            'course': {
                'id': section.course.id,
                'name': section.course.name,
                'code': section.course.code,
                'grade_level': section.course.grade_level,
                'total_capacity': section.course.get_total_capacity(),
            },
            'teacher': {
                'id': section.teacher.id,
                'name': f"{section.teacher.first_name} {section.teacher.last_name}"
            } if section.teacher else None,
            'period': {
                'id': section.period.id,
                'name': section.period.name
            } if section.period else None,
            'room': {
                'id': section.room.id,
                'name': section.room.name,
                'capacity': section.room.capacity
            } if section.room else None,
            'students': students_data,
            'is_at_capacity': section.is_at_capacity(),
            'available_space': section.get_available_space(),
            'student_stats': section.get_student_stats()
        }
        
        return JsonResponse(response_data)

    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def post(self, request: HttpRequest, section_id: int) -> JsonResponse:
        """Handle POST requests for modifying section details"""
        section = self.get_section_with_related(section_id)
        data = json.loads(request.body)
        
        # Update teacher if provided
        if 'teacher_id' in data:
            teacher = get_object_or_404(User, id=data['teacher_id'], role='TEACHER')
            
            # Check for schedule conflicts
            if section.period and Section.objects.filter(
                teacher=teacher,
                period=section.period
            ).exclude(id=section.id).exists():
                return JsonResponse(
                    {'error': 'Teacher has a schedule conflict with this period'},
                    status=400
                )
            
            section.teacher = teacher
            logger.info(f"Updated teacher for section {section_id} to {teacher.id}")
        
        # Update period if provided
        if 'period_id' in data:
            period = get_object_or_404(Period, id=data['period_id'])
            
            # Check for conflicts
            if section.has_schedule_conflict(period.id):
                return JsonResponse(
                    {'error': 'Schedule conflict detected'},
                    status=400
                )
            
            # Check for student conflicts
            conflicting_students = section.get_student_conflicts(period.id)
            if conflicting_students:
                return JsonResponse({
                    'error': 'Some students have schedule conflicts',
                    'conflicting_student_ids': conflicting_students
                }, status=400)
            
            section.period = period
            logger.info(f"Updated period for section {section_id} to {period.id}")
        
        # Update room if provided
        if 'room_id' in data:
            room = get_object_or_404(Room, id=data['room_id'])
            
            # Check room capacity
            if room.capacity < section.students.count():
                return JsonResponse(
                    {'error': 'Room capacity is less than current student count'},
                    status=400
                )
            
            # Check for room conflicts
            if section.period and Section.objects.filter(
                room=room,
                period=section.period
            ).exclude(id=section.id).exists():
                return JsonResponse(
                    {'error': 'Room is already scheduled for this period'},
                    status=400
                )
            
            section.room = room
            logger.info(f"Updated room for section {section_id} to {room.id}")
        
        # Update students if provided
        if 'student_ids' in data:
            student_ids = data['student_ids']
            if not isinstance(student_ids, list):
                return JsonResponse({'error': 'student_ids must be a list'}, status=400)
            
            # Validate student capacity
            if len(student_ids) > section.course.max_students_per_section:
                return JsonResponse(
                    {'error': 'Adding these students would exceed section capacity'},
                    status=400
                )
            
            # Get and validate students
            students = User.objects.filter(id__in=student_ids, role='STUDENT')
            if len(students) != len(student_ids):
                return JsonResponse({'error': 'Some student IDs are invalid'}, status=400)
            
            # Check for student schedule conflicts
            if section.period:
                conflicts = []
                for student in students:
                    if student.assigned_sections.filter(
                        period=section.period
                    ).exclude(id=section.id).exists():
                        conflicts.append(student.id)
                
                if conflicts:
                    return JsonResponse({
                        'error': 'Some students have schedule conflicts',
                        'conflicting_student_ids': conflicts
                    }, status=400)
            
            # Update students
            section.students.set(students)
            logger.info(
                f"Updated students for section {section_id}",
                extra={'student_count': len(students)}
            )
        
        section.save()
        
        # Clear cache
        cache.delete(f'section_with_related_{section_id}')
        
        return JsonResponse({'status': 'success'})

@method_decorator(csrf_exempt, name='dispatch')
class SectionListView(View):
    @handle_exceptions
    @log_execution_time
    def get(self, request: HttpRequest) -> JsonResponse:
        """Handle GET requests for section lists"""
        cache_key = 'all_sections_list'
        sections_data = cache.get(cache_key)
        
        if sections_data is None:
            sections = Section.objects.select_related(
                'course', 'teacher', 'period', 'room'
            ).prefetch_related(
                Prefetch(
                    'students',
                    queryset=User.objects.only('id')
                )
            ).annotate(
                student_count=Count('students')
            )
            
            sections_data = []
            for section in sections:
                sections_data.append({
                    'id': section.id,
                    'name': section.name,
                    'course': {
                        'id': section.course.id,
                        'name': section.course.name,
                        'code': section.course.code,
                        'grade_level': section.course.grade_level
                    },
                    'teacher': {
                        'id': section.teacher.id,
                        'name': f"{section.teacher.first_name} {section.teacher.last_name}"
                    } if section.teacher else None,
                    'period': {
                        'id': section.period.id,
                        'name': section.period.name
                    } if section.period else None,
                    'room': {
                        'id': section.room.id,
                        'name': section.room.name,
                        'capacity': section.room.capacity
                    } if section.room else None,
                    'student_count': section.student_count,
                    'is_at_capacity': section.is_at_capacity(),
                    'available_space': section.get_available_space()
                })
            
            cache.set(cache_key, sections_data, CACHE_TIMEOUT)
        
        return JsonResponse({'sections': sections_data})

    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def post(self, request: HttpRequest) -> JsonResponse:
        """Handle POST requests for creating new sections"""
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['course_id', 'section_number']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return JsonResponse(
                {'error': f'Missing required fields: {", ".join(missing_fields)}'},
                status=400
            )
        
        # Get course and validate section number
        course = get_object_or_404(Course, id=data['course_id'])
        if data['section_number'] > course.num_sections:
            return JsonResponse(
                {'error': 'Section number exceeds course section limit'},
                status=400
            )
        
        # Check for duplicate section number
        if Section.objects.filter(
            course=course,
            section_number=data['section_number']
        ).exists():
            return JsonResponse(
                {'error': 'Section number already exists for this course'},
                status=400
            )
        
        # Validate teacher if provided
        teacher = None
        if 'teacher_id' in data:
            teacher = get_object_or_404(User, id=data['teacher_id'], role='TEACHER')
            
            # Check teacher schedule if period is also provided
            if 'period_id' in data:
                period = get_object_or_404(Period, id=data['period_id'])
                if Section.objects.filter(teacher=teacher, period=period).exists():
                    return JsonResponse(
                        {'error': 'Teacher has a schedule conflict with this period'},
                        status=400
                    )
        
        # Validate room if provided
        room = None
        if 'room_id' in data:
            room = get_object_or_404(Room, id=data['room_id'])
            
            # Check room schedule if period is also provided
            if 'period_id' in data:
                period = get_object_or_404(Period, id=data['period_id'])
                if Section.objects.filter(room=room, period=period).exists():
                    return JsonResponse(
                        {'error': 'Room is already scheduled for this period'},
                        status=400
                    )
        
        # Create section
        try:
            section = Section.objects.create(
                course=course,
                section_number=data['section_number'],
                teacher=teacher,
                period=get_object_or_404(Period, id=data['period_id']) if 'period_id' in data else None,
                room=room
            )
            
            # Add students if provided
            if 'student_ids' in data:
                students = User.objects.filter(
                    id__in=data['student_ids'],
                    role='STUDENT'
                )
                section.students.set(students)
            
            # Clear cache
            cache.delete('all_sections_list')
            
            logger.info(
                f"Created new section: {section.name}",
                extra={
                    'section_id': section.id,
                    'course_id': course.id,
                    'section_data': data
                }
            )
            
            return JsonResponse({
                'status': 'success',
                'section_id': section.id
            })
            
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400) 