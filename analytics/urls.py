from django.urls import path, include
from django.shortcuts import render
from rest_framework.routers import DefaultRouter
from . import views

app_name = "analytics"

router = DefaultRouter()
router.register(
    r"platform-statistics",
    views.PlatformStatisticsViewSet,
    basename="platform-statistics",
)
router.register(
    r"predictive",
    views.PredictiveAnalyticsViewSet,
    basename="predictive-analytics",
)

urlpatterns = [
    path("", include(router.urls)),
    path("admin/overview/", views.AdminAnalyticsView.as_view(), name="admin-overview"),
    path("admin/participant-growth/", views.ParticipantGrowthView.as_view(), name="participant-growth"),
    path("admin/revenue/", views.RevenueAnalyticsView.as_view(), name="revenue"),
    path(
        "admin/role-distribution/",
        views.RoleDistributionView.as_view(),
        name="role-distribution",
    ),
    path("admin/activities/", views.RecentActivitiesView.as_view(), name="activities"),
    path(
        "admin/top-providers/", views.TopProvidersView.as_view(), name="top-providers"
    ),
    path(
        "admin/geographic/",
        views.GeographicDistributionView.as_view(),
        name="geographic",
    ),
    path(
        "doctor/dashboard/",
        views.DoctorAnalyticsView.as_view(),
        name="doctor-dashboard",
    ),
    path(
        "hospital/dashboard/",
        views.HospitalAnalyticsView.as_view(),
        name="hospital-dashboard",
    ),
    path(
        "pharmacy/dashboard/",
        views.PharmacyAnalyticsView.as_view(),
        name="pharmacy-dashboard",
    ),
    path(
        "insurance/dashboard/",
        views.InsuranceAnalyticsView.as_view(),
        name="insurance-dashboard",
    ),
    path(
        "patient/dashboard/",
        views.PatientAnalyticsView.as_view(),
        name="patient-dashboard",
    ),
    path(
        "patient/detailed/",
        views.DetailedPatientAnalyticsView.as_view(),
        name="patient-detailed",
    ),
    path(
        "doctor/detailed/",
        views.DetailedDoctorAnalyticsView.as_view(),
        name="doctor-detailed",
    ),
    path(
        "hospital/detailed/",
        views.DetailedHospitalAnalyticsView.as_view(),
        name="hospital-detailed",
    ),
    path(
        "pharmacy/detailed/",
        views.DetailedPharmacyAnalyticsView.as_view(),
        name="pharmacy-detailed",
    ),
    path('survey/', views.survey_stats_view, name='survey_stats'),
    path('survey/submit/', views.survey_submit_view, name='survey_submit'),
    path('survey/thank-you/', views.survey_thank_you_view, name='survey_thank_you'),
    path('survey/statistics/', views.SurveyStatisticsAPIView.as_view(), name='survey_statistics_api'),
    path('admin/survey/export/<str:file_format>/', views.export_survey_data_view, name='survey_export'),
]
