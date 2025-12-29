from django.urls import path
from core import views

app_name = 'insurance_portal'

urlpatterns = [
    path('dashboard/', views.InsuranceDashboardView.as_view(), name='dashboard'),
    path('validation/', views.InsuranceValidationView.as_view(), name='validation'),
    path('claims/', views.InsuranceClaimsView.as_view(), name='claims'),
    path('policies/', views.InsurancePoliciesView.as_view(), name='policies'),
    path('members/', views.InsuranceMembersView.as_view(), name='members'),
    path('staff/', views.InsuranceStaffManagementView.as_view(), name='staff'),
    path('staff/dashboard/', views.InsuranceStaffDashboardView.as_view(), name='staff-dashboard'),
    path('payments/', views.InsurancePaymentsView.as_view(), name='payments'),
    path('network/', views.InsuranceNetworkView.as_view(), name='network'),
    path('reports/', views.InsuranceReportsView.as_view(), name='reports'),
    path('profile/', views.InsuranceProfileView.as_view(), name='profile'),
    path('settings/', views.InsuranceSettingsView.as_view(), name='settings'),
    path('wallet/', __import__('payments.invoice_views', fromlist=['ServiceProviderWalletView']).ServiceProviderWalletView.as_view(), name='wallet'),
    path('invoices/', __import__('payments.invoice_views', fromlist=['InvoiceListView']).InvoiceListView.as_view(), name='invoices'),
    path('view-invoice/<uuid:invoice_id>/', __import__('payments.invoice_views', fromlist=['InvoiceDetailView']).InvoiceDetailView.as_view(), name='view-invoice'),
    path('download-invoice/<uuid:invoice_id>/', __import__('payments.invoice_views', fromlist=['InvoiceDownloadView']).InvoiceDownloadView.as_view(), name='download-invoice'),
    path('transactions/', views.TransactionsView.as_view(), name='transactions'),
    path('financial/', __import__('financial.web_views', fromlist=['financial_dashboard']).financial_dashboard, name='financial'),
    path('hr/', __import__('hr.web_views', fromlist=['hr_dashboard']).hr_dashboard, name='hr'),
]
