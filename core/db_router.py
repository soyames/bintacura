# -*- coding: utf-8 -*-
"""
Multi-Region Database Router for BINTACURA Platform
Enables multi-tenant architecture with regional database iBINTAtion
"""
from django.conf import settings


class RegionalDatabaseRouter:
    """
    Routes database operations to regional databases based on user/request context.
    
    Architecture:
    - Central Hub: BINTACURA.com (database: 'default')
    - Regional Instances: ml.BINTACURA.com, etc. (database: 'region_<code>')
    
    Usage:
    1. Add to settings.py: DATABASE_ROUTERS = ['core.db_router.RegionalDatabaseRouter']
    2. Configure regional databases in DATABASES setting
    3. Set REGIONAL_DATABASE_MAP in settings
    """
    
    # Apps that should always use the central database
    CENTRAL_APPS = {
        'admin',
        'auth',
        'contenttypes',
        'sessions',
    }
    
    # Apps that use regional databases
    REGIONAL_APPS = {
        'core',
        'appointments',
        'prescriptions',
        'health_records',
        'communication',
        'payments',
        'pharmacy',
        'hospital',
        'insurance',
        'analytics',
        'ads',
    }
    
    def __init__(self):
        """Initialize router with regional database mapping."""
        self.regional_databases = getattr(settings, 'REGIONAL_DATABASE_MAP', {})
        self.default_region = getattr(settings, 'DEFAULT_REGION', 'default')
    
    def get_region_from_request(self):
        """
        Extract region from current request context.
        
        Uses thread-local storage to access current request.
        Falls back to default region if no request context.
        """
        try:
            from threading import local
            _thread_locals = getattr(settings, '_thread_locals', None)
            if _thread_locals and hasattr(_thread_locals, 'request'):
                request = _thread_locals.request
                # Check custom header for region
                region = request.META.get('HTTP_X_BINTACURA_REGION')
                if region and region in self.regional_databases:
                    return region
                
                # Check subdomain
                host = request.META.get('HTTP_HOST', '')
                for region_code, config in self.regional_databases.items():
                    if config.get('domain') in host:
                        return region_code
        except Exception:
            pass
        
        return self.default_region
    
    def db_for_read(self, model, **hints):
        """
        Route read operations to appropriate database.
        
        Args:
            model: The model being queried
            **hints: Additional routing hints (e.g., instance)
        
        Returns:
            str: Database alias to use, or None for default routing
        """
        app_label = model._meta.app_label
        
        # Always use central database for admin apps
        if app_label in self.CENTRAL_APPS:
            return 'default'
        
        # Check if model explicitly specifies a database
        if hasattr(model, '_database_override'):
            return model._database_override
        
        # Check hints for explicit database
        if 'database' in hints:
            return hints['database']
        
        # Route regional apps to appropriate database
        if app_label in self.REGIONAL_APPS:
            region = self.get_region_from_request()
            return self.regional_databases.get(region, {}).get('alias', 'default')
        
        return 'default'
    
    def db_for_write(self, model, **hints):
        """
        Route write operations to appropriate database.
        
        Same logic as db_for_read to ensure consistency.
        """
        return self.db_for_read(model, **hints)
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Determine if a relation between obj1 and obj2 is allowed.
        
        Relations are allowed if:
        1. Both objects are in the same database
        2. One is in central DB and other in regional DB (for lookups)
        """
        db1 = self.db_for_read(obj1.__class__)
        db2 = self.db_for_read(obj2.__class__)
        
        # Same database - always allow
        if db1 == db2:
            return True
        
        # One in central, one in regional - allow (for auth, etc.)
        if 'default' in (db1, db2):
            return True
        
        # Different regional databases - disallow
        return False
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Determine if migrations should run on a given database.
        
        Args:
            db: Database alias
            app_label: App being migrated
            model_name: Model being migrated (optional)
        
        Returns:
            bool: True if migration should run, False otherwise
        """
        # Central apps only migrate on default database
        if app_label in self.CENTRAL_APPS:
            return db == 'default'
        
        # Regional apps migrate on all databases
        if app_label in self.REGIONAL_APPS:
            return True
        
        # Default: allow migration
        return None


class ReadReplicaRouter:
    """
    Routes read operations to read replicas for better performance.
    
    Usage:
    1. Configure read replica databases (e.g., 'default_replica')
    2. Add this router AFTER RegionalDatabaseRouter
    """
    
    def db_for_read(self, model, **hints):
        """Route reads to replica if available."""
        if hasattr(settings, 'READ_REPLICA_DB'):
            # Don't use replica for write-sensitive models
            if hasattr(model, '_no_read_replica') and model._no_read_replica:
                return None
            return settings.READ_REPLICA_DB
        return None
    
    def db_for_write(self, model, **hints):
        """Always write to primary database."""
        return None
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow all relations (defer to other routers)."""
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Don't migrate on read replicas."""
        if hasattr(settings, 'READ_REPLICA_DB') and db == settings.READ_REPLICA_DB:
            return False
        return None


