from django.urls import path
from core import views
from pharmacy import service_views

app_name = "pharmacy"

urlpatterns = [
    path("dashboard/", views.PharmacyDashboardView.as_view(), name="dashboard"),
    
    # Service management
    path("services/create/", service_views.create_pharmacy_service, name="create_service"),
    path("services/list/", service_views.list_pharmacy_services, name="list_services"),
    path("services/<uuid:service_id>/edit/", service_views.edit_pharmacy_service, name="edit_service"),
    path("services/<uuid:service_id>/delete/", service_views.delete_pharmacy_service, name="delete_service"),
    path(
        "prescriptions/",
        views.PharmacyPrescriptionsView.as_view(),
        name="prescriptions",
    ),
    path("inventory/", views.PharmacyInventoryView.as_view(), name="inventory"),
    path("orders/", views.PharmacyOrdersView.as_view(), name="orders"),
    path("suppliers/", views.PharmacySuppliersView.as_view(), name="suppliers"),
    path("sales/", views.PharmacySalesView.as_view(), name="sales"),
    path("reports/", views.PharmacyReportsView.as_view(), name="reports"),
    path("profile/", views.PharmacyProfileView.as_view(), name="profile"),
    path("settings/", views.PharmacySettingsView.as_view(), name="settings"),
    path("wallet/", __import__('payments.invoice_views', fromlist=['ServiceProviderWalletView']).ServiceProviderWalletView.as_view(), name="wallet"),
    path("invoices/", __import__('payments.invoice_views', fromlist=['InvoiceListView']).InvoiceListView.as_view(), name="invoices"),
    path("view-invoice/<uuid:invoice_id>/", __import__('payments.invoice_views', fromlist=['InvoiceDetailView']).InvoiceDetailView.as_view(), name="view-invoice"),
    path("download-invoice/<uuid:invoice_id>/", __import__('payments.invoice_views', fromlist=['InvoiceDownloadView']).InvoiceDownloadView.as_view(), name="download-invoice"),
    path("transactions/", views.TransactionsView.as_view(), name="transactions"),
    path("patients/", views.PharmacyPatientsView.as_view(), name="patients"),
    path("services/", views.PharmacyServicesView.as_view(), name="services"),
    path("staff/", views.PharmacyStaffManagementView.as_view(), name="staff"),
    path("bonus-configs/", views.PharmacyBonusConfigView.as_view(), name="bonus-configs"),
    path("staff/pharmacist/dashboard/", views.PharmacyStaffPharmacistDashboardView.as_view(), name="pharmacy_staff_pharmacist_dashboard"),
    path("staff/cashier/dashboard/", views.PharmacyCashierDashboardView.as_view(), name="cashier_dashboard"),
    path("staff/inventory-clerk/dashboard/", views.PharmacyInventoryClerkDashboardView.as_view(), name="inventory_clerk_dashboard"),
    path("staff/delivery/dashboard/", views.PharmacyDeliveryDashboardView.as_view(), name="delivery_dashboard"),
    path("staff/manager/dashboard/", views.PharmacyManagerDashboardView.as_view(), name="pharmacy_manager_dashboard"),
    path("prescription/<int:prescription_id>/", views.PrescriptionDetailView.as_view(), name="prescription_detail"),
    path("prescription/<int:prescription_id>/process/", views.ProcessPrescriptionView.as_view(), name="prescription_process"),
    path("prescription/<int:prescription_id>/mark-ready/", views.MarkPrescriptionReadyView.as_view(), name="prescription_mark_ready"),
    path("prescription/<int:prescription_id>/deliver/", views.DeliverPrescriptionView.as_view(), name="prescription_deliver"),
    path("financial/", __import__('financial.web_views', fromlist=['financial_dashboard']).financial_dashboard, name="financial"),
    path("hr/", __import__('hr.web_views', fromlist=['hr_dashboard']).hr_dashboard, name="hr"),
]
