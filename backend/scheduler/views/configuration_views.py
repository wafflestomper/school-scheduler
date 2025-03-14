from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.cache import cache
from ..models import (
    SchedulingConfiguration,
    CourseTypeConfiguration
)
from ..decorators import handle_exceptions, log_execution_time
import json

CACHE_TIMEOUT = 300  # 5 minutes

class BaseConfigurationView(View):
    """Base view for configuration endpoints"""
    model = None
    fields = []
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    @handle_exceptions
    @log_execution_time
    def get(self, request):
        """Get active configuration"""
        config = self.model.objects.filter(active=True).first()
        if not config:
            return JsonResponse({'error': 'No active configuration found'}, status=404)
        
        return JsonResponse({
            field: getattr(config, field)
            for field in self.fields
        })
    
    @transaction.atomic
    @handle_exceptions
    @log_execution_time
    def post(self, request):
        """Update configuration"""
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        config = self.model.objects.filter(active=True).first()
        if not config:
            config = self.model.objects.create(
                name='Default Configuration',
                active=True
            )
        
        for field in self.fields:
            if field in data:
                setattr(config, field, data[field])
        
        try:
            config.full_clean()
            config.save()
            
            # Clear cache
            cache.delete(f'{self.model.__name__}_active')
            
            return JsonResponse({
                field: getattr(config, field)
                for field in self.fields
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class SchedulingConfigurationView(BaseConfigurationView):
    model = SchedulingConfiguration
    fields = ['max_class_size', 'max_consecutive_periods',
             'min_prep_periods', 'prioritize_specialized_rooms']

@method_decorator(csrf_exempt, name='dispatch')
class CourseTypeConfigurationView(BaseConfigurationView):
    model = CourseTypeConfiguration
    fields = ['enforce_grade_levels', 'allow_mixed_levels', 'respect_prerequisites'] 