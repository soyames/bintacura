from rest_framework import serializers
from .models import (
    FiscalYear, FiscalPeriod, ChartOfAccounts, JournalEntry, JournalEntryLine,
    BankAccount, Budget, BudgetLine, Tax, ProjectManagement
)
from core.serializers import ParticipantSerializer


class FiscalYearSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.full_name', read_only=True)
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = FiscalYear
        fields = '__all__'

    def get_is_current(self, obj) -> dict:
        from django.utils import timezone
        today = timezone.now().date()
        return obj.start_date <= today <= obj.end_date


class FiscalPeriodSerializer(serializers.ModelSerializer):
    fiscal_year_name = serializers.CharField(source='fiscal_year.name', read_only=True)

    class Meta:
        model = FiscalPeriod
        fields = '__all__'


class ChartOfAccountsSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.full_name', read_only=True)
    parent_account_name = serializers.CharField(source='parent_account.account_name', read_only=True)
    current_balance = serializers.SerializerMethodField()
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    account_subtype_display = serializers.CharField(source='get_account_subtype_display', read_only=True)

    class Meta:
        model = ChartOfAccounts
        fields = '__all__'

    def get_current_balance(self, obj) -> float:
        return float(obj.get_balance())


class JournalEntryLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source='account.account_code', read_only=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)

    class Meta:
        model = JournalEntryLine
        fields = '__all__'


class JournalEntrySerializer(serializers.ModelSerializer):
    line_items = JournalEntryLineSerializer(many=True, read_only=True)
    organization_name = serializers.CharField(source='organization.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    posted_by_name = serializers.CharField(source='posted_by.full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    entry_type_display = serializers.CharField(source='get_entry_type_display', read_only=True)
    total_debit = serializers.SerializerMethodField()
    total_credit = serializers.SerializerMethodField()
    is_balanced = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = '__all__'

    def get_total_debit(self, obj) -> float:
        return float(sum([line.debit_amount for line in obj.line_items.all()]))

    def get_total_credit(self, obj) -> float:
        return float(sum([line.credit_amount for line in obj.line_items.all()]))

    def get_is_balanced(self, obj) -> dict:
        return self.get_total_debit(obj) == self.get_total_credit(obj)


class BankAccountSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.full_name', read_only=True)
    gl_account_code = serializers.CharField(source='gl_account.account_code', read_only=True)
    gl_account_name = serializers.CharField(source='gl_account.account_name', read_only=True)
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)

    class Meta:
        model = BankAccount
        fields = '__all__'


class BudgetLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source='account.account_code', read_only=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)

    class Meta:
        model = BudgetLine
        fields = '__all__'


class BudgetSerializer(serializers.ModelSerializer):
    line_items = BudgetLineSerializer(many=True, read_only=True)
    organization_name = serializers.CharField(source='organization.full_name', read_only=True)
    fiscal_year_name = serializers.CharField(source='fiscal_year.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_budget = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = '__all__'

    def get_total_budget(self, obj) -> float:
        return float(sum([line.annual_amount for line in obj.line_items.all()]))


class TaxSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.full_name', read_only=True)
    tax_payable_account_name = serializers.CharField(source='tax_payable_account.account_name', read_only=True, allow_null=True)
    tax_expense_account_name = serializers.CharField(source='tax_expense_account.account_name', read_only=True, allow_null=True)
    tax_type_display = serializers.CharField(source='get_tax_type_display', read_only=True)

    class Meta:
        model = Tax
        fields = '__all__'


class ProjectManagementSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.full_name', read_only=True)
    manager_name = serializers.CharField(source='manager.full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    actual_spend = serializers.SerializerMethodField()
    budget_variance = serializers.SerializerMethodField()

    class Meta:
        model = ProjectManagement
        fields = '__all__'

    def get_actual_spend(self, obj) -> float:
        # Calculate actual spend from journal entries
        from django.db.models import Sum
        actual = JournalEntryLine.objects.filter(
            project=obj,
            journal_entry__status='posted'
        ).aggregate(total=Sum('debit_amount'))['total'] or 0
        return float(actual)

    def get_budget_variance(self, obj) -> float:
        actual = self.get_actual_spend(obj)
        return float(obj.budget_amount - actual)
