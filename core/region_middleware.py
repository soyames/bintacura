# -*- coding: utf-8 -*-
"""
Region Context Middleware for Multi-Region Architecture
Sets up thread-local storage for region context in API requests
"""
from threading import local
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


_thread_locals = local()


def get_current_request():
    """Get the current request from thread-local storage."""
    return getattr(_thread_locals, 'request', None)


def get_current_region():
    """Get the current region from thread-local storage."""
    return getattr(_thread_locals, 'region', settings.DEPLOYMENT_REGION)


class RegionContextMiddleware(MiddlewareMixin):
    """
    Middleware to set region context for each request.
    
    Region determination priority:
    1. HTTP_X_BINTACURA_REGION header (explicit region selection)
    2. Subdomain detection (e.g., ml.BINTACURA.com -> mali)
    3. DEPLOYMENT_REGION setting (server-level default)
    
    This middleware must be placed BEFORE database operations occur.
    """
    
    def process_request(self, request):
        """Store request and region in thread-local storage."""
        # Store request for database router access
        _thread_locals.request = request
        
        # Determine region from request
        region = self._determine_region(request)
        _thread_locals.region = region
        
        # Add region to request for easy access
        request.BINTACURA_region = region
        
        return None
    
    def process_response(self, request, response):
        """Clean up thread-local storage."""
        # Add region header to response for debugging
        if hasattr(request, 'BINTACURA_region'):
            response['X-BINTACURA-Region'] = request.BINTACURA_region
        
        return response
    
    def process_exception(self, request, exception):
        """Clean up thread-locals on exception."""
        self._cleanup_thread_locals()
        return None
    
    def _determine_region(self, request):
        """
        Determine the region for the current request.
        
        Args:
            request: Django request object
            
        Returns:
            str: Region code (e.g., 'default', 'mali', 'senegal')
        """
        # 1. Check explicit region header
        region = request.META.get('HTTP_X_BINTACURA_REGION')
        if region and self._is_valid_region(region):
            return region
        
        # 2. Check subdomain
        host = request.META.get('HTTP_HOST', '').lower()
        region_map = getattr(settings, 'REGIONAL_DATABASE_MAP', {})
        
        for region_code, config in region_map.items():
            domain = config.get('domain', '')
            if domain and domain in host:
                return region_code
        
        # 3. Use deployment region setting
        return getattr(settings, 'DEPLOYMENT_REGION', 'default')
    
    def _is_valid_region(self, region):
        """Check if region code is configured."""
        region_map = getattr(settings, 'REGIONAL_DATABASE_MAP', {})
        return region in region_map or region == 'default'
    
    def _cleanup_thread_locals(self):
        """Clean up thread-local storage."""
        if hasattr(_thread_locals, 'request'):
            delattr(_thread_locals, 'request')
        if hasattr(_thread_locals, 'region'):
            delattr(_thread_locals, 'region')


# Make thread locals accessible to db_router
settings._thread_locals = _thread_locals

