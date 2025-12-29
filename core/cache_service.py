from django.core.cache import cache
from functools import wraps
import hashlib
import json


def cache_view(timeout=300, key_prefix="view"):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            cache_key = generate_cache_key(key_prefix, request, args, kwargs)

            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response

            response = view_func(request, *args, **kwargs)
            cache.set(cache_key, response, timeout)
            return response

        return wrapper

    return decorator


def cache_queryset(timeout=300, key_prefix="qs"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = generate_cache_key(key_prefix, None, args, kwargs)

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result

        return wrapper

    return decorator


def invalidate_cache(key_pattern):
    cache.delete_pattern(f"*{key_pattern}*")


def generate_cache_key(prefix, request, args, kwargs):
    key_parts = [prefix]

    if request:
        key_parts.append(request.path)
        key_parts.append(request.method)
        if request.user.is_authenticated:
            key_parts.append(str(request.user.uid))

    key_parts.extend([str(arg) for arg in args])
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])

    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


class CacheService:
    @staticmethod
    def get_or_set(key, callback, timeout=300):
        value = cache.get(key)
        if value is None:
            value = callback()
            cache.set(key, value, timeout)
        return value

    @staticmethod
    def invalidate_model(model_name, instance_id=None):
        if instance_id:
            pattern = f"{model_name}:{instance_id}"
        else:
            pattern = f"{model_name}:*"
        cache.delete_pattern(pattern)

    @staticmethod
    def cache_participant_data(participant_id, data, timeout=600):
        cache.set(f"participant:{participant_id}", data, timeout)

    @staticmethod
    def get_participant_data(participant_id):
        return cache.get(f"participant:{participant_id}")

    @staticmethod
    def cache_appointment_list(user_id, appointments, timeout=300):
        cache.set(f"appointments:{user_id}", appointments, timeout)

    @staticmethod
    def invalidate_appointment_cache(user_id):
        cache.delete(f"appointments:{user_id}")


cache_service = CacheService()
