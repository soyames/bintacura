from django.urls import path, include
from core import views
from django.views.generic import TemplateView
from patient import views as patient_views

app_name = "patient"

# Web URLs only
urlpatterns = [    
    # API Endpoints
    path("api/prescriptions/", patient_views.PrescriptionsAPIView.as_view(), name="api_prescriptions"),
    
    path("dashboard/", views.PatientDashboardView.as_view(), name="dashboard"),
    path("profile/", views.PatientProfileView.as_view(), name="profile"),
    path(
        "beneficiaries/", views.PatientBeneficiariesView.as_view(), name="beneficiaries"
    ),
    path("settings/", views.PatientSettingsView.as_view(), name="settings"),
    path("invoices/", __import__('payments.invoice_views', fromlist=['InvoiceListView']).InvoiceListView.as_view(), name="invoices"),
    path("view-invoice/", __import__('payments.invoice_views', fromlist=['InvoiceDetailView']).InvoiceDetailView.as_view(), name="view-invoice"),
    path("view-invoice/<uuid:invoice_id>/", __import__('payments.invoice_views', fromlist=['InvoiceDetailView']).InvoiceDetailView.as_view(), name="view-invoice-detail"),
    path("download-invoice/<uuid:invoice_id>/", __import__('payments.invoice_views', fromlist=['InvoiceDownloadView']).InvoiceDownloadView.as_view(), name="download-invoice"),
    path("transactions/", views.TransactionsView.as_view(), name="transactions"),
    path(
        "my-appointments/", views.MyAppointmentsView.as_view(), name="my_appointments"
    ),
    path(
        "transport-request/",
        lambda request: __import__('django.shortcuts', fromlist=['redirect']).redirect('/api/v1/transport/book/'),
        name="transport_request",
    ),
    path("ai-assistant/", __import__('ai.views', fromlist=['AIAssistantPageView']).AIAssistantPageView.as_view(), name="ai_assistant"),
    path("symptom-checker/", __import__('ai.views', fromlist=['SymptomCheckerPageView']).SymptomCheckerPageView.as_view(), name="symptom_checker"),
    path("health-insights/", __import__('ai.views', fromlist=['HealthInsightsPageView']).HealthInsightsPageView.as_view(), name="health_insights"),
    path("health-records/", views.HealthRecordsView.as_view(), name="health_records"),
    path("prescriptions/", views.PrescriptionsView.as_view(), name="prescriptions"),
    path("telemedicine/", views.TelemedicineView.as_view(), name="telemedicine"),
    path(
        "insurance-subscription/",
        views.InsuranceSubscriptionView.as_view(),
        name="insurance_subscription",
    ),
    path(
        "insurance/claims/",
        views.PatientInsuranceClaimsView.as_view(),
        name="insurance_claims",
    ),
    path(
        "insurance/invoices/",
        views.PatientInsuranceInvoicesView.as_view(),
        name="insurance_invoices",
    ),
    path(
        "book-appointment/",
        views.BookAppointmentView.as_view(),
        name="book_appointment",
    ),
    path(
        "reschedule-appointment/<uuid:appointment_id>/",
        views.RescheduleAppointmentView.as_view(),
        name="reschedule_appointment",
    ),
    # path("providers/", views.ProvidersView.as_view(), name="providers"),  # Deprecated - using role-specific views
    path(
        "book-telemedicine/",
        views.BookTelemedicineView.as_view(),
        name="book_telemedicine",
    ),
    path(
        "video-consultation/<uuid:appointment_id>/",
        views.PatientVideoConsultationView.as_view(),
        name="video_consultation",
    ),
    path(
        "consultation/<uuid:appointment_id>/feedback/",
        __import__('core.views', fromlist=['ConsultationFeedbackView']).ConsultationFeedbackView.as_view(),
        name="consultation_feedback",
    ),
    path("api/profile/", views.PatientProfileAPIView.as_view(), name="api_profile"),
    path(
        "api/beneficiaries/",
        views.BeneficiariesAPIView.as_view(),
        name="api_beneficiaries",
    ),
    path(
        "api/beneficiaries/<uuid:pk>/",
        views.BeneficiaryDetailAPIView.as_view(),
        name="api_beneficiary_detail",
    ),
    path("forum/", views.PatientForumView.as_view(), name="forum"),
    path("hospitals/", views.PatientHospitalsView.as_view(), name="hospitals"),
    path(
        "api/hospitals/",
        views.HospitalsAPIView.as_view(),
        name="api_hospitals",
    ),
    path(
        "api/hospital-appointments/",
        views.HospitalAppointmentsAPIView.as_view(),
        name="api_hospital_appointments",
    ),
    path(
        "api/available-slots/",
        views.AvailableSlotsAPIView.as_view(),
        name="api_available_slots",
    ),
    path("pharmacies/", views.PatientPharmaciesView.as_view(), name="pharmacies"),
    path("pharmacy-catalog/", views.PharmacyCatalogView.as_view(), name="pharmacy_catalog"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path(
        "api/pharmacies/",
        views.PharmaciesAPIView.as_view(),
        name="api_pharmacies",
    ),
    path(
        "api/pharmacy-catalog/",
        views.PharmacyCatalogAPIView.as_view(),
        name="api_pharmacy_catalog",
    ),

    path(
        "api/pharmacy-orders/",
        views.PharmacyOrdersAPIView.as_view(),
        name="api_pharmacy_orders",
    ),
    
    # Preventive Care Reminders
    path("preventive-reminders/", patient_views.PreventiveRemindersView.as_view(), name="preventive_reminders"),
    
    # Health Journal (Personal Health Notes)
    path("health-journal/", patient_views.HealthJournalView.as_view(), name="health_journal"),
    
    # Wearable Devices
    path("wearable-devices/", include(("wearable_devices.urls", "wearable_devices"))),
]
