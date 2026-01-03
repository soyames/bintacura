from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'wearable_devices'

router = DefaultRouter()
router.register(r'devices', views.WearableDeviceViewSet, basename='device')
router.register(r'data', views.WearableDataViewSet, basename='data')
router.register(r'sync-logs', views.WearableSyncLogViewSet, basename='sync-log')

urlpatterns = [
    # Web views
    path('', views.WearableDevicesView.as_view(), name='devices'),
    path('connect/<str:device_type>/', views.connect_device, name='wearable_connect'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/devices/<uuid:device_id>/wearable_settings/', views.wearable_settings, name='wearable_settings'),
]
