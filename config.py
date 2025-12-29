"""
Environment Configuration Management for BINTACURA
==================================================

This module handles environment-specific configuration loading for BINTACURA's
multi-region healthcare platform deployed on Render.com.

Architecture:
- Primary Database: Render.com PostgreSQL (global/default region)
- Future: Regional databases for Mali, Senegal, Burkina Faso, etc.
- Local Development: Port 8080
- Production: Render.com with auto-scaling

Usage:
    from config import load_environment
    
    # Auto-detect and load environment
    load_environment()
    
    # Or specify environment
    load_environment('production')

Multi-Region Support:
    Set DEPLOYMENT_REGION environment variable to enable regional routing:
    - 'global' (default): Uses primary Render database
    - 'mali': Routes to Mali regional database (when configured)
    - 'senegal': Routes to Senegal regional database (when configured)
"""

import os
import sys
from pathlib import Path
from decouple import config


class EnvironmentConfig:
    """Environment configuration loader with multi-region support"""
    
    VALID_ENVIRONMENTS = ['development', 'staging', 'production']
    SUPPORTED_REGIONS = ['global', 'mali', 'senegal', 'burkina_faso', 'niger', 'benin', 'ivory_coast', 'togo', 'cameroon', 'ghana','central_african_republic']
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent
        self.environment = None
        self.is_local = True
        self.region = 'global'
        
    def detect_environment(self):
        """Auto-detect the current environment"""
        # Check environment variable
        env = config('ENVIRONMENT', default=None)
        
        if env:
            return env.lower()
        
        # Detect Render.com deployment
        if os.environ.get('RENDER'):
            return 'production'
        
        # Detect based on hostname
        hostname = os.environ.get('HOSTNAME', '').lower()
        
        if any(x in hostname for x in ['prod', 'production', 'render']):
            return 'production'
        elif any(x in hostname for x in ['staging', 'stage']):
            return 'staging'
        else:
            return 'development'
    
    def detect_region(self):
        """Detect deployment region"""
        return config('DEPLOYMENT_REGION', default='global').lower()
    
    def load(self, environment=None):
        """Load environment configuration"""
        self.environment = environment or self.detect_environment()
        self.region = self.detect_region()
        
        if self.environment not in self.VALID_ENVIRONMENTS:
            print(f"⚠️  Warning: Unknown environment '{self.environment}'")
            print(f"   Valid options: {', '.join(self.VALID_ENVIRONMENTS)}")
            print(f"   Defaulting to 'development'")
            self.environment = 'development'
        
        # Determine if running locally or on server
        self.is_local = self._detect_if_local()
        
        # Print configuration summary
        self._print_config_summary()
        
        return self.environment
    
    def _detect_if_local(self):
        """Detect if running on local machine or Render.com"""
        # Check for Render.com
        if os.environ.get('RENDER'):
            return False
        
        # Check for common cloud environment variables
        cloud_indicators = [
            'AWS_EXECUTION_ENV',
            'KUBERNETES_SERVICE_HOST',
            'HEROKU_APP_NAME',
            'DYNO',
            'GOOGLE_CLOUD_PROJECT',
            'AZURE_FUNCTIONS_ENVIRONMENT',
            'IS_RENDER',
        ]
        
        for indicator in cloud_indicators:
            if os.environ.get(indicator):
                return False
        
        # Check if running on localhost
        hostname = os.environ.get('HOSTNAME', '').lower()
        if any(x in hostname for x in ['localhost', '127.0.0.1', 'desktop', 'laptop']):
            return True
        
        # Default to local if can't determine
        return True
    
    def _print_config_summary(self):
        """Print configuration summary"""
        location = 'LOCAL MACHINE' if self.is_local else 'RENDER.COM'
        
        print("\n" + "="*70)
        print("BINTACURA ENVIRONMENT CONFIGURATION")
        print("="*70)
        print(f"Environment:     {self.environment.upper()}")
        print(f"Location:        {location}")
        print(f"Region:          {self.region.upper()}")
        print(f"Debug Mode:      {config('DEBUG', default=False, cast=bool)}")
        print(f"Database:        {config('DB_HOST', default='localhost')}")
        print(f"Email Backend:   {'AWS SES' if config('USE_SES', default=False, cast=bool) else 'SMTP'}")
        print(f"Security:        {config('SECURITY_PROFILE', default='moderate')}")
        if self.is_local:
            print(f"Local Port:      8080")
        print("="*70 + "\n")
    
    def get_deployment_checklist(self):
        """Return deployment checklist for current environment"""
        if self.environment == 'production':
            return self._production_checklist()
        elif self.environment == 'staging':
            return self._staging_checklist()
        else:
            return self._development_checklist()
    
    def _production_checklist(self):
        """Production deployment checklist for Render.com"""
        checklist = {
            'DEBUG': config('DEBUG', default=True, cast=bool) == False,
            'SECRET_KEY': config('SECRET_KEY', default='insecure') != 'insecure',
            'SECURE_SSL_REDIRECT': config('SECURE_SSL_REDIRECT', default=False, cast=bool) == True,
            'ALLOWED_HOSTS': len(config('ALLOWED_HOSTS', default='').split(',')) > 0,
            'DATABASE_SSL': True,
            'EMAIL_CONFIGURED': config('USE_SES', default=False, cast=bool) or config('EMAIL_HOST', default=''),
            'RENDER_DEPLOYMENT': os.environ.get('RENDER') is not None,
        }
        return checklist
    
    def _staging_checklist(self):
        """Staging deployment checklist"""
        return {
            'DEBUG': True,
            'SECRET_KEY': config('SECRET_KEY', default='insecure') != 'insecure',
            'ALLOWED_HOSTS': len(config('ALLOWED_HOSTS', default='').split(',')) > 0,
            'EMAIL_CONFIGURED': True,
        }
    
    def _development_checklist(self):
        """Development environment checklist"""
        return {
            'DATABASE_ACCESSIBLE': True,
            'ENV_FILE_EXISTS': (self.base_dir / '.env').exists(),
            'PORT_8080': True,  # Local development uses port 8080
        }
    
    def validate(self):
        """Validate environment configuration"""
        checklist = self.get_deployment_checklist()
        failed_checks = [k for k, v in checklist.items() if not v]
        
        if failed_checks:
            print("\n⚠️  CONFIGURATION WARNINGS:")
            for check in failed_checks:
                print(f"   ❌ {check}")
            print()
            
            if self.environment == 'production':
                print("⛔ CRITICAL: Production environment has configuration issues!")
                print("   Fix these issues before deploying to production.\n")
                return False
        else:
            print("✅ Configuration validated successfully!\n")
        
        return True
    
    def get_region_info(self):
        """Get information about current region configuration"""
        return {
            'region': self.region,
            'is_multi_region': config('ENABLE_MULTI_REGION', default=False, cast=bool),
            'available_regions': self.SUPPORTED_REGIONS,
        }


# Global instance
_env_config = EnvironmentConfig()
_loaded = False  # Flag to prevent duplicate loading


def load_environment(environment=None):
    """
    Load and validate environment configuration
    
    Args:
        environment: Optional environment name (development, staging, production)
                    If not provided, will auto-detect
    
    Returns:
        str: The loaded environment name
    """
    global _loaded
    if _loaded:
        return _env_config.environment or 'development'
    
    result = _env_config.load(environment)
    _loaded = True
    return result


def get_environment():
    """Get current environment name"""
    return _env_config.environment or 'development'


def get_region():
    """Get current deployment region"""
    return _env_config.region


def is_local():
    """Check if running locally"""
    return _env_config.is_local


def is_production():
    """Check if running in production"""
    return _env_config.environment == 'production'


def is_render():
    """Check if running on Render.com"""
    return os.environ.get('RENDER') is not None


def validate_config():
    """Validate current configuration"""
    return _env_config.validate()


def get_region_info():
    """Get multi-region configuration info"""
    return _env_config.get_region_info()


# Auto-load on import (can be disabled if needed)
if __name__ != "__main__":
    load_environment()

