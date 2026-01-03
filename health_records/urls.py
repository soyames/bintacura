from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'health_records'

router = DefaultRouter()
router.register(r'records', views.HealthRecordViewSet, basename='record')
# NOTE: Wearable device routes have been moved to the wearable_devices app
router.register(r'documents', views.DocumentUploadViewSet, basename='document')
router.register(r'notes', views.PersonalHealthNoteViewSet, basename='note')

urlpatterns = [
    path('', include(router.urls)),
]
