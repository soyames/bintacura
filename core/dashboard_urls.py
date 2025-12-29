from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.MainDashboardView.as_view(), name="main"),
    path(
        "patient/",
        login_required(views.PatientDashboardView.as_view()),
        name="patient",
    ),
    path(
        "doctor/",
        login_required(views.DoctorDashboardView.as_view()),
        name="doctor",
    ),
    path(
        "hospital/",
        login_required(views.HospitalDashboardView.as_view()),
        name="hospital",
    ),
    path(
        "pharmacy/",
        login_required(views.PharmacyDashboardView.as_view()),
        name="pharmacy",
    ),
    path(
        "insurance/",
        login_required(views.InsuranceDashboardView.as_view()),
        name="insurance",
    ),
    path(
        "main/",
        login_required(
            TemplateView.as_view(template_name="dashboards/main_dashboard.html")
        ),
        name="main_alt",
    ),
]
