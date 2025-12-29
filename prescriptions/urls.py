from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'prescriptions'

router = DefaultRouter()
router.register(r'prescriptions', views.PrescriptionViewSet, basename='prescription')
router.register(r'items', views.PrescriptionItemViewSet, basename='prescriptionitem')
router.register(r'medications', views.MedicationViewSet, basename='medication')

urlpatterns = [
    # Custom endpoint for creating prescriptions (cleaner URL)
    path('create/', views.PrescriptionViewSet.as_view({'post': 'create_prescription'}), name='prescription-create'),
    path('', include(router.urls)),
]
