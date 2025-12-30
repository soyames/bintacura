from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Q
from decimal import Decimal
import uuid
from core.models import Participant
from core.mixins import SyncMixin


class FiscalYear(SyncMixin):
    """Defines fiscal years for financial reporting"""
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    organization = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='fiscal_years')
    name = models.CharField(max_length=100, help_text="e.g., FY 2024-2025")
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    closed_by = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='closed_fiscal_years')
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'fiscal_years'
        unique_together = ['organization', 'name']
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.organization.full_name} - {self.name}"


class FiscalPeriod(SyncMixin):
    """Monthly/quarterly periods within fiscal years"""
    PERIOD_TYPE_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='periods')
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPE_CHOICES, default='monthly')
    period_number = models.IntegerField(help_text="1-12 for monthly, 1-4 for quarterly")
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    closed_by = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='closed_periods')
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'fiscal_periods'
        unique_together = ['fiscal_year', 'period_type', 'period_number']
        ordering = ['fiscal_year', 'period_number']

    def __str__(self):
        return f"{self.fiscal_year.name} - Period {self.period_number}"


class ChartOfAccounts(SyncMixin):
    """Master list of all accounts in the organization"""
    ACCOUNT_TYPE_CHOICES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]

    ACCOUNT_SUBTYPE_CHOICES = [
        # Assets
        ('current_asset', 'Current Asset'),
        ('fixed_asset', 'Fixed Asset'),
        ('intangible_asset', 'Intangible Asset'),
        ('prepaid_expense', 'Prepaid Expense'),
        # Liabilities
        ('current_liability', 'Current Liability'),
        ('long_term_liability', 'Long-term Liability'),
        # Equity
        ('capital', 'Capital'),
        ('retained_earnings', 'Retained Earnings'),
        ('drawings', 'Drawings'),
        # Revenue
        ('operating_revenue', 'Operating Revenue'),
        ('non_operating_revenue', 'Non-operating Revenue'),
        # Expense
        ('operating_expense', 'Operating Expense'),
        ('non_operating_expense', 'Non-operating Expense'),
        ('cost_of_goods_sold', 'Cost of Goods Sold'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    organization = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='chart_of_accounts')
    account_code = models.CharField(max_length=50, help_text="Unique account code e.g., 1100, 2200")
    account_name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    account_subtype = models.CharField(max_length=50, choices=ACCOUNT_SUBTYPE_CHOICES)
    parent_account = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_accounts')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_system_account = models.BooleanField(default=False, help_text="System-managed, cannot be deleted")
    currency = models.CharField(max_length=3, default='XOF')
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    opening_balance_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'chart_of_accounts'
        unique_together = ['organization', 'account_code']
        ordering = ['account_code']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['account_type']),
        ]

    def __str__(self):
        return f"{self.account_code} - {self.account_name}"

    def get_balance(self, as_of_date=None):
        """Calculate current balance for this account"""
        query = self.ledger_entries.all()
        if as_of_date:
            query = query.filter(journal_entry__posting_date__lte=as_of_date)

        debits = query.aggregate(total=Sum('debit_amount'))['total'] or Decimal('0')
        credits = query.aggregate(total=Sum('credit_amount'))['total'] or Decimal('0')

        # Assets and Expenses increase with debits
        if self.account_type in ['asset', 'expense']:
            return debits - credits
        # Liabilities, Equity, Revenue increase with credits
        else:
            return credits - debits


