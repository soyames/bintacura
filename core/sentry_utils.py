"""
Sentry integration utilities for Bintacura
Provides context enrichment and custom error handling
"""
import sentry_sdk
from functools import wraps


def set_participant_context(participant):
    """Set participant context for Sentry events"""
    if not participant:
        return
    
    sentry_sdk.set_user({
        "id": str(participant.uid),
        "username": getattr(participant, 'username', None),
        "email": getattr(participant, 'email', None),
        "role": getattr(participant, 'role', None),
    })


def set_transaction_context(transaction_type, transaction_id, **extra):
    """Set transaction context for Sentry events"""
    sentry_sdk.set_context("transaction", {
        "type": transaction_type,
        "id": str(transaction_id),
        **extra
    })


def capture_business_metric(metric_name, value, tags=None):
    """Capture business metrics in Sentry"""
    from sentry_sdk import metrics
    
    metrics.distribution(metric_name, value)


def capture_error_with_context(exception, context=None):
    """Capture exception with additional context"""
    if context:
        for key, value in context.items():
            sentry_sdk.set_context(key, value)
    
    sentry_sdk.capture_exception(exception)


def sentry_trace(func):
    """Decorator to trace function execution in Sentry"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with sentry_sdk.start_transaction(op="function", name=func.__name__):
            return func(*args, **kwargs)
    return wrapper


def add_breadcrumb(message, category="custom", level="info", data=None):
    """Add breadcrumb to Sentry for debugging"""
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {}
    )
