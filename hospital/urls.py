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
    path('transport/requests/', views.transport_requests, name='transport-requests'),
    path('transport/requests/<uuid:request_id>/accept/', views.accept_transport_request, name='accept-transport'),
    path('transport/requests/<uuid:request_id>/assign/', views.assign_staff_to_transport, name='assign-staff-transport'),
    path('transport/requests/<uuid:request_id>/transfer/', views.transfer_transport_request, name='transfer-transport'),
]
