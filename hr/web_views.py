from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .models import (
    Employee, PayrollPeriod, PayrollRun, LeaveType,
    LeaveRequest, TimeAndAttendance
)
from django.db.models import Count


@login_required
def hr_dashboard(request):
    """HR & Payroll management dashboard"""
    # Only allow organization users
    if request.user.role not in ['hospital', 'pharmacy', 'insurance_company']:
        return HttpResponseForbidden("Access denied")

    # Get active employees count
    total_employees = Employee.objects.filter(
        organization=request.user,
        status='active'
    ).count()

    # Get employees by employment type
    employment_stats = Employee.objects.filter(
        organization=request.user,
        status='active'
    ).values('employment_type').annotate(count=Count('id'))

    # Get current payroll period
    from django.utils import timezone
    today = timezone.now().date()
    current_payroll_period = PayrollPeriod.objects.filter(
        organization=request.user,
        start_date__lte=today,
        end_date__gte=today
    ).first()

    # Get pending leave requests
    pending_leave_requests = LeaveRequest.objects.filter(
        employee__organization=request.user,
        status='pending'
    ).count()

    # Get recent employees
    recent_employees = Employee.objects.filter(
        organization=request.user
    ).order_by('-created_at')[:5]

    # Get leave types
    leave_types = LeaveType.objects.filter(
        organization=request.user,
        is_active=True
    )

    context = {
        'total_employees': total_employees,
        'employment_stats': employment_stats,
        'current_payroll_period': current_payroll_period,
        'pending_leave_requests': pending_leave_requests,
        'recent_employees': recent_employees,
        'leave_types': leave_types,
        'page_title': 'Ressources Humaines & Paie',
    }

    # Determine template based on user role
    role_prefix = request.user.role.replace('_company', '')
    template = f'hr/{role_prefix}_hr.html'

    return render(request, template, context)
