import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import timedelta

from core.models import Participant, Department
from core.mixins import SyncMixin


class Employee(SyncMixin):
    """Unified employee model across all participant types"""
    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('intern', 'Intern'),
        ('temporary', 'Temporary'),
    ]

    SALARY_TYPE_CHOICES = [
        ('monthly', 'Monthly'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    organization = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='employees',
        help_text="The employer (Hospital/Pharmacy/Insurance Company)"
    )
    user = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='employment_records',
        help_text="The employee's participant account"
    )
    employee_id = models.CharField(max_length=50, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees'
    )

    # Job Information
    job_title = models.CharField(max_length=255)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Compensation
    salary_type = models.CharField(max_length=20, choices=SALARY_TYPE_CHOICES)
    base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='XOF')

    # Banking & Tax
    bank_name = models.CharField(max_length=255, blank=True)
    bank_account_number = models.CharField(max_length=100, blank=True)
    tax_identification_number = models.CharField(max_length=50, blank=True)
    social_security_number = models.CharField(max_length=50, blank=True)

    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(max_length=100, blank=True)

    # Audit
    created_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees_created'
    )

    class Meta:
        db_table = 'hr_employee'
        ordering = ['employee_id']
        unique_together = [['organization', 'employee_id']]
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['employee_id']),
            models.Index(fields=['hire_date']),
        ]

    def __str__(self):
        return f"{self.employee_id} - {self.user.full_name}"

    def get_years_of_service(self):
        """Calculate years of service"""
        end_date = self.termination_date or timezone.now().date()
        delta = end_date - self.hire_date
        return delta.days / 365.25


class PayrollPeriod(SyncMixin):
    """Payroll period definition"""
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-Weekly'),
        ('semi_monthly', 'Semi-Monthly'),
        ('monthly', 'Monthly'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('open', 'Open'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('paid', 'Paid'),
        ('closed', 'Closed'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    organization = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='payroll_periods'
    )
    period_name = models.CharField(max_length=100, help_text="e.g., January 2025 Payroll")
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    pay_date = models.DateField(help_text="Actual payment date")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    # Processing metadata
    processed_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_periods_processed'
    )
    processed_at = models.DateTimeField(null=True, blank=True)

    # Audit

    class Meta:
        db_table = 'hr_payroll_period'
        ordering = ['-start_date']
        unique_together = [['organization', 'period_name']]
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.period_name} ({self.start_date} to {self.end_date})"


