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
from ..models import Room, Section, Period, User
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
        except Room.DoesNotExist:
            logger.warning("Room not found", extra={'room_id': kwargs.get('room_id')})
            return JsonResponse({'error': 'Room not found'}, status=404)
        except ValidationError as e:
            logger.warning(
                "Validation error",
                extra={'errors': str(e), 'room_id': kwargs.get('room_id')}
            )
            return JsonResponse({'error': str(e)}, status=400)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON data received")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(
                f"Unexpected error: {str(e)}",
                exc_info=True,
                extra={'room_id': kwargs.get('room_id')}
            )
            return JsonResponse(
                {'error': 'An unexpected error occurred'},
                status=500
            )
    return wrapper

@method_decorator(csrf_exempt, name='dispatch')
class RoomView(View):
    def get_room_with_stats(self, room_id: int, period_id: Optional[int] = None) -> Dict[str, Any]:
        """Get room with related statistics"""
        cache_key = f'room_with_stats_{room_id}_{period_id or "all"}'
        room_data = cache.get(cache_key)
        
        if room_data is None:
            room = get_object_or_404(Room, id=room_id)
            sections = Section.objects.filter(room=room)
            
            if period_id:
                sections = sections.filter(period_id=period_id)
            
            sections = sections.select_related(
                'course', 'period'
            ).prefetch_related(
                Prefetch(
                    'students',
                    queryset=User.objects.only('id')
                )
            )
            
            schedule_stats = room.get_schedule_stats()
            
            room_data = {
                'id': room.id,
                'name': room.name,
                'capacity': room.capacity,
                'description': room.description,
                'features': {
                    'is_science_lab': room.is_science_lab,
                    'is_art_room': room.is_art_room,
                    'is_gym': room.is_gym
                },
                'sections': [
                    {
                        'id': section.id,
                        'name': section.name,
                        'course': {
                            'id': section.course.id,
                            'name': section.course.name,
                            'code': section.course.code
                        },
                        'period': {
                            'id': section.period.id,
                            'name': section.period.name
                        } if section.period else None,
                        'student_count': section.students.count(),
                        'is_at_capacity': section.is_at_capacity(),
                        'available_space': section.get_available_space()
                    }
                    for section in sections
                ],
                'stats': schedule_stats
            }
            
            if period_id:
                room_data['period_stats'] = {
                    'is_at_capacity': room.is_at_capacity(period_id),
                    'available_space': room.get_available_space(period_id),
                    'has_conflict': room.has_schedule_conflict(period_id)
                }
            
            cache.set(cache_key, room_data, CACHE_TIMEOUT)
        
        return room_data

    @handle_exceptions
    @log_execution_time
    def get(self, request: HttpRequest, room_id: int) -> JsonResponse:
        """Handle GET requests for room details"""
        period_id = request.GET.get('period_id')
        if period_id:
            try:
                period_id = int(period_id)
            except ValueError:
                return JsonResponse({'error': 'Invalid period ID'}, status=400)
        
        room_data = self.get_room_with_stats(room_id, period_id)
        return JsonResponse(room_data)

    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def post(self, request: HttpRequest, room_id: int) -> JsonResponse:
        """Handle POST requests for modifying room details"""
        room = get_object_or_404(Room, id=room_id)
        data = json.loads(request.body)
        
        # Update fields if provided
        if 'name' in data:
            room.name = data['name']
        
        if 'capacity' in data:
            # Validate that new capacity can accommodate current sections
            max_section_size = Section.objects.filter(room=room).annotate(
                student_count=Count('students')
            ).order_by('-student_count').values_list('student_count', flat=True).first() or 0
            
            if data['capacity'] < max_section_size:
                return JsonResponse({
                    'error': f'New capacity ({data["capacity"]}) is less than current maximum section size ({max_section_size})'
                }, status=400)
            
            room.capacity = data['capacity']
        
        if 'description' in data:
            room.description = data['description']
        
        if 'is_science_lab' in data:
            room.is_science_lab = data['is_science_lab']
        
        if 'is_art_room' in data:
            room.is_art_room = data['is_art_room']
        
        if 'is_gym' in data:
            room.is_gym = data['is_gym']
        
        # Validate and save
        try:
            room.full_clean()
            room.save()
            
            # Clear cache for all period-specific data
            cache.delete_pattern(f'room_with_stats_{room_id}_*')
            cache.delete('all_rooms_list')
            
            logger.info(
                f"Updated room: {room.name}",
                extra={
                    'room_id': room.id,
                    'changes': {k: v for k, v in data.items() if k != 'description'}
                }
            )
            
            return JsonResponse({
                'status': 'success',
                'room': self.get_room_with_stats(room_id)
            })
            
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class RoomListView(View):
    @handle_exceptions
    @log_execution_time
    def get(self, request: HttpRequest) -> JsonResponse:
        """Handle GET requests for room lists"""
        period_id = request.GET.get('period_id')
        min_capacity = request.GET.get('min_capacity', 1)
        room_type = request.GET.get('room_type')
        
        try:
            min_capacity = int(min_capacity)
            if period_id:
                period_id = int(period_id)
        except ValueError:
            return JsonResponse({'error': 'Invalid numeric parameter'}, status=400)
        
        cache_key = f'rooms_list_{period_id or "all"}_{min_capacity}_{room_type or "all"}'
        rooms_data = cache.get(cache_key)
        
        if rooms_data is None:
            # Get base queryset
            if period_id:
                rooms = Room.get_available_rooms(period_id, min_capacity)
            else:
                rooms = Room.objects.filter(capacity__gte=min_capacity)
            
            # Apply room type filter if specified
            if room_type:
                try:
                    rooms = Room.get_specialized_rooms(room_type)
                except ValueError:
                    return JsonResponse({'error': 'Invalid room type'}, status=400)
            
            # Annotate with section counts
            rooms = rooms.annotate(
                sections_count=Count('sections')
            ).order_by('name')
            
            rooms_data = []
            for room in rooms:
                schedule_stats = room.get_schedule_stats()
                rooms_data.append({
                    'id': room.id,
                    'name': room.name,
                    'capacity': room.capacity,
                    'description': room.description,
                    'features': {
                        'is_science_lab': room.is_science_lab,
                        'is_art_room': room.is_art_room,
                        'is_gym': room.is_gym
                    },
                    'sections_count': room.sections_count,
                    'stats': schedule_stats
                })
            
            cache.set(cache_key, rooms_data, CACHE_TIMEOUT)
        
        return JsonResponse({
            'rooms': rooms_data,
            'filters': {
                'period_id': period_id,
                'min_capacity': min_capacity,
                'room_type': room_type
            }
        })

    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def post(self, request: HttpRequest) -> JsonResponse:
        """Handle POST requests for creating new rooms"""
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['name', 'capacity']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return JsonResponse(
                {'error': f'Missing required fields: {", ".join(missing_fields)}'},
                status=400
            )
        
        # Create room
        try:
            room = Room.objects.create(
                name=data['name'],
                capacity=data['capacity'],
                description=data.get('description', ''),
                is_science_lab=data.get('is_science_lab', False),
                is_art_room=data.get('is_art_room', False),
                is_gym=data.get('is_gym', False)
            )
            
            # Clear cache
            cache.delete_pattern('rooms_list_*')
            
            logger.info(
                f"Created new room: {room.name}",
                extra={
                    'room_id': room.id,
                    'room_data': {k: v for k, v in data.items() if k != 'description'}
                }
            )
            
            return JsonResponse({
                'status': 'success',
                'room': self.get_room_with_stats(room.id)
            })
            
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400) 