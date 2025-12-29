from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "patient_api"

# API Router for patient data
router = DefaultRouter()
router.register(r"data", views.PatientDataViewSet, basename="patient-data")
router.register(r"dependents", views.DependentProfileViewSet, basename="dependent")

urlpatterns = [
    path("", include(router.urls)),
]
