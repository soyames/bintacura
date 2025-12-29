from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'transport_api'

router = DefaultRouter()
router.register(r'requests', views.TransportRequestViewSet, basename='request')
router.register(r'providers', views.TransportProviderViewSet, basename='provider')

urlpatterns = [
    path('', include(router.urls)),
    path('book/', views.TransportRequestView.as_view(), name='transport_request_page'),
    path('tracking/<uuid:request_id>/', views.TransportTrackingView.as_view(), name='transport_tracking'),
]
