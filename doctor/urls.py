from django.urls import path, include
from core import views
from . import views as doctor_views

# Import API URLs (will be included from main urls.py with namespace)
from . import api_urls

app_name = "doctor"

# Web URLs only
urlpatterns = [
    path("dashboard/", views.DoctorDashboardView.as_view(), name="dashboard"),
    path("patients/", views.DoctorPatientsView.as_view(), name="patients"),
    path("appointments/", views.DoctorAppointmentsView.as_view(), name="appointments"),
    path("queue/", doctor_views.DoctorQueueView.as_view(), name="queue"),
    path(
        "consultations/", views.DoctorConsultationsView.as_view(), name="consultations"
    ),
    path(
        "prescriptions/", views.DoctorPrescriptionsView.as_view(), name="prescriptions"
    ),
    path("schedule/", views.DoctorScheduleView.as_view(), name="schedule"),
    path("calendar/", views.DoctorCalendarView.as_view(), name="calendar"),
    path("profile/", views.DoctorProfileView.as_view(), name="profile"),
    path("settings/", views.DoctorSettingsView.as_view(), name="settings"),
    path("wallet/", __import__('payments.invoice_views', fromlist=['ServiceProviderWalletView']).ServiceProviderWalletView.as_view(), name="wallet"),
    path("invoices/", __import__('payments.invoice_views', fromlist=['InvoiceListView']).InvoiceListView.as_view(), name="invoices"),
    path("view-invoice/<uuid:invoice_id>/", __import__('payments.invoice_views', fromlist=['InvoiceDetailView']).InvoiceDetailView.as_view(), name="view-invoice"),
    path("download-invoice/<uuid:invoice_id>/", __import__('payments.invoice_views', fromlist=['InvoiceDownloadView']).InvoiceDownloadView.as_view(), name="download-invoice"),
    path("transactions/", views.TransactionsView.as_view(), name="transactions"),
    path("analytics/", doctor_views.DoctorAnalyticsView.as_view(), name="analytics"),
    path("laboratory/", views.DoctorLaboratoryView.as_view(), name="laboratory"),
    path("referrals/", views.DoctorReferralsView.as_view(), name="referrals"),
    path("certificates/", views.DoctorCertificatesView.as_view(), name="certificates"),
    path(
        "new-prescription/",
        views.DoctorNewPrescriptionView.as_view(),
        name="new-prescription",
    ),
    path(
        "medical-record/",
        views.DoctorMedicalRecordView.as_view(),
        name="medical-record",
    ),
    path(
        "medical-record/<uuid:patient_id>/",
        views.DoctorMedicalRecordView.as_view(),
        name="medical-record-patient",
    ),
    path("lab-request/", views.DoctorLabRequestView.as_view(), name="lab-request"),
    path("referral/", views.DoctorReferralView.as_view(), name="referral"),
    path("services/", views.DoctorServicesView.as_view(), name="services"),
    path("bonuses/", views.DoctorBonusesView.as_view(), name="bonuses"),
    path(
        "video-consultation/<uuid:appointment_id>/",
        views.DoctorVideoConsultationView.as_view(),
        name="video_consultation",
    ),
]