class PayrollRun(SyncMixin):
    """Payroll execution for individual employees"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    payroll_period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name='payroll_runs'
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='payroll_runs'
    )

    # Hours worked (for hourly employees)
    regular_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    overtime_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Earnings
    base_pay = models.DecimalField(max_digits=12, decimal_places=2)
    overtime_pay = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    bonus = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    allowances = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Housing, transport, etc."
    )
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2)

    # Deductions
    total_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Net Pay
    net_pay = models.DecimalField(max_digits=12, decimal_places=2)

    # Payment tracking
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        help_text="Bank transfer, cash, mobile money, etc."
    )
    payment_reference = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    # Audit
    approved_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_runs_approved'
    )

    class Meta:
        db_table = 'hr_payroll_run'
        ordering = ['-created_at']
        unique_together = [['payroll_period', 'employee']]
        indexes = [
            models.Index(fields=['payroll_period', 'payment_status']),
            models.Index(fields=['employee', 'payment_status']),
        ]

    def __str__(self):
        return f"Payroll for {self.employee.user.full_name} - {self.payroll_period.period_name}"

    def calculate_totals(self):
        """Calculate gross pay and net pay"""
        self.gross_pay = (
            self.base_pay +
            self.overtime_pay +
            self.bonus +
            self.commission +
            self.allowances
        )

        # Calculate total deductions from related PayrollDeduction objects
        deductions_total = self.deductions.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        self.total_deductions = deductions_total
        self.net_pay = self.gross_pay - self.total_deductions
        self.save()


class PayrollDeduction(SyncMixin):
    """Payroll deductions (tax, insurance, loans, etc.)"""
    DEDUCTION_TYPE_CHOICES = [
        ('income_tax', 'Income Tax'),
        ('social_security', 'Social Security'),
        ('pension', 'Pension Contribution'),
        ('health_insurance', 'Health Insurance'),
        ('loan_repayment', 'Loan Repayment'),
        ('advance_repayment', 'Advance Repayment'),
        ('union_dues', 'Union Dues'),
        ('garnishment', 'Garnishment'),
        ('other', 'Other'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name='deductions'
    )
    deduction_type = models.CharField(max_length=30, choices=DEDUCTION_TYPE_CHOICES)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    is_mandatory = models.BooleanField(default=True)

    # Audit

    class Meta:
        db_table = 'hr_payroll_deduction'
        ordering = ['deduction_type']

    def __str__(self):
        return f"{self.description} - {self.amount}"


class LeaveType(SyncMixin):
    """Types of leave (annual, sick, maternity, etc.)"""
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    organization = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='leave_types'
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    description = models.TextField(blank=True)

    # Entitlement
    days_per_year = models.IntegerField(
        help_text="Number of days entitled per year"
    )
    max_carryover_days = models.IntegerField(
        default=0,
        help_text="Maximum days that can be carried over to next year"
    )

    # Configuration
    is_paid = models.BooleanField(default=True)
    requires_documentation = models.BooleanField(
        default=False,
        help_text="Requires supporting documents (e.g., medical certificate)"
    )
    requires_approval = models.BooleanField(default=True)
    minimum_notice_days = models.IntegerField(
        default=0,
        help_text="Minimum days of notice required before leave start"
    )
    maximum_consecutive_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum consecutive days allowed"
    )

    # Eligibility
    requires_minimum_service_months = models.IntegerField(
        default=0,
        help_text="Minimum months of service required to be eligible"
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Audit

    class Meta:
        db_table = 'hr_leave_type'
        ordering = ['name']
        unique_together = [['organization', 'code']]

    def __str__(self):
        return f"{self.name} ({self.days_per_year} days/year)"


class LeaveRequest(SyncMixin):
    """Employee leave requests"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='leave_requests'
    )

    # Leave details
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        help_text="Can include half days (e.g., 2.5 days)"
    )
    reason = models.TextField()

    # Supporting documents
    attachment_url = models.URLField(blank=True)

    # Approval workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_requests_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Handover
    handover_to = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handover_requests',
        help_text="Employee handling duties during absence"
    )
    handover_notes = models.TextField(blank=True)

    # Contact during leave
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_address = models.TextField(blank=True)

    # Audit

    class Meta:
        db_table = 'hr_leave_request'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.employee.user.full_name} - {self.leave_type.name} ({self.start_date} to {self.end_date})"

    def clean(self):
        """Validate leave request"""
        from django.core.exceptions import ValidationError

        if self.end_date < self.start_date:
            raise ValidationError("End date must be after start date")

        # Check if employee has sufficient balance
        if self.pk is None:  # Only check on creation
            balance = LeaveBalance.objects.filter(
                employee=self.employee,
                leave_type=self.leave_type,
                year=self.start_date.year
            ).first()

            if balance and balance.remaining_days < self.days_requested:
                raise ValidationError(
                    f"Insufficient leave balance. Available: {balance.remaining_days} days"
                )


