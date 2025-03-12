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
from ..models import StudentGroup, SiblingGroup, User

logger = logging.getLogger(__name__)
CACHE_TIMEOUT = 300  # 5 minutes

def log_execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"{func.__name__} took {end_time - start_time:.2f} seconds to execute")
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
class StudentGroupView(View):
    def get_group_with_stats(self, group_id: int) -> Dict[str, Any]:
        cache_key = f'student_group_{group_id}'
        data = cache.get(cache_key)
        if data is not None:
            return data

        group = get_object_or_404(StudentGroup.objects.select_related(), id=group_id)
        students = group.students.select_related().all()
        
        data = {
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'priority': group.priority,
            'student_count': len(students),
            'students': [
                {
                    'id': student.id,
                    'name': f"{student.first_name} {student.last_name}",
                    'grade_level': student.grade_level
                }
                for student in students
            ]
        }
        
        cache.set(cache_key, data, CACHE_TIMEOUT)
        return data

    @log_execution_time
    @handle_exceptions
    def get(self, request: HttpRequest, group_id: Optional[int] = None) -> JsonResponse:
        if group_id:
            data = self.get_group_with_stats(group_id)
        else:
            groups = StudentGroup.objects.prefetch_related('students').all()
            data = [
                {
                    'id': group.id,
                    'name': group.name,
                    'description': group.description,
                    'priority': group.priority,
                    'student_count': group.students.count()
                }
                for group in groups
            ]
        return JsonResponse(data, safe=False)

    @log_execution_time
    @handle_exceptions
    def post(self, request: HttpRequest, group_id: Optional[int] = None) -> JsonResponse:
        data = json.loads(request.body)
        
        with transaction.atomic():
            if group_id:
                group = get_object_or_404(StudentGroup, id=group_id)
                group.name = data.get('name', group.name)
                group.description = data.get('description', group.description)
                group.priority = data.get('priority', group.priority)
            else:
                group = StudentGroup(
                    name=data['name'],
                    description=data.get('description', ''),
                    priority=data.get('priority', 3)
                )
            
            group.full_clean()
            group.save()

            if 'student_ids' in data:
                students = User.objects.filter(
                    id__in=data['student_ids'],
                    role='STUDENT'
                )
                group.students.set(students)

            cache.delete(f'student_group_{group.id}')
            
            return JsonResponse({
                'message': 'Student group updated successfully',
                'group': self.get_group_with_stats(group.id)
            })

@method_decorator(csrf_exempt, name='dispatch')
class SiblingGroupView(View):
    def get_group_with_stats(self, group_id: int) -> Dict[str, Any]:
        cache_key = f'sibling_group_{group_id}'
        data = cache.get(cache_key)
        if data is not None:
            return data

        group = get_object_or_404(SiblingGroup.objects.select_related(), id=group_id)
        students = group.students.select_related().all()
        
        data = {
            'id': group.id,
            'name': group.name,
            'student_count': len(students),
            'students': [
                {
                    'id': student.id,
                    'name': f"{student.first_name} {student.last_name}",
                    'grade_level': student.grade_level
                }
                for student in students
            ]
        }
        
        cache.set(cache_key, data, CACHE_TIMEOUT)
        return data

    @log_execution_time
    @handle_exceptions
    def get(self, request: HttpRequest, group_id: Optional[int] = None) -> JsonResponse:
        if group_id:
            data = self.get_group_with_stats(group_id)
        else:
            groups = SiblingGroup.objects.prefetch_related('students').all()
            data = [
                {
                    'id': group.id,
                    'name': group.name,
                    'student_count': group.students.count()
                }
                for group in groups
            ]
        return JsonResponse(data, safe=False)

    @log_execution_time
    @handle_exceptions
    def post(self, request: HttpRequest, group_id: Optional[int] = None) -> JsonResponse:
        data = json.loads(request.body)
        
        with transaction.atomic():
            if group_id:
                group = get_object_or_404(SiblingGroup, id=group_id)
                group.name = data.get('name', group.name)
            else:
                group = SiblingGroup(name=data['name'])
            
            group.full_clean()
            group.save()

            if 'student_ids' in data:
                students = User.objects.filter(
                    id__in=data['student_ids'],
                    role='STUDENT'
                )
                group.students.set(students)

            cache.delete(f'sibling_group_{group.id}')
            
            return JsonResponse({
                'message': 'Sibling group updated successfully',
                'group': self.get_group_with_stats(group.id)
            })

@method_decorator(csrf_exempt, name='dispatch')
class StudentGroupListView(View):
    @log_execution_time
    @handle_exceptions
    def get(self, request: HttpRequest) -> JsonResponse:
        cache_key = 'student_groups_list'
        data = cache.get(cache_key)
        
        if data is None:
            groups = StudentGroup.objects.prefetch_related(
                Prefetch('students', queryset=User.objects.only('id', 'first_name', 'last_name', 'grade_level'))
            ).annotate(
                student_count=Count('students')
            ).all()

            data = [
                {
                    'id': group.id,
                    'name': group.name,
                    'description': group.description,
                    'priority': group.priority,
                    'student_count': group.student_count
                }
                for group in groups
            ]
            cache.set(cache_key, data, CACHE_TIMEOUT)
        
        return JsonResponse(data, safe=False)

    @log_execution_time
    @handle_exceptions
    def post(self, request: HttpRequest) -> JsonResponse:
        data = json.loads(request.body)
        
        with transaction.atomic():
            group = StudentGroup(
                name=data['name'],
                description=data.get('description', ''),
                priority=data.get('priority', 3)
            )
            group.full_clean()
            group.save()

            if 'student_ids' in data:
                students = User.objects.filter(
                    id__in=data['student_ids'],
                    role='STUDENT'
                )
                group.students.set(students)

            cache.delete('student_groups_list')
            
            return JsonResponse({
                'message': 'Student group created successfully',
                'group': {
                    'id': group.id,
                    'name': group.name,
                    'description': group.description,
                    'priority': group.priority,
                    'student_count': group.students.count()
                }
            })

@method_decorator(csrf_exempt, name='dispatch')
class SiblingGroupListView(View):
    @log_execution_time
    @handle_exceptions
    def get(self, request: HttpRequest) -> JsonResponse:
        cache_key = 'sibling_groups_list'
        data = cache.get(cache_key)
        
        if data is None:
            groups = SiblingGroup.objects.prefetch_related(
                Prefetch('students', queryset=User.objects.only('id', 'first_name', 'last_name', 'grade_level'))
            ).annotate(
                student_count=Count('students')
            ).all()

            data = [
                {
                    'id': group.id,
                    'name': group.name,
                    'student_count': group.student_count
                }
                for group in groups
            ]
            cache.set(cache_key, data, CACHE_TIMEOUT)
        
        return JsonResponse(data, safe=False)

    @log_execution_time
    @handle_exceptions
    def post(self, request: HttpRequest) -> JsonResponse:
        data = json.loads(request.body)
        
        with transaction.atomic():
            group = SiblingGroup(name=data['name'])
            group.full_clean()
            group.save()

            if 'student_ids' in data:
                students = User.objects.filter(
                    id__in=data['student_ids'],
                    role='STUDENT'
                )
                group.students.set(students)

            cache.delete('sibling_groups_list')
            
            return JsonResponse({
                'message': 'Sibling group created successfully',
                'group': {
                    'id': group.id,
                    'name': group.name,
                    'student_count': group.students.count()
                }
            }) 