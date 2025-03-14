from functools import wraps
from time import time
import logging
from django.http import JsonResponse
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

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
        except ValidationError as e:
            logger.warning(
                "Validation error",
                extra={'errors': str(e), 'id': kwargs.get('id')}
            )
            return JsonResponse({'error': str(e)}, status=400)
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