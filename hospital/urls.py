from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'hospital_api'

router = DefaultRouter()
router.register(r'staff', views.HospitalStaffViewSet, basename='staff')
router.register(r'beds', views.BedViewSet, basename='bed')
router.register(r'admissions', views.AdmissionViewSet, basename='admission')
router.register(r'tasks', views.DepartmentTaskViewSet, basename='task')
router.register(r'departments', views.DepartmentViewSet, basename='department')
router.register(r'analytics', views.HospitalAnalyticsViewSet, basename='hospital-analytics')

urlpatterns = [
    path('', include(router.urls)),
]
