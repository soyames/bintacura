"""
URL Configuration for Sync API Endpoints
"""

from django.urls import path
from . import views

app_name = 'sync'

urlpatterns = [
    # Cloud sync endpoints (called by local instances)
    path('push/', views.push_events, name='push_events'),
    path('pull/', views.pull_events, name='pull_events'),
    path('status/', views.sync_status, name='sync_status'),
]
