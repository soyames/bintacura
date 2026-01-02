from rest_framework import serializers
from .models import (
    Employee, PayrollPeriod, PayrollRun, PayrollDeduction,
    LeaveType, LeaveRequest, LeaveBalance, TimeAndAttendance,
    EmployeeBenefit
)
from core.models import Participant, Department


class EmployeeSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.full_name', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    years_of_service = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    employment_type_display = serializers.CharField(source='get_employment_type_display', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'organization', 'organization_name', 'user', 'user_name', 'user_email',
            'employee_id', 'department', 'department_name', 'job_title',
            'employment_type', 'employment_type_display', 'hire_date', 'termination_date',
            'status', 'status_display', 'salary_type', 'base_salary', 'currency',
            'bank_name', 'bank_account_number', 'tax_identification_number', 'social_security_number',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship',
            'years_of_service', 'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_years_of_service(self, obj) -> dict:
        return round(obj.get_years_of_service(), 2)


class PayrollDeductionSerializer(serializers.ModelSerializer):
    deduction_type_display = serializers.CharField(source='get_deduction_type_display', read_only=True)

    class Meta:
        model = PayrollDeduction
        fields = [
            'id', 'payroll_run', 'deduction_type', 'deduction_type_display',
            'description', 'amount', 'is_mandatory', 'created_at'
        ]
        read_only_fields = ['created_at']


class PayrollPeriodSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.full_name', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.full_name', read_only=True)
    total_runs = serializers.SerializerMethodField()
    total_gross_pay = serializers.SerializerMethodField()
    total_net_pay = serializers.SerializerMethodField()

    class Meta:
        model = PayrollPeriod
        fields = [
            'id', 'organization', 'organization_name', 'period_name', 'frequency', 'frequency_display',
            'start_date', 'end_date', 'pay_date', 'status', 'status_display',
            'processed_by', 'processed_by_name', 'processed_at',
            'total_runs', 'total_gross_pay', 'total_net_pay',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['processed_at', 'created_at', 'updated_at']

    def get_total_runs(self, obj) -> int:
        return obj.payroll_runs.count()

    def get_total_gross_pay(self, obj) -> float:
        from django.db.models import Sum
        total = obj.payroll_runs.aggregate(total=Sum('gross_pay'))['total']
        return float(total) if total else 0.0

    def get_total_net_pay(self, obj) -> float:
        from django.db.models import Sum
        total = obj.payroll_runs.aggregate(total=Sum('net_pay'))['total']
        return float(total) if total else 0.0


class PayrollRunSerializer(serializers.ModelSerializer):
    payroll_period_name = serializers.CharField(source='payroll_period.period_name', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_id_number = serializers.CharField(source='employee.employee_id', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    deductions = PayrollDeductionSerializer(many=True, read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)

    class Meta:
        model = PayrollRun
        fields = [
            'id', 'payroll_period', 'payroll_period_name', 'employee', 'employee_name', 'employee_id_number',
            'regular_hours', 'overtime_hours', 'base_pay', 'overtime_pay', 'bonus', 'commission', 'allowances',
            'gross_pay', 'total_deductions', 'net_pay', 'deductions',
            'payment_status', 'payment_status_display', 'payment_method', 'payment_reference', 'paid_at',
            'approved_by', 'approved_by_name', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['gross_pay', 'net_pay', 'created_at', 'updated_at']


class LeaveTypeSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.full_name', read_only=True)

    class Meta:
        model = LeaveType
        fields = [
            'id', 'organization', 'organization_name', 'name', 'code', 'description',
            'days_per_year', 'max_carryover_days', 'is_paid', 'requires_documentation',
            'requires_approval', 'minimum_notice_days', 'maximum_consecutive_days',
            'requires_minimum_service_months', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    handover_to_name = serializers.CharField(source='handover_to.user.full_name', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'employee_name', 'employee_id', 'leave_type', 'leave_type_name',
            'start_date', 'end_date', 'days_requested', 'reason', 'attachment_url',
            'status', 'status_display', 'submitted_at', 'approved_by', 'approved_by_name',
            'approved_at', 'rejection_reason',
            'handover_to', 'handover_to_name', 'handover_notes',
            'contact_phone', 'contact_address',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['submitted_at', 'approved_at', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate leave request"""
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError("End date must be after start date")
        return data


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    total_available = serializers.SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'employee', 'employee_name', 'employee_id', 'leave_type', 'leave_type_name', 'year',
            'entitled_days', 'carried_over_days', 'used_days', 'pending_days', 'remaining_days',
            'total_available', 'adjustment_days', 'adjustment_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['remaining_days', 'created_at', 'updated_at']

    def get_total_available(self, obj) -> float:
        return float(obj.entitled_days + obj.carried_over_days + obj.adjustment_days)


class TimeAndAttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    work_date = serializers.SerializerMethodField()

    class Meta:
        model = TimeAndAttendance
        fields = [
            'id', 'employee', 'employee_name', 'employee_id',
            'clock_in', 'clock_out', 'work_date',
            'total_hours', 'regular_hours', 'overtime_hours', 'break_duration_minutes',
            'clock_in_location', 'clock_out_location', 'clock_in_ip', 'clock_out_ip',
            'is_late', 'is_early_departure', 'is_approved', 'approved_by', 'approved_by_name',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['total_hours', 'regular_hours', 'overtime_hours', 'created_at', 'updated_at']

    def get_work_date(self, obj) -> dict:
        return obj.clock_in.date()


class EmployeeBenefitSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    benefit_type_display = serializers.CharField(source='get_benefit_type_display', read_only=True)
    total_contribution = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeBenefit
        fields = [
            'id', 'employee', 'employee_name', 'benefit_type', 'benefit_type_display',
            'benefit_name', 'description', 'employer_contribution', 'employee_contribution',
            'total_contribution', 'start_date', 'end_date', 'is_active',
            'provider_name', 'policy_number',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_total_contribution(self, obj) -> float:
        return float(obj.employer_contribution + obj.employee_contribution)