class JournalEntry(SyncMixin):
    """Journal entries are the fundamental accounting transactions"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('void', 'Void'),
    ]

    ENTRY_TYPE_CHOICES = [
        ('manual', 'Manual Entry'),
        ('sales', 'Sales'),
        ('purchase', 'Purchase'),
        ('payment', 'Payment'),
        ('receipt', 'Receipt'),
        ('payroll', 'Payroll'),
        ('depreciation', 'Depreciation'),
        ('adjustment', 'Adjustment'),
        ('opening_balance', 'Opening Balance'),
        ('closing', 'Closing Entry'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    organization = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='journal_entries')
    entry_number = models.CharField(max_length=50, unique=True)
    entry_type = models.CharField(max_length=30, choices=ENTRY_TYPE_CHOICES, default='manual')
    posting_date = models.DateField()
    fiscal_period = models.ForeignKey(FiscalPeriod, on_delete=models.PROTECT, related_name='journal_entries', null=True)
    reference_number = models.CharField(max_length=100, blank=True, help_text="Invoice #, Check #, etc.")
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Source document tracking
    source_model = models.CharField(max_length=100, blank=True)
    source_id = models.UUIDField(null=True, blank=True)

    # Approval workflow
    created_by = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, related_name='created_journal_entries')
    posted_by = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='posted_journal_entries')
    posted_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'journal_entries'
        ordering = ['-posting_date', '-entry_number']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['posting_date']),
            models.Index(fields=['entry_type']),
        ]

    def __str__(self):
        return f"{self.entry_number} - {self.posting_date}"

    def post(self, posted_by):
        """Post the journal entry to the general ledger"""
        if self.status == 'posted':
            raise ValueError("Entry already posted")

        # Verify debits equal credits
        total_debits = self.line_items.aggregate(total=Sum('debit_amount'))['total'] or Decimal('0')
        total_credits = self.line_items.aggregate(total=Sum('credit_amount'))['total'] or Decimal('0')

        if total_debits != total_credits:
            raise ValueError(f"Debits ({total_debits}) must equal credits ({total_credits})")

        self.status = 'posted'
        self.posted_by = posted_by
        self.posted_at = timezone.now()
        self.save()


class JournalEntryLine(SyncMixin):
    """Individual line items in a journal entry (debits and credits)"""
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='line_items')
    account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, related_name='ledger_entries')
    description = models.CharField(max_length=500, blank=True)
    debit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    credit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # Additional tracking
    department = models.ForeignKey('core.Department', on_delete=models.SET_NULL, null=True, blank=True)
    project = models.ForeignKey('ProjectManagement', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'journal_entry_lines'
        ordering = ['journal_entry', 'id']

    def __str__(self):
        if self.debit_amount > 0:
            return f"DR {self.account.account_code} {self.debit_amount}"
        return f"CR {self.account.account_code} {self.credit_amount}"


class BankAccount(SyncMixin):
    """Organization bank accounts"""
    ACCOUNT_TYPE_CHOICES = [
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('money_market', 'Money Market'),
        ('credit_line', 'Line of Credit'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    organization = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='bank_accounts')
    account_name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=100)
    account_type = models.CharField(max_length=30, choices=ACCOUNT_TYPE_CHOICES)
    currency = models.CharField(max_length=3, default='XOF')
    iban = models.CharField(max_length=50, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)
    branch_name = models.CharField(max_length=255, blank=True)
    gl_account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, related_name='bank_accounts')
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    last_reconciled_date = models.DateField(null=True, blank=True)
    last_reconciled_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'bank_accounts'
        ordering = ['account_name']

    def __str__(self):
        return f"{self.bank_name} - {self.account_name} ({self.account_number[-4:]})"


class Budget(SyncMixin):
    """Budget planning and control"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    organization = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='budgets')
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='budgets')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_budgets')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, related_name='created_budgets')

    class Meta:
        db_table = 'budgets'
        ordering = ['-fiscal_year', 'name']

    def __str__(self):
        return f"{self.name} - {self.fiscal_year.name}"


class BudgetLine(SyncMixin):
    """Individual line items in a budget"""
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='line_items')
    account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, related_name='budget_lines')
    department = models.ForeignKey('core.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='budget_lines')

    # Budget amounts by period
    q1_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    q2_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    q3_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    q4_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    annual_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'budget_lines'
        unique_together = ['budget', 'account', 'department']

    def __str__(self):
        return f"{self.budget.name} - {self.account.account_name}"

    def save(self, *args, **kwargs):
        self.annual_amount = self.q1_amount + self.q2_amount + self.q3_amount + self.q4_amount
        super().save(*args, **kwargs)


class Tax(SyncMixin):
    """Tax rates and configurations"""
    TAX_TYPE_CHOICES = [
        ('sales_tax', 'Sales Tax'),
        ('vat', 'VAT'),
        ('withholding_tax', 'Withholding Tax'),
        ('income_tax', 'Income Tax'),
        ('payroll_tax', 'Payroll Tax'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    organization = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='taxes')
    tax_name = models.CharField(max_length=255)
    tax_code = models.CharField(max_length=50)
    tax_type = models.CharField(max_length=30, choices=TAX_TYPE_CHOICES)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage (e.g., 18.00 for 18%)")
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # GL accounts for tax
    tax_payable_account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, related_name='tax_payable_for', null=True)
    tax_expense_account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, related_name='tax_expense_for', null=True, blank=True)

    description = models.TextField(blank=True)

    class Meta:
        db_table = 'taxes'
        unique_together = ['organization', 'tax_code']
        ordering = ['tax_name']

    def __str__(self):
        return f"{self.tax_name} ({self.tax_rate}%)"


class ProjectManagement(SyncMixin):
    """Project/cost center tracking for expenses"""
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    organization = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='projects')
    project_code = models.CharField(max_length=50)
    project_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    budget_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    manager = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, related_name='managed_projects')

    class Meta:
        db_table = 'projects'
        unique_together = ['organization', 'project_code']
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.project_code} - {self.project_name}"
