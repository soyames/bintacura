from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "doctor_api"

# API Router for doctor data
router = DefaultRouter()
router.register(r"data", views.DoctorDataViewSet, basename="doctor-data")
router.register(r"affiliations", views.DoctorAffiliationViewSet, basename="affiliations")

urlpatterns = [
    path("", include(router.urls)),
    # Additional API endpoints
    path("patients/", views.doctor_patients_api, name="patients"),
    path("consultations/", views.doctor_consultations_api, name="consultations"),
    path("consultations/call/", views.call_patient_api, name="call-patient"),
    path("consultations/complete/", views.complete_consultation_api, name="complete-consultation"),
]
