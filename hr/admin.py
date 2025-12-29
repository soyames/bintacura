from django.contrib import admin
from .models import (
    Employee, PayrollPeriod, PayrollRun, PayrollDeduction,
    LeaveType, LeaveRequest, LeaveBalance, TimeAndAttendance,
    EmployeeBenefit
)


class PayrollDeductionInline(admin.TabularInline):
    model = PayrollDeduction
    extra = 1
    fields = ['deduction_type', 'description', 'amount', 'is_mandatory']


class EmployeeBenefitInline(admin.TabularInline):
    model = EmployeeBenefit
    extra = 0
    fields = ['benefit_type', 'benefit_name', 'employer_contribution', 'employee_contribution', 'start_date', 'end_date', 'is_active']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'user', 'organization', 'job_title', 'employment_type', 'status', 'hire_date']
    list_filter = ['organization', 'status', 'employment_type', 'hire_date']
    search_fields = ['employee_id', 'user__full_name', 'user__email', 'job_title']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [EmployeeBenefitInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('organization', 'user', 'employee_id', 'department')
        }),
        ('Job Details', {
            'fields': ('job_title', 'employment_type', 'hire_date', 'termination_date', 'status')
        }),
        ('Compensation', {
            'fields': ('salary_type', 'base_salary', 'currency')
        }),
        ('Banking & Tax', {
            'fields': ('bank_name', 'bank_account_number', 'tax_identification_number', 'social_security_number')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ['period_name', 'organization', 'frequency', 'start_date', 'end_date', 'pay_date', 'status']
    list_filter = ['organization', 'status', 'frequency', 'start_date']
    search_fields = ['period_name']
    readonly_fields = ['processed_at', 'created_at', 'updated_at']

    fieldsets = (
        ('Period Information', {
            'fields': ('organization', 'period_name', 'frequency')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'pay_date')
        }),
        ('Status', {
            'fields': ('status', 'processed_by', 'processed_at')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ['employee', 'payroll_period', 'gross_pay', 'total_deductions', 'net_pay', 'payment_status', 'paid_at']
    list_filter = ['payroll_period', 'payment_status', 'paid_at']
    search_fields = ['employee__user__full_name', 'employee__employee_id']
    readonly_fields = ['gross_pay', 'net_pay', 'created_at', 'updated_at']
    inlines = [PayrollDeductionInline]

    fieldsets = (
        ('Payroll Information', {
            'fields': ('payroll_period', 'employee')
        }),
        ('Hours Worked', {
            'fields': ('regular_hours', 'overtime_hours')
        }),
        ('Earnings', {
            'fields': ('base_pay', 'overtime_pay', 'bonus', 'commission', 'allowances', 'gross_pay')
        }),
        ('Deductions', {
            'fields': ('total_deductions',)
        }),
        ('Net Pay', {
            'fields': ('net_pay',)
        }),
        ('Payment', {
            'fields': ('payment_status', 'payment_method', 'payment_reference', 'paid_at', 'approved_by')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'organization', 'days_per_year', 'is_paid', 'requires_approval', 'is_active']
    list_filter = ['organization', 'is_paid', 'requires_approval', 'is_active']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('organization', 'name', 'code', 'description')
        }),
        ('Entitlement', {
            'fields': ('days_per_year', 'max_carryover_days')
        }),
        ('Configuration', {
            'fields': ('is_paid', 'requires_documentation', 'requires_approval', 'minimum_notice_days', 'maximum_consecutive_days')
        }),
        ('Eligibility', {
            'fields': ('requires_minimum_service_months',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'days_requested', 'status', 'submitted_at']
    list_filter = ['status', 'leave_type', 'start_date']
    search_fields = ['employee__user__full_name', 'employee__employee_id', 'reason']
    readonly_fields = ['submitted_at', 'approved_at', 'created_at', 'updated_at']

    fieldsets = (
        ('Leave Information', {
            'fields': ('employee', 'leave_type', 'start_date', 'end_date', 'days_requested', 'reason')
        }),
        ('Supporting Documents', {
            'fields': ('attachment_url',)
        }),
        ('Approval', {
            'fields': ('status', 'submitted_at', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Handover', {
            'fields': ('handover_to', 'handover_notes'),
            'classes': ('collapse',)
        }),
        ('Contact During Leave', {
            'fields': ('contact_phone', 'contact_address'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'year', 'entitled_days', 'used_days', 'pending_days', 'remaining_days']
    list_filter = ['year', 'leave_type']
    search_fields = ['employee__user__full_name', 'employee__employee_id']
    readonly_fields = ['remaining_days', 'created_at', 'updated_at']

    fieldsets = (
        ('Balance Information', {
            'fields': ('employee', 'leave_type', 'year')
        }),
        ('Balance Details', {
            'fields': ('entitled_days', 'carried_over_days', 'used_days', 'pending_days', 'remaining_days')
        }),
        ('Adjustments', {
            'fields': ('adjustment_days', 'adjustment_reason'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TimeAndAttendance)
class TimeAndAttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'clock_in', 'clock_out', 'total_hours', 'regular_hours', 'overtime_hours', 'is_approved']
    list_filter = ['is_approved', 'is_late', 'is_early_departure', 'clock_in']
    search_fields = ['employee__user__full_name', 'employee__employee_id']
    readonly_fields = ['total_hours', 'regular_hours', 'overtime_hours', 'created_at', 'updated_at']

    fieldsets = (
        ('Attendance Information', {
            'fields': ('employee', 'clock_in', 'clock_out')
        }),
        ('Hours Calculated', {
            'fields': ('total_hours', 'regular_hours', 'overtime_hours', 'break_duration_minutes')
        }),
        ('Location Tracking', {
            'fields': ('clock_in_location', 'clock_out_location', 'clock_in_ip', 'clock_out_ip'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_late', 'is_early_departure', 'is_approved', 'approved_by')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmployeeBenefit)
class EmployeeBenefitAdmin(admin.ModelAdmin):
    list_display = ['employee', 'benefit_type', 'benefit_name', 'employer_contribution', 'employee_contribution', 'start_date', 'is_active']
    list_filter = ['benefit_type', 'is_active', 'start_date']
    search_fields = ['employee__user__full_name', 'benefit_name', 'provider_name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Benefit Information', {
            'fields': ('employee', 'benefit_type', 'benefit_name', 'description')
        }),
        ('Cost', {
            'fields': ('employer_contribution', 'employee_contribution')
        }),
        ('Effective Dates', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Provider', {
            'fields': ('provider_name', 'policy_number'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
