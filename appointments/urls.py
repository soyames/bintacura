from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'appointments'

router = DefaultRouter()
router.register(r'appointments', views.AppointmentViewSet, basename='appointment')
router.register(r'availability', views.AvailabilityViewSet, basename='availability')
router.register(r'queue', views.AppointmentQueueViewSet, basename='queue')

urlpatterns = [
    path('', include(router.urls)),
]
