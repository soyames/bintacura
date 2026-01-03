from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "patient_api"

# API Router for patient data
router = DefaultRouter()
router.register(r"data", views.PatientDataViewSet, basename="patient-data")
router.register(r"dependents", views.DependentProfileViewSet, basename="dependent")
router.register(r"preventive-reminders", views.PreventiveCareReminderViewSet, basename="preventive-reminder")
router.register(r"health-notes", views.PersonalHealthNoteViewSet, basename="health-note")

urlpatterns = [
    path("", include(router.urls)),
]
