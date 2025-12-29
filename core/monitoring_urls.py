"""
URLs for centralized monitoring and logging
"""

from django.urls import path
from .monitoring_views import (
    receive_regional_logs,
    receive_health_status,
    get_health_status,
    get_security_config,
    get_region_info
)

app_name = 'monitoring'

urlpatterns = [
    # Central hub endpoints (receive data from regions)
    path('logs/receive/', receive_regional_logs, name='receive_logs'),
    path('health/receive/', receive_health_status, name='receive_health'),
    
    # Local endpoints (query current deployment)
    path('health/', get_health_status, name='health_status'),
    path('security/', get_security_config, name='security_config'),
    path('region/', get_region_info, name='region_info'),
]
