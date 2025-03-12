from __future__ import annotations
from typing import Dict, Any, List, Optional, Type
from django.http import JsonResponse, HttpRequest
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db.models import Model
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import (
    SchedulingConfiguration, SiblingConfiguration,
    StudentGroupConfiguration, ElectiveConfiguration,
    CourseTypeConfiguration
)
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
        except (SchedulingConfiguration.DoesNotExist,
                SiblingConfiguration.DoesNotExist,
                StudentGroupConfiguration.DoesNotExist,
                ElectiveConfiguration.DoesNotExist,
                CourseTypeConfiguration.DoesNotExist):
            logger.warning("Configuration not found", extra={'id': kwargs.get('id')})
            return JsonResponse({'error': 'Configuration not found'}, status=404)
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

class BaseConfigurationView(View):
    """Base class for configuration views"""
    model: Type[Model] = None
    fields: List[str] = []
    
    def get_config_data(self, config: Model) -> Dict[str, Any]:
        """Get configuration data as dictionary"""
        data = {
            'id': config.id,
            'name': config.name,
            'active': config.active
        }
        for field in self.fields:
            data[field] = getattr(config, field)
        return data

    @handle_exceptions
    @log_execution_time
    def get(self, request: HttpRequest, config_id: Optional[int] = None) -> JsonResponse:
        """Handle GET requests for configuration details"""
        if config_id:
            cache_key = f'{self.model.__name__.lower()}_{config_id}'
            config_data = cache.get(cache_key)
            
            if config_data is None:
                config = get_object_or_404(self.model, id=config_id)
                config_data = self.get_config_data(config)
                cache.set(cache_key, config_data, CACHE_TIMEOUT)
            
            return JsonResponse(config_data)
        else:
            cache_key = f'all_{self.model.__name__.lower()}s'
            configs_data = cache.get(cache_key)
            
            if configs_data is None:
                configs = self.model.objects.all()
                configs_data = [self.get_config_data(config) for config in configs]
                cache.set(cache_key, configs_data, CACHE_TIMEOUT)
            
            return JsonResponse({'configurations': configs_data})

    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def post(self, request: HttpRequest, config_id: Optional[int] = None) -> JsonResponse:
        """Handle POST requests for creating/updating configurations"""
        data = json.loads(request.body)
        
        if config_id:
            # Update existing configuration
            config = get_object_or_404(self.model, id=config_id)
            
            # Update fields
            for field in ['name', 'active'] + self.fields:
                if field in data:
                    setattr(config, field, data[field])
        else:
            # Create new configuration
            required_fields = ['name'] + self.fields
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return JsonResponse(
                    {'error': f'Missing required fields: {", ".join(missing_fields)}'},
                    status=400
                )
            
            config = self.model(
                name=data['name'],
                active=data.get('active', False)
            )
            for field in self.fields:
                setattr(config, field, data[field])
        
        try:
            config.full_clean()
            config.save()
            
            # Clear cache
            if config_id:
                cache.delete(f'{self.model.__name__.lower()}_{config_id}')
            cache.delete(f'all_{self.model.__name__.lower()}s')
            
            logger.info(
                f"{'Updated' if config_id else 'Created'} {self.model.__name__}: {config.name}",
                extra={'config_id': config.id}
            )
            
            return JsonResponse({
                'status': 'success',
                'config_id': config.id
            })
            
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class SchedulingConfigurationView(BaseConfigurationView):
    model = SchedulingConfiguration
    fields = ['max_class_size', 'max_consecutive_periods', 'min_prep_periods',
              'prioritize_specialized_rooms']

@method_decorator(csrf_exempt, name='dispatch')
class SiblingConfigurationView(BaseConfigurationView):
    model = SiblingConfiguration
    fields = ['keep_siblings_together', 'priority']

@method_decorator(csrf_exempt, name='dispatch')
class StudentGroupConfigurationView(BaseConfigurationView):
    model = StudentGroupConfiguration
    fields = ['respect_separation_groups', 'respect_grouping_preferences', 'priority']

@method_decorator(csrf_exempt, name='dispatch')
class ElectiveConfigurationView(BaseConfigurationView):
    model = ElectiveConfiguration
    fields = ['max_electives_per_student', 'prioritize_grade_level', 'allow_mixed_grades']

@method_decorator(csrf_exempt, name='dispatch')
class CourseTypeConfigurationView(BaseConfigurationView):
    model = CourseTypeConfiguration
    fields = ['enforce_grade_levels', 'allow_mixed_levels', 'respect_prerequisites'] 