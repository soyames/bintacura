from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'hr'

router = DefaultRouter()
router.register(r'employees', views.EmployeeViewSet, basename='employee')
router.register(r'payroll-periods', views.PayrollPeriodViewSet, basename='payroll-period')
router.register(r'payroll-runs', views.PayrollRunViewSet, basename='payroll-run')
router.register(r'leave-types', views.LeaveTypeViewSet, basename='leave-type')
router.register(r'leave-requests', views.LeaveRequestViewSet, basename='leave-request')
router.register(r'leave-balances', views.LeaveBalanceViewSet, basename='leave-balance')
router.register(r'attendance', views.TimeAndAttendanceViewSet, basename='attendance')
router.register(r'benefits', views.EmployeeBenefitViewSet, basename='benefit')

urlpatterns = [
    path('', include(router.urls)),
]
