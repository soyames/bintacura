from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'financial'

router = DefaultRouter()
router.register(r'fiscal-years', views.FiscalYearViewSet, basename='fiscal-year')
router.register(r'fiscal-periods', views.FiscalPeriodViewSet, basename='fiscal-period')
router.register(r'chart-of-accounts', views.ChartOfAccountsViewSet, basename='chart-of-accounts')
router.register(r'journal-entries', views.JournalEntryViewSet, basename='journal-entry')
router.register(r'bank-accounts', views.BankAccountViewSet, basename='bank-account')
router.register(r'budgets', views.BudgetViewSet, basename='budget')
router.register(r'taxes', views.TaxViewSet, basename='tax')
router.register(r'projects', views.ProjectManagementViewSet, basename='project')
router.register(r'reports', views.FinancialReportsViewSet, basename='financial-report')

urlpatterns = [
    path('', include(router.urls)),
]
