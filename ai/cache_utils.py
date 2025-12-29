"""
AI Caching Utilities (Phase 11)
Provides caching functionality for AI insights and ML model predictions
Uses Django's cache framework with local memory backend for minimal storage impact
"""
from django.core.cache import cache
from django.core.cache.backends.locmem import LocMemCache
from functools import wraps
import hashlib
import json


class AICacheManager:
    """
    Central cache manager for all AI operations
    Implements intelligent caching with automatic invalidation
    """

    # Cache timeout configurations (in seconds)
    CACHE_TIMEOUTS = {
        'chat_conversation': 3600,  # 1 hour
        'health_analysis': 1800,  # 30 minutes
        'diagnostic_analysis': 1800,  # 30 minutes
        'lab_interpretation': 1800,  # 30 minutes
        'health_risk': 3600,  # 1 hour
        'healthcare_needs': 7200,  # 2 hours
        'churn_prediction': 3600,  # 1 hour
        'patient_segmentation': 7200,  # 2 hours
        'revenue_forecast': 3600,  # 1 hour
        'hospital_insights': 1800,  # 30 minutes
    }

    @staticmethod
    def get_cache_key(prefix, participant_id, **kwargs):
        """
        Generate a unique cache key based on prefix, participant, and parameters

        Args:
            prefix: Cache key prefix (e.g., 'diagnostic_analysis')
            participant_id: UUID of participant
            **kwargs: Additional parameters for cache key uniqueness

        Returns:
            str: Unique cache key
        """
        # Sort kwargs for consistent key generation
        sorted_kwargs = sorted(kwargs.items())
        kwargs_str = json.dumps(sorted_kwargs, sort_keys=True)

        # Create hash for long parameter strings
        params_hash = hashlib.md5(kwargs_str.encode()).hexdigest()[:8]

        return f"ai:{prefix}:{participant_id}:{params_hash}"

    @staticmethod
    def get(prefix, participant_id, **kwargs):
        """
        Get cached AI result

        Args:
            prefix: Cache key prefix
            participant_id: UUID of participant
            **kwargs: Additional cache key parameters

        Returns:
            Cached value or None if not found
        """
        cache_key = AICacheManager.get_cache_key(prefix, participant_id, **kwargs)
        return cache.get(cache_key)

    @staticmethod
    def set(prefix, participant_id, value, timeout=None, **kwargs):
        """
        Set cached AI result

        Args:
            prefix: Cache key prefix
            participant_id: UUID of participant
            value: Value to cache
            timeout: Cache timeout in seconds (None uses default for prefix)
            **kwargs: Additional cache key parameters
        """
        cache_key = AICacheManager.get_cache_key(prefix, participant_id, **kwargs)

        # Use default timeout if not specified
        if timeout is None:
            timeout = AICacheManager.CACHE_TIMEOUTS.get(prefix, 1800)  # Default 30 min

        cache.set(cache_key, value, timeout)

    @staticmethod
    def invalidate(prefix, participant_id, **kwargs):
        """
        Invalidate (delete) cached AI result

        Args:
            prefix: Cache key prefix
            participant_id: UUID of participant
            **kwargs: Additional cache key parameters
        """
        cache_key = AICacheManager.get_cache_key(prefix, participant_id, **kwargs)
        cache.delete(cache_key)

    @staticmethod
    def invalidate_pattern(prefix, participant_id):
        """
        Invalidate all cache entries matching prefix and participant

        Args:
            prefix: Cache key prefix
            participant_id: UUID of participant

        Note: This is a simplified version. For production with Redis,
        use SCAN command for pattern-based deletion.
        """
        # For local memory cache, we can't easily delete by pattern
        # This is a placeholder for future Redis implementation
        pass

    @staticmethod
    def invalidate_participant(participant_id):
        """
        Invalidate all AI cache for a specific participant

        Args:
            participant_id: UUID of participant

        Use cases:
        - When new health record is added
        - When patient data is updated
        """
        prefixes = [
            'health_analysis',
            'diagnostic_analysis',
            'lab_interpretation',
            'health_risk',
            'healthcare_needs',
        ]

        for prefix in prefixes:
            AICacheManager.invalidate(prefix, participant_id)

    @staticmethod
    def invalidate_organization(organization_id):
        """
        Invalidate all AI cache for an organization

        Args:
            organization_id: UUID of organization

        Use cases:
        - When new employee data is added
        - When transaction records change
        """
        prefixes = [
            'churn_prediction',
            'patient_segmentation',
            'revenue_forecast',
            'hospital_insights',
        ]

        for prefix in prefixes:
            AICacheManager.invalidate(prefix, organization_id)


