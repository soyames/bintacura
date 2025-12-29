# -*- coding: utf-8 -*-
"""
Feature Flag System for BINTACURA Platform
Enables region-specific feature control and gradual rollouts
"""
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class FeatureFlags:
    """
    Feature flag manager for controlling features per region.
    
    Features can be:
    - Enabled/disabled globally
    - Enabled/disabled per region
    - Enabled for specific percentage of users (gradual rollout)
    - Enabled for specific user roles
    
    Usage:
    ```python
    if FeatureFlags.is_enabled('new_payment_flow', request):
        # Use new payment flow
    else:
        # Use old payment flow
    ```
    """
    
    # Cache timeout for feature flags (5 minutes)
    CACHE_TIMEOUT = 300
    
    # Default feature flags configuration
    DEFAULT_FLAGS = {
        # Payment features
        'fedapay_integration': {'enabled': True, 'regions': ['mali', 'benin', 'togo']},
        'stripe_integration': {'enabled': True, 'regions': ['default']},
        'wallet_system': {'enabled': True, 'regions': 'all'},
        
        # Healthcare features
        'telemedicine': {'enabled': True, 'regions': 'all'},
        'ai_health_insights': {'enabled': False, 'regions': []},  # Not ready yet
        'wearable_integration': {'enabled': True, 'regions': 'all'},
        
        # Pharmacy features
        'pharmacy_ordering': {'enabled': True, 'regions': 'all'},
        'prescription_delivery': {'enabled': True, 'regions': ['mali', 'default']},
        'doctor_pharmacy_referral': {'enabled': True, 'regions': 'all'},
        
        # Insurance features
        'insurance_claims': {'enabled': True, 'regions': 'all'},
        'auto_claim_approval': {'enabled': False, 'regions': []},  # Testing phase
        
        # Communication features
        'community_forum': {'enabled': True, 'regions': 'all'},
        'video_calls': {'enabled': True, 'regions': 'all'},
        'ride_requests': {'enabled': True, 'regions': ['mali', 'default']},
        
        # Admin features
        'advanced_analytics': {'enabled': True, 'regions': 'all'},
        'audit_logging': {'enabled': True, 'regions': 'all'},
        'security_monitoring': {'enabled': True, 'regions': 'all'},
    }
    
    @classmethod
    def get_flags_config(cls):
        """
        Get feature flags configuration.
        
        Priority:
        1. Database configuration (for dynamic updates)
        2. Settings file configuration
        3. Default flags
        """
        # Check cache first
        cache_key = 'feature_flags_config'
        cached_config = cache.get(cache_key)
        if cached_config:
            return cached_config
        
        # Try to load from database
        try:
            from core.models import FeatureFlagConfig
            db_config = {}
            for flag in FeatureFlagConfig.objects.filter(is_active=True):
                db_config[flag.flag_name] = {
                    'enabled': flag.is_enabled,
                    'regions': flag.enabled_regions.split(',') if flag.enabled_regions else 'all',
                    'rollout_percentage': flag.rollout_percentage,
                    'allowed_roles': flag.allowed_roles.split(',') if flag.allowed_roles else [],
                }
            
            if db_config:
                cache.set(cache_key, db_config, cls.CACHE_TIMEOUT)
                return db_config
        except Exception as e:
            logger.warning(f"Could not load feature flags from database: {e}")
        
        # Fall back to settings or defaults
        config = getattr(settings, 'FEATURE_FLAGS', cls.DEFAULT_FLAGS)
        cache.set(cache_key, config, cls.CACHE_TIMEOUT)
        return config
    
    @classmethod
    def is_enabled(cls, flag_name, request=None, region=None, user=None):
        """
        Check if a feature flag is enabled.
        
        Args:
            flag_name: Name of the feature flag
            request: Django request object (optional)
            region: Region code (optional, extracted from request if not provided)
            user: User object (optional, extracted from request if not provided)
        
        Returns:
            bool: True if feature is enabled, False otherwise
        """
        config = cls.get_flags_config()
        
        # Flag doesn't exist - default to disabled
        if flag_name not in config:
            logger.warning(f"Feature flag '{flag_name}' not found in configuration")
            return False
        
        flag_config = config[flag_name]
        
        # Check if globally disabled
        if not flag_config.get('enabled', False):
            return False
        
        # Extract region and user from request if provided
        if request:
            if not region and hasattr(request, 'BINTACURA_region'):
                region = request.BINTACURA_region
            if not user and hasattr(request, 'user'):
                user = request.user
        
        # Check region restrictions
        allowed_regions = flag_config.get('regions', 'all')
        if allowed_regions != 'all' and region:
            if region not in allowed_regions:
                return False
        
        # Check role restrictions
        allowed_roles = flag_config.get('allowed_roles', [])
        if allowed_roles and user:
            if not hasattr(user, 'role') or user.role not in allowed_roles:
                return False
        
        # Check rollout percentage (gradual rollout)
        rollout_percentage = flag_config.get('rollout_percentage', 100)
        if rollout_percentage < 100 and user:
            # Use user ID for consistent rollout
            user_hash = hash(str(user.uid)) % 100
            if user_hash >= rollout_percentage:
                return False
        
        return True
    
    @classmethod
    def get_enabled_features(cls, request=None, region=None, user=None):
        """
        Get list of all enabled features for given context.
        
        Returns:
            list: List of enabled feature flag names
        """
        config = cls.get_flags_config()
        enabled = []
        
        for flag_name in config.keys():
            if cls.is_enabled(flag_name, request, region, user):
                enabled.append(flag_name)
        
        return enabled
    
    @classmethod
    def clear_cache(cls):
        """Clear cached feature flags configuration."""
        cache.delete('feature_flags_config')
        logger.info("Feature flags cache cleared")


# Template tag for feature flags
def feature_enabled(flag_name, request):
    """
    Template tag to check feature flags in templates.
    
    Usage in templates:
    {% if feature_enabled 'new_payment_flow' request %}
        <!-- New payment flow -->
    {% endif %}
    """
    return FeatureFlags.is_enabled(flag_name, request)

