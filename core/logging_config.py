"""
Centralized logging configuration for multi-region deployment
"""
import os
from pathlib import Path


def get_logging_config(base_dir, region='default'):
    """
    Get logging configuration for the deployment region
    """
    logs_dir = Path(base_dir) / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
            },
            'simple': {
                'format': '{levelname} {message}',
                'style': '{',
            },
            'json': {
                '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
            } if region != 'default' else {
                'format': '{levelname} {asctime} {module} {message}',
                'style': '{',
            },
        },
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse',
            },
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
            'file': {
                'level': 'WARNING',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': logs_dir / f'{region}_security.log',
                'maxBytes': 1024 * 1024 * 10,  # 10MB
                'backupCount': 5,
                'formatter': 'verbose',
            },
            'error_file': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': logs_dir / f'{region}_errors.log',
                'maxBytes': 1024 * 1024 * 10,  # 10MB
                'backupCount': 5,
                'formatter': 'verbose',
            },
            'app_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': logs_dir / f'{region}_app.log',
                'maxBytes': 1024 * 1024 * 10,  # 10MB
                'backupCount': 5,
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console', 'error_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.request': {
                'handlers': ['console', 'error_file'],
                'level': 'ERROR',
                'propagate': False,
            },
            'django.security': {
                'handlers': ['console', 'file'],
                'level': 'WARNING',
                'propagate': False,
            },
            'core.security': {
                'handlers': ['console', 'file'],
                'level': 'WARNING',
                'propagate': False,
            },
            'BINTACURA': {
                'handlers': ['console', 'app_file'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
    
    return config

