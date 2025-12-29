from django.conf import settings
from decouple import config


class SecurityConfig:
    """Centralized security configuration with region-specific settings"""
    
    # Region-specific security profiles
    SECURITY_PROFILES = {
        'strict': {
            'ddos_requests_per_second': 10,
            'ddos_requests_per_minute': 300,
            'ddos_endpoint_limit': 50,
            'ddos_block_duration': 3600,
            'brute_force_attempts': 5,
            'brute_force_window': 300,
            'brute_force_block_duration': 900,
            'sql_injection_block_attempts': 3,
            'request_max_size': 10 * 1024 * 1024,
            'enable_api_key_validation': True,
            'enable_xss_protection': True,
            'enable_sql_injection_protection': True,
            'enable_path_traversal_protection': True,
            'enable_ddos_protection': True,
            'enable_brute_force_protection': True,
        },
        'moderate': {
            'ddos_requests_per_second': 20,
            'ddos_requests_per_minute': 600,
            'ddos_endpoint_limit': 100,
            'ddos_block_duration': 1800,
            'brute_force_attempts': 8,
            'brute_force_window': 300,
            'brute_force_block_duration': 600,
            'sql_injection_block_attempts': 5,
            'request_max_size': 15 * 1024 * 1024,
            'enable_api_key_validation': False,
            'enable_xss_protection': True,
            'enable_sql_injection_protection': True,
            'enable_path_traversal_protection': True,
            'enable_ddos_protection': True,
            'enable_brute_force_protection': True,
        },
        'lenient': {
            'ddos_requests_per_second': 50,
            'ddos_requests_per_minute': 1000,
            'ddos_endpoint_limit': 200,
            'ddos_block_duration': 600,
            'brute_force_attempts': 15,
            'brute_force_window': 600,
            'brute_force_block_duration': 300,
            'sql_injection_block_attempts': 10,
            'request_max_size': 25 * 1024 * 1024,
            'enable_api_key_validation': False,
            'enable_xss_protection': True,
            'enable_sql_injection_protection': True,
            'enable_path_traversal_protection': True,
            'enable_ddos_protection': True,
            'enable_brute_force_protection': True,
        },
        'development': {
            'ddos_requests_per_second': 100,
            'ddos_requests_per_minute': 5000,
            'ddos_endpoint_limit': 1000,
            'ddos_block_duration': 60,
            'brute_force_attempts': 50,
            'brute_force_window': 600,
            'brute_force_block_duration': 60,
            'sql_injection_block_attempts': 50,
            'request_max_size': 50 * 1024 * 1024,
            'enable_api_key_validation': False,
            'enable_xss_protection': False,
            'enable_sql_injection_protection': False,
            'enable_path_traversal_protection': False,
            'enable_ddos_protection': False,
            'enable_brute_force_protection': False,
        },
    }
    
    # Paths that should be exempt from certain security checks
    EXEMPT_PATHS = {
        'static': ['/static/', '/media/', '/favicon.ico'],
        'auth': ['/api/v1/auth/login/', '/api/v1/auth/register/', '/auth/login/', '/auth/register/'],
        'admin': ['/admin/'],
        'health': ['/health/', '/api/health/'],
        'api_docs': ['/api/docs/', '/api/schema/', '/api/redoc/'],
    }
    
    # Trusted user agents (to reduce false positives)
    TRUSTED_USER_AGENTS = [
        'Mozilla',
        'Chrome',
        'Safari',
        'Firefox',
        'Edge',
        'Opera',
        'curl',  # For API testing
        'PostmanRuntime',  # For API testing
        'Insomnia',  # For API testing
    ]
    
    # Whitelisted IPs (for testing, monitoring, etc.)
    WHITELISTED_IPS = config('SECURITY_WHITELISTED_IPS', default='', cast=lambda v: [s.strip() for s in v.split(',') if s.strip()])
    
    # SQL Injection patterns that are too strict (causing false positives)
    # We'll make these more contextual
    RELAXED_SQL_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"('\s*OR\s*'1'\s*=\s*'1)",
        r"('\s*OR\s*1\s*=\s*1)",
        r"(\bxp_cmdshell\b)",
    ]
    
    # XSS patterns that are too strict
    RELAXED_XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:\s*alert",
        r"onerror\s*=\s*['\"]",
        r"<iframe[^>]*src",
        r"eval\s*\(\s*['\"]",
    ]
    
    @classmethod
    def get_profile(cls, profile_name=None):
        """Get security profile based on environment or explicit name"""
        if profile_name is None:
            profile_name = config('SECURITY_PROFILE', default='moderate' if not settings.DEBUG else 'development')
        
        return cls.SECURITY_PROFILES.get(profile_name, cls.SECURITY_PROFILES['moderate'])
    
    @classmethod
    def is_path_exempt(cls, path, category=None):
        """Check if a path is exempt from security checks"""
        if category:
            return any(path.startswith(exempt) for exempt in cls.EXEMPT_PATHS.get(category, []))
        
        # Check all categories
        for exempt_paths in cls.EXEMPT_PATHS.values():
            if any(path.startswith(exempt) for exempt in exempt_paths):
                return True
        return False
    
    @classmethod
    def is_ip_whitelisted(cls, ip):
        """Check if IP is whitelisted"""
        return ip in cls.WHITELISTED_IPS or ip in ['127.0.0.1', '::1', 'localhost']
    
    @classmethod
    def is_trusted_user_agent(cls, user_agent):
        """Check if user agent is trusted"""
        if not user_agent:
            return False
        return any(agent in user_agent for agent in cls.TRUSTED_USER_AGENTS)
    
    @classmethod
    def get_setting(cls, key, default=None, profile=None):
        """Get a specific security setting"""
        profile_data = cls.get_profile(profile)
        return profile_data.get(key, default)
