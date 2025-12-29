from django.contrib import admin
from .models import (
    FiscalYear, FiscalPeriod, ChartOfAccounts, JournalEntry, JournalEntryLine,
    BankAccount, Budget, BudgetLine, Tax, ProjectManagement
)


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 2
    fields = ['account', 'description', 'debit_amount', 'credit_amount', 'department']


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'start_date', 'end_date', 'is_closed']
    list_filter = ['is_closed', 'organization']
    search_fields = ['name', 'organization__full_name']
    date_hierarchy = 'start_date'


@admin.register(FiscalPeriod)
class FiscalPeriodAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'fiscal_year', 'period_type', 'period_number', 'start_date', 'end_date', 'is_closed']
    list_filter = ['period_type', 'is_closed', 'fiscal_year']
    search_fields = ['fiscal_year__name']


@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(admin.ModelAdmin):
    list_display = ['account_code', 'account_name', 'account_type', 'account_subtype', 'organization', 'is_active']
    list_filter = ['account_type', 'account_subtype', 'is_active', 'organization']
    search_fields = ['account_code', 'account_name', 'organization__full_name']
    ordering = ['account_code']


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_number', 'posting_date', 'entry_type', 'description', 'status', 'organization']
    list_filter = ['status', 'entry_type', 'posting_date', 'organization']
    search_fields = ['entry_number', 'description', 'reference_number']
    date_hierarchy = 'posting_date'
    inlines = [JournalEntryLineInline]
    readonly_fields = ['posted_by', 'posted_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('entry_number', 'organization', 'entry_type', 'posting_date', 'fiscal_period')
        }),
        ('Details', {
            'fields': ('reference_number', 'description', 'notes')
        }),
        ('Status', {
            'fields': ('status', 'posted_by', 'posted_at')
        }),
    )


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['account_name', 'bank_name', 'account_number', 'account_type', 'current_balance', 'organization', 'is_active']
    list_filter = ['account_type', 'is_active', 'organization']
    search_fields = ['account_name', 'bank_name', 'account_number', 'organization__full_name']


class BudgetLineInline(admin.TabularInline):
    model = BudgetLine
    extra = 1
    fields = ['account', 'department', 'q1_amount', 'q2_amount', 'q3_amount', 'q4_amount', 'annual_amount']
    readonly_fields = ['annual_amount']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'fiscal_year', 'organization', 'status', 'approved_by', 'approved_at']
    list_filter = ['status', 'fiscal_year', 'organization']
    search_fields = ['name', 'description', 'organization__full_name']
    inlines = [BudgetLineInline]


@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ['tax_name', 'tax_code', 'tax_type', 'tax_rate', 'effective_date', 'is_active', 'organization']
    list_filter = ['tax_type', 'is_active', 'organization']
    search_fields = ['tax_name', 'tax_code']
    date_hierarchy = 'effective_date'


@admin.register(ProjectManagement)
class ProjectManagementAdmin(admin.ModelAdmin):
    list_display = ['project_code', 'project_name', 'status', 'start_date', 'end_date', 'budget_amount', 'manager', 'organization']
    list_filter = ['status', 'organization']
    search_fields = ['project_code', 'project_name', 'manager__full_name']
    date_hierarchy = 'start_date'