def cache_ai_result(prefix, timeout=None, participant_param='participant'):
    """
    Decorator to cache AI analysis results

    Args:
        prefix: Cache key prefix
        timeout: Cache timeout in seconds
        participant_param: Name of the participant parameter in the function

    Usage:
        @cache_ai_result('diagnostic_analysis', timeout=1800)
        def analyze_diagnostics(participant, days_back=365):
            # ... analysis logic ...
            return result
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get participant from args or kwargs
            participant = kwargs.get(participant_param)
            if not participant and len(args) > 0:
                participant = args[0]

            if not participant:
                # Can't cache without participant ID
                return func(*args, **kwargs)

            participant_id = str(participant.uid)

            # Build cache kwargs from function kwargs
            cache_kwargs = {k: v for k, v in kwargs.items() if k != participant_param}

            # Try to get from cache
            cached_result = AICacheManager.get(prefix, participant_id, **cache_kwargs)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            AICacheManager.set(prefix, participant_id, result, timeout, **cache_kwargs)

            return result

        return wrapper
    return decorator


def cache_ml_prediction(model_name, timeout=3600):
    """
    Decorator specifically for ML model predictions

    Args:
        model_name: Name of the ML model
        timeout: Cache timeout in seconds (default 1 hour)

    Usage:
        @cache_ml_prediction('churn_predictor', timeout=3600)
        def predict_churn(organization):
            # ... ML prediction logic ...
            return predictions
    """
    return cache_ai_result(f'ml_{model_name}', timeout=timeout, participant_param='organization')


class AICacheStats:
    """Track cache hit/miss statistics for monitoring"""

    @staticmethod
    def record_hit(prefix):
        """Record a cache hit"""
        cache.set(f'ai:stats:{prefix}:hits', cache.get(f'ai:stats:{prefix}:hits', 0) + 1, timeout=86400)

    @staticmethod
    def record_miss(prefix):
        """Record a cache miss"""
        cache.set(f'ai:stats:{prefix}:misses', cache.get(f'ai:stats:{prefix}:misses', 0) + 1, timeout=86400)

    @staticmethod
    def get_stats(prefix):
        """
        Get cache statistics for a prefix

        Returns:
            dict: Hit and miss counts
        """
        hits = cache.get(f'ai:stats:{prefix}:hits', 0)
        misses = cache.get(f'ai:stats:{prefix}:misses', 0)
        total = hits + misses

        hit_rate = (hits / total * 100) if total > 0 else 0

        return {
            'hits': hits,
            'misses': misses,
            'total': total,
            'hit_rate': round(hit_rate, 2)
        }

    @staticmethod
    def get_all_stats():
        """Get statistics for all AI cache prefixes"""
        stats = {}
        for prefix in AICacheManager.CACHE_TIMEOUTS.keys():
            stats[prefix] = AICacheStats.get_stats(prefix)
        return stats


# Signal handlers for automatic cache invalidation
def invalidate_health_cache_on_record_save(sender, instance, **kwargs):
    """
    Signal handler to invalidate health analysis cache when health record changes

    Connect in ai/apps.py:
        from django.db.models.signals import post_save
        from health_records.models import HealthRecord

        post_save.connect(
            invalidate_health_cache_on_record_save,
            sender=HealthRecord
        )
    """
    if hasattr(instance, 'assigned_to'):
        participant_id = str(instance.assigned_to.id)
        AICacheManager.invalidate_participant(participant_id)


def invalidate_org_cache_on_data_change(sender, instance, **kwargs):
    """
    Signal handler to invalidate organization cache when employee/transaction changes

    Connect for Employee and Transaction models
    """
    if hasattr(instance, 'organization'):
        organization_id = str(instance.organization.id)
        AICacheManager.invalidate_organization(organization_id)
