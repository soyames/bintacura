from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'health_records'

router = DefaultRouter()
router.register(r'records', views.HealthRecordViewSet, basename='record')
router.register(r'wearable', views.WearableDataViewSet, basename='wearable')

urlpatterns = [
    path('', include(router.urls)),
]
