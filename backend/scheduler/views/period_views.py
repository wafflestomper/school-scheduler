from __future__ import annotations
from typing import Dict, Any, List, Optional
from django.http import JsonResponse, HttpRequest
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Period, Section
import json
import logging
from functools import wraps
from time import time
from datetime import datetime

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
        except Period.DoesNotExist:
            logger.warning("Period not found", extra={'period_id': kwargs.get('period_id')})
            return JsonResponse({'error': 'Period not found'}, status=404)
        except ValidationError as e:
            logger.warning(
                "Validation error",
                extra={'errors': str(e), 'period_id': kwargs.get('period_id')}
            )
            return JsonResponse({'error': str(e)}, status=400)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON data received")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(
                f"Unexpected error: {str(e)}",
                exc_info=True,
                extra={'period_id': kwargs.get('period_id')}
            )
            return JsonResponse(
                {'error': 'An unexpected error occurred'},
                status=500
            )
    return wrapper

@method_decorator(csrf_exempt, name='dispatch')
class PeriodView(View):
    """View for managing individual periods"""
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @log_execution_time
    def get_period_with_stats(self, period_id: int) -> Optional[Dict[str, Any]]:
        """Get period details with related statistics"""
        cache_key = f'period_details_{period_id}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            period = Period.objects.get(id=period_id)
            data = {
                'id': period.id,
                'name': period.name,
                'start_time': period.start_time.strftime('%H:%M'),
                'end_time': period.end_time.strftime('%H:%M'),
                'duration_minutes': period.duration_minutes(),
                'stats': period.get_schedule_stats()
            }
            cache.set(cache_key, data, self.CACHE_TIMEOUT)
            return data
        except Period.DoesNotExist:
            return None
    
    @handle_exceptions
    def get(self, request: HttpRequest, period_id: int) -> JsonResponse:
        """Handle GET request for period details"""
        period_data = self.get_period_with_stats(period_id)
        if not period_data:
            return JsonResponse({
                'error': 'Period not found'
            }, status=404)
            
        return JsonResponse(period_data)
    
    @handle_exceptions
    def post(self, request: HttpRequest, period_id: int) -> JsonResponse:
        """Handle POST request for updating period details"""
        try:
            period = Period.objects.get(id=period_id)
        except Period.DoesNotExist:
            return JsonResponse({
                'error': 'Period not found'
            }, status=404)
            
        try:
            data = json.loads(request.body)
            
            with transaction.atomic():
                if 'name' in data:
                    period.name = data['name']
                if 'start_time' in data:
                    period.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
                if 'end_time' in data:
                    period.end_time = datetime.strptime(data['end_time'], '%H:%M').time()
                    
                period.full_clean()
                period.save()
                
                # Clear cache
                cache.delete(f'period_details_{period_id}')
                cache.delete('period_list')
                
                return JsonResponse({
                    'message': 'Period updated successfully',
                    'period': self.get_period_with_stats(period_id)
                })
                
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except ValidationError as e:
            return JsonResponse({
                'error': 'Validation error',
                'details': dict(e)
            }, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class PeriodListView(View):
    """View for managing period lists"""
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @log_execution_time
    def get_period_list(self) -> list[Dict[str, Any]]:
        """Get list of all periods with basic details"""
        cache_key = 'period_list'
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        periods = Period.objects.all().order_by('start_time')
        data = [{
            'id': period.id,
            'name': period.name,
            'start_time': period.start_time.strftime('%H:%M'),
            'end_time': period.end_time.strftime('%H:%M'),
            'duration_minutes': period.duration_minutes()
        } for period in periods]
        
        cache.set(cache_key, data, self.CACHE_TIMEOUT)
        return data
    
    @handle_exceptions
    def get(self, request: HttpRequest) -> JsonResponse:
        """Handle GET request for period list"""
        return JsonResponse({
            'periods': self.get_period_list()
        })
    
    @handle_exceptions
    def post(self, request: HttpRequest) -> JsonResponse:
        """Handle POST request for creating new period"""
        try:
            data = json.loads(request.body)
            
            required_fields = ['name', 'start_time', 'end_time']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return JsonResponse({
                    'error': 'Missing required fields',
                    'fields': missing_fields
                }, status=400)
            
            with transaction.atomic():
                period = Period(
                    name=data['name'],
                    start_time=datetime.strptime(data['start_time'], '%H:%M').time(),
                    end_time=datetime.strptime(data['end_time'], '%H:%M').time()
                )
                period.full_clean()
                period.save()
                
                # Clear cache
                cache.delete('period_list')
                
                return JsonResponse({
                    'message': 'Period created successfully',
                    'period': {
                        'id': period.id,
                        'name': period.name,
                        'start_time': period.start_time.strftime('%H:%M'),
                        'end_time': period.end_time.strftime('%H:%M'),
                        'duration_minutes': period.duration_minutes()
                    }
                }, status=201)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except ValidationError as e:
            return JsonResponse({
                'error': 'Validation error',
                'details': dict(e)
            }, status=400) 