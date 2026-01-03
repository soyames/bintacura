"""
Performance monitoring decorators for critical endpoints
"""
import sentry_sdk
from functools import wraps
from django.utils.decorators import method_decorator


def monitor_performance(operation_name=None):
    """Decorator to monitor function/view performance in Sentry"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            with sentry_sdk.start_transaction(op="view", name=op_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def monitor_api_performance(view_func):
    """Decorator specifically for API views"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        with sentry_sdk.start_transaction(
            op="api.request",
            name=f"{request.method} {request.path}"
        ):
            sentry_sdk.set_context("api", {
                "method": request.method,
                "path": request.path,
                "query_params": dict(request.GET),
            })
            return view_func(request, *args, **kwargs)
    return wrapper


def monitor_model_save(model_class):
    """Decorator to monitor model save operations"""
    original_save = model_class.save
    
    @wraps(original_save)
    def save_with_monitoring(self, *args, **kwargs):
        with sentry_sdk.start_span(op="db.save", description=f"{model_class.__name__}.save"):
            return original_save(self, *args, **kwargs)
    
    model_class.save = save_with_monitoring
    return model_class


class MonitorPerformanceMixin:
    """Mixin for class-based views to add performance monitoring"""
    
    @method_decorator(monitor_api_performance)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
