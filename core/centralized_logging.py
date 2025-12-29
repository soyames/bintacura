"""
Centralized logging system for multi-region deployment
Sends logs from all regions to central hub for monitoring
"""

import logging
import json
from datetime import datetime
from django.conf import settings
from typing import Dict, Any, Optional
import requests
from requests.exceptions import RequestException


class CentralizedLogHandler(logging.Handler):
    """
    Custom logging handler that sends logs to central hub
    """
    
    def __init__(self, central_hub_url: str = None, api_key: str = None):
        super().__init__()
        self.central_hub_url = central_hub_url or getattr(
            settings, 'CENTRAL_HUB_LOGGING_URL', None
        )
        self.api_key = api_key or getattr(
            settings, 'CENTRAL_HUB_API_KEY', None
        )
        self.region_code = getattr(settings, 'REGION_CODE', 'default')
        self.enabled = getattr(settings, 'ENABLE_CENTRALIZED_LOGGING', False)
    
    def emit(self, record: logging.LogRecord):
        """Send log record to central hub"""
        if not self.enabled or not self.central_hub_url:
            return
        
        try:
            log_entry = self.format_log_entry(record)
            self.send_to_central_hub(log_entry)
        except Exception:
            self.handleError(record)
    
    def format_log_entry(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Format log record for transmission"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'region': self.region_code,
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line_number': record.lineno,
            'pathname': record.pathname,
            'exception': self.format_exception(record) if record.exc_info else None,
            'extra': getattr(record, 'extra_data', {})
        }
    
    def format_exception(self, record: logging.LogRecord) -> Optional[Dict]:
        """Format exception information"""
        if not record.exc_info:
            return None
        
        exc_type, exc_value, exc_traceback = record.exc_info
        return {
            'type': exc_type.__name__ if exc_type else None,
            'value': str(exc_value),
            'traceback': self.format(record)
        }
    
    def send_to_central_hub(self, log_entry: Dict[str, Any]):
        """Send log entry to central hub via HTTP"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': self.api_key
            }
            
            response = requests.post(
                self.central_hub_url,
                json=log_entry,
                headers=headers,
                timeout=5
            )
            response.raise_for_status()
        except RequestException:
            pass


class RegionalLogAggregator:
    """
    Service for aggregating logs from multiple regions at central hub
    """
    
    def __init__(self):
        self.logger = logging.getLogger('core.central_logging')
    
    def receive_log(self, log_data: Dict[str, Any]) -> bool:
        """
        Receive and store log from regional deployment
        """
        try:
            region = log_data.get('region', 'unknown')
            level = log_data.get('level', 'INFO')
            message = log_data.get('message', '')
            
            log_message = f"[{region}] {message}"
            
            if level == 'CRITICAL':
                self.logger.critical(log_message, extra={'log_data': log_data})
            elif level == 'ERROR':
                self.logger.error(log_message, extra={'log_data': log_data})
            elif level == 'WARNING':
                self.logger.warning(log_message, extra={'log_data': log_data})
            elif level == 'INFO':
                self.logger.info(log_message, extra={'log_data': log_data})
            else:
                self.logger.debug(log_message, extra={'log_data': log_data})
            
            return True
        except Exception as e:
            self.logger.error(f"Error receiving log: {str(e)}")
            return False
    
    def get_regional_logs(
        self,
        region: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> list:
        """
        Query logs from specific region or all regions
        This would typically query a database or log aggregation service
        """
        pass


def setup_centralized_logging():
    """
    Configure centralized logging for the application
    """
    if not getattr(settings, 'ENABLE_CENTRALIZED_LOGGING', False):
        return
    
    central_handler = CentralizedLogHandler()
    central_handler.setLevel(logging.WARNING)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    central_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(central_handler)
    
    django_logger = logging.getLogger('django')
    django_logger.addHandler(central_handler)
    
    security_logger = logging.getLogger('core.security')
    security_logger.addHandler(central_handler)


class HealthMonitor:
    """
    Monitor health and performance of regional deployments
    """
    
    def __init__(self):
        self.logger = logging.getLogger('core.health_monitor')
    
    def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        from django.db import connection
        from django.db.utils import OperationalError
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {
                'status': 'healthy',
                'database': 'connected'
            }
        except OperationalError as e:
            return {
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': str(e)
            }
    
    def check_cache_health(self) -> Dict[str, Any]:
        """Check cache system health"""
        from django.core.cache import cache
        
        try:
            cache.set('health_check', 'ok', 10)
            value = cache.get('health_check')
            if value == 'ok':
                return {'status': 'healthy', 'cache': 'operational'}
            else:
                return {'status': 'unhealthy', 'cache': 'not_responding'}
        except Exception as e:
            return {
                'status': 'unhealthy',
                'cache': 'error',
                'error': str(e)
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        import psutil
        
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
        except Exception:
            return {}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'region': getattr(settings, 'REGION_CODE', 'default'),
            'database': self.check_database_health(),
            'cache': self.check_cache_health(),
            'metrics': self.get_system_metrics()
        }
    
    def report_to_central_hub(self):
        """Send health status to central hub"""
        if not getattr(settings, 'ENABLE_CENTRALIZED_MONITORING', False):
            return
        
        central_hub_url = getattr(settings, 'CENTRAL_HUB_HEALTH_URL', None)
        api_key = getattr(settings, 'CENTRAL_HUB_API_KEY', None)
        
        if not central_hub_url or not api_key:
            return
        
        try:
            health_status = self.get_health_status()
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': api_key
            }
            
            response = requests.post(
                central_hub_url,
                json=health_status,
                headers=headers,
                timeout=5
            )
            response.raise_for_status()
        except RequestException as e:
            self.logger.error(f"Failed to report health to central hub: {str(e)}")