class LeaveBalance(SyncMixin):
    """Employee leave balance tracking"""
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_balances'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='leave_balances'
    )
    year = models.IntegerField()

    # Balance tracking
    entitled_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        help_text="Total days entitled for the year"
    )
    carried_over_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal('0.0'),
        help_text="Days carried over from previous year"
    )
    used_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal('0.0')
    )
    pending_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal('0.0'),
        help_text="Days in pending leave requests"
    )
    remaining_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        help_text="Available days remaining"
    )

    # Adjustments
    adjustment_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal('0.0'),
        help_text="Manual adjustments (positive or negative)"
    )
    adjustment_reason = models.TextField(blank=True)

    # Audit

    class Meta:
        db_table = 'hr_leave_balance'
        ordering = ['-year', 'employee']
        unique_together = [['employee', 'leave_type', 'year']]
        indexes = [
            models.Index(fields=['employee', 'year']),
            models.Index(fields=['year']),
        ]

    def __str__(self):
        return f"{self.employee.user.full_name} - {self.leave_type.name} {self.year}: {self.remaining_days} days"

    def calculate_remaining(self):
        """Calculate remaining days"""
        total_available = (
            self.entitled_days +
            self.carried_over_days +
            self.adjustment_days
        )
        self.remaining_days = total_available - self.used_days - self.pending_days
        self.save()


class TimeAndAttendance(SyncMixin):
    """Clock in/out tracking"""
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )

    # Clock times
    clock_in = models.DateTimeField()
    clock_out = models.DateTimeField(null=True, blank=True)

    # Calculated hours
    total_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    regular_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    overtime_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Break time
    break_duration_minutes = models.IntegerField(
        default=0,
        help_text="Total break time in minutes"
    )

    # Location tracking (optional)
    clock_in_location = models.CharField(max_length=255, blank=True)
    clock_out_location = models.CharField(max_length=255, blank=True)
    clock_in_ip = models.GenericIPAddressField(null=True, blank=True)
    clock_out_ip = models.GenericIPAddressField(null=True, blank=True)

    # Status flags
    is_late = models.BooleanField(default=False)
    is_early_departure = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)

    # Notes
    notes = models.TextField(blank=True)

    # Audit
    approved_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_approvals'
    )

    class Meta:
        db_table = 'hr_time_attendance'
        ordering = ['-clock_in']
        indexes = [
            models.Index(fields=['employee', 'clock_in']),
            models.Index(fields=['clock_in']),
        ]

    def __str__(self):
        return f"{self.employee.user.full_name} - {self.clock_in.date()}"

    def calculate_hours(self):
        """Calculate total hours worked"""
        if self.clock_out:
            duration = self.clock_out - self.clock_in
            total_minutes = duration.total_seconds() / 60

            # Subtract break time
            worked_minutes = total_minutes - self.break_duration_minutes

            self.total_hours = Decimal(str(worked_minutes / 60))

            # Determine regular vs overtime (assuming 8-hour workday)
            if self.total_hours > 8:
                self.regular_hours = Decimal('8.00')
                self.overtime_hours = self.total_hours - Decimal('8.00')
            else:
                self.regular_hours = self.total_hours
                self.overtime_hours = Decimal('0.00')

            self.save()


class EmployeeBenefit(SyncMixin):
    """Employee benefits configuration"""
    BENEFIT_TYPE_CHOICES = [
        ('health_insurance', 'Health Insurance'),
        ('life_insurance', 'Life Insurance'),
        ('pension', 'Pension Plan'),
        ('transportation', 'Transportation Allowance'),
        ('housing', 'Housing Allowance'),
        ('meal', 'Meal Allowance'),
        ('education', 'Education Assistance'),
        ('other', 'Other'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='benefits'
    )
    benefit_type = models.CharField(max_length=30, choices=BENEFIT_TYPE_CHOICES)
    benefit_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Cost
    employer_contribution = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    employee_contribution = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Effective dates
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Provider information
    provider_name = models.CharField(max_length=255, blank=True)
    policy_number = models.CharField(max_length=100, blank=True)

    # Audit

    class Meta:
        db_table = 'hr_employee_benefit'
        ordering = ['employee', 'benefit_type']

    def __str__(self):
        return f"{self.employee.user.full_name} - {self.benefit_name}"
