from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .models import (
    FiscalYear, FiscalPeriod, ChartOfAccounts, JournalEntry,
    BankAccount, Budget, Tax
)


@login_required
def financial_dashboard(request):
    """Financial management dashboard"""
    # Only allow organization users
    if request.user.role not in ['hospital', 'pharmacy', 'insurance_company']:
        return HttpResponseForbidden("Access denied")

    # Get current fiscal year
    current_fiscal_year = FiscalYear.objects.filter(
        organization=request.user,
        is_closed=False
    ).first()

    # Get open fiscal periods
    open_periods = FiscalPeriod.objects.filter(
        fiscal_year__organization=request.user,
        is_closed=False
    ).order_by('start_date')[:3]

    # Get recent journal entries
    recent_entries = JournalEntry.objects.filter(
        organization=request.user
    ).order_by('-posting_date')[:5]

    # Get total accounts
    total_accounts = ChartOfAccounts.objects.filter(
        organization=request.user,
        is_active=True
    ).count()

    # Get bank accounts
    bank_accounts = BankAccount.objects.filter(
        organization=request.user,
        is_active=True
    )

    context = {
        'current_fiscal_year': current_fiscal_year,
        'open_periods': open_periods,
        'recent_entries': recent_entries,
        'total_accounts': total_accounts,
        'bank_accounts': bank_accounts,
        'page_title': 'Gestion Financière',
    }

    # Determine template based on user role
    role_prefix = request.user.role.replace('_company', '')
    template = f'financial/{role_prefix}_financial.html'

    return render(request, template, context)
