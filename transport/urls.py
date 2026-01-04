from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'transport_api'

router = DefaultRouter()
router.register(r'requests', views.TransportRequestViewSet, basename='request')
router.register(r'providers', views.TransportProviderViewSet, basename='provider')
router.register(r'hospital/requests', views.HospitalTransportViewSet, basename='hospital-request')

urlpatterns = [
    path('', include(router.urls)),
    path('book/', views.TransportRequestView.as_view(), name='transport_request_page'),
    path('my-requests/', views.PatientTransportRequestsView.as_view(), name='patient_requests_list'),
    path('tracking/<uuid:request_id>/', views.TransportTrackingView.as_view(), name='transport_tracking'),
    
    # Hospital transport dashboard
    path('hospital/dashboard/', views.HospitalTransportDashboardView.as_view(), name='hospital_dashboard'),
    
    # Legacy hospital endpoints (kept for compatibility)
    path('hospital/requests/', views.hospital_transport_requests, name='hospital_requests'),
    path('hospital/requests/<uuid:request_id>/accept/', views.accept_transport_request, name='accept_request'),
    path('hospital/requests/<uuid:request_id>/update_status/', views.update_transport_status, name='update_status'),
    path('hospital/requests/<uuid:request_id>/decline/', views.decline_transport_request, name='decline_request'),
]
