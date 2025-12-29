from django.urls import path
from core import views
from hospital import views as hospital_views

app_name = "hospital"

urlpatterns = [
    path("dashboard/", views.HospitalDashboardView.as_view(), name="dashboard"),
    path("patients/", views.HospitalPatientsView.as_view(), name="patients"),
    path("admissions/", views.HospitalAdmissionsView.as_view(), name="admissions"),
    path("departments/", views.HospitalDepartmentsView.as_view(), name="departments"),
    path("staff/", views.HospitalStaffView.as_view(), name="staff"),
    path("beds/", views.HospitalBedsView.as_view(), name="beds"),
    path("reports/", views.HospitalReportsView.as_view(), name="reports"),
    path("profile/", views.HospitalProfileView.as_view(), name="profile"),
    path("settings/", views.HospitalSettingsView.as_view(), name="settings"),
    path("wallet/", __import__('payments.invoice_views', fromlist=['ServiceProviderWalletView']).ServiceProviderWalletView.as_view(), name="wallet"),
    path("invoices/", __import__('payments.invoice_views', fromlist=['InvoiceListView']).InvoiceListView.as_view(), name="invoices"),
    path("view-invoice/<uuid:invoice_id>/", __import__('payments.invoice_views', fromlist=['InvoiceDetailView']).InvoiceDetailView.as_view(), name="view-invoice"),
    path("download-invoice/<uuid:invoice_id>/", __import__('payments.invoice_views', fromlist=['InvoiceDownloadView']).InvoiceDownloadView.as_view(), name="download-invoice"),
    path("transactions/", views.TransactionsView.as_view(), name="transactions"),
    path("equipment/", views.HospitalEquipmentView.as_view(), name="equipment"),
    path("services/", views.HospitalServicesView.as_view(), name="services"),
    path(
        "appointments/", views.HospitalAppointmentsView.as_view(), name="appointments"
    ),
    path("queue/", hospital_views.HospitalQueueView.as_view(), name="queue"),
    path("staff/receptionist/dashboard/", views.ReceptionistDashboardView.as_view(), name="receptionist_dashboard"),
    path("staff/receptionist/appointments/", views.ReceptionistAppointmentsView.as_view(), name="receptionist_appointments"),
    path("staff/receptionist/patients/", views.ReceptionistPatientsView.as_view(), name="receptionist_patients"),
    path("staff/nurse/dashboard/", views.NurseDashboardView.as_view(), name="nurse_dashboard"),
    path("staff/lab-technician/dashboard/", views.LabTechnicianDashboardView.as_view(), name="lab_technician_dashboard"),
    path("staff/pharmacist/dashboard/", views.HospitalPharmacistDashboardView.as_view(), name="hospital_pharmacist_dashboard"),
    path("staff/administrator/dashboard/", views.HospitalAdministratorDashboardView.as_view(), name="hospital_administrator_dashboard"),
    path("financial/", __import__('financial.web_views', fromlist=['financial_dashboard']).financial_dashboard, name="financial"),
    path("hr/", __import__('hr.web_views', fromlist=['hr_dashboard']).hr_dashboard, name="hr"),
]
