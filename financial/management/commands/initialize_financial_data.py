from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import date, timedelta
from decimal import Decimal
import calendar

from core.models import Participant
from financial.models import (
    FiscalYear, FiscalPeriod, ChartOfAccounts, BankAccount, Tax
)


class Command(BaseCommand):
    help = 'Initialize financial data for all healthcare organizations'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting financial initialization...'))

        try:
            with transaction.atomic():
                # Get all organizations
                organizations = Participant.objects.filter(
                    role__in=['hospital', 'pharmacy', 'insurance_company']
                )

                for org in organizations:
                    self.stdout.write(f'Initializing: {org.full_name}')

                    # Create fiscal year
                    fiscal_year = self.create_fiscal_year(org)
                    self.create_fiscal_periods(fiscal_year)

                    # Create chart of accounts
                    self.create_chart_of_accounts(org)

                    # Create taxes
                    self.create_taxes(org)

                    self.stdout.write(self.style.SUCCESS(f'  [OK] Completed: {org.full_name}'))

                self.stdout.write(self.style.SUCCESS('\n[SUCCESS] Financial initialization complete!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Error: {str(e)}'))
            raise

    def create_fiscal_year(self, organization):
        """Create current fiscal year"""
        today = date.today()
        year = today.year

        # Create fiscal year from Jan 1 to Dec 31
        fiscal_year, created = FiscalYear.objects.get_or_create(
            organization=organization,
            name=f'FY {year}',
            defaults={
                'start_date': date(year, 1, 1),
                'end_date': date(year, 12, 31),
                'is_closed': False
            }
        )

        if created:
            self.stdout.write(f'  Created fiscal year: {fiscal_year.name}')

        return fiscal_year

    def create_fiscal_periods(self, fiscal_year):
        """Create monthly periods for the fiscal year"""
        year = fiscal_year.start_date.year

        for month in range(1, 13):
            last_day = calendar.monthrange(year, month)[1]

            period, created = FiscalPeriod.objects.get_or_create(
                fiscal_year=fiscal_year,
                period_type='monthly',
                period_number=month,
                defaults={
                    'start_date': date(year, month, 1),
                    'end_date': date(year, month, last_day),
                    'is_closed': False
                }
            )

    def create_chart_of_accounts(self, organization):
        """Create standard chart of accounts for healthcare organizations"""
        accounts = [
            # ASSETS (1000-1999)
            {'code': '1000', 'name': 'Cash and Cash Equivalents', 'type': 'asset', 'subtype': 'current_asset'},
            {'code': '1010', 'name': 'Petty Cash', 'type': 'asset', 'subtype': 'current_asset'},
            {'code': '1100', 'name': 'Bank Account - Operating', 'type': 'asset', 'subtype': 'current_asset'},
            {'code': '1110', 'name': 'Bank Account - Payroll', 'type': 'asset', 'subtype': 'current_asset'},
            {'code': '1200', 'name': 'Accounts Receivable', 'type': 'asset', 'subtype': 'current_asset'},
            {'code': '1210', 'name': 'Patient Receivables', 'type': 'asset', 'subtype': 'current_asset'},
            {'code': '1220', 'name': 'Insurance Receivables', 'type': 'asset', 'subtype': 'current_asset'},
            {'code': '1300', 'name': 'Inventory - Medical Supplies', 'type': 'asset', 'subtype': 'current_asset'},
            {'code': '1310', 'name': 'Inventory - Pharmaceuticals', 'type': 'asset', 'subtype': 'current_asset'},
            {'code': '1320', 'name': 'Inventory - Office Supplies', 'type': 'asset', 'subtype': 'current_asset'},
            {'code': '1400', 'name': 'Prepaid Expenses', 'type': 'asset', 'subtype': 'prepaid_expense'},
            {'code': '1410', 'name': 'Prepaid Insurance', 'type': 'asset', 'subtype': 'prepaid_expense'},
            {'code': '1500', 'name': 'Fixed Assets - Equipment', 'type': 'asset', 'subtype': 'fixed_asset'},
            {'code': '1510', 'name': 'Medical Equipment', 'type': 'asset', 'subtype': 'fixed_asset'},
            {'code': '1520', 'name': 'Office Equipment', 'type': 'asset', 'subtype': 'fixed_asset'},
            {'code': '1530', 'name': 'Vehicles', 'type': 'asset', 'subtype': 'fixed_asset'},
            {'code': '1540', 'name': 'Buildings', 'type': 'asset', 'subtype': 'fixed_asset'},
            {'code': '1600', 'name': 'Accumulated Depreciation', 'type': 'asset', 'subtype': 'fixed_asset'},

            # LIABILITIES (2000-2999)
            {'code': '2000', 'name': 'Accounts Payable', 'type': 'liability', 'subtype': 'current_liability'},
            {'code': '2010', 'name': 'Supplier Payables', 'type': 'liability', 'subtype': 'current_liability'},
            {'code': '2100', 'name': 'Salaries Payable', 'type': 'liability', 'subtype': 'current_liability'},
            {'code': '2110', 'name': 'Wages Payable', 'type': 'liability', 'subtype': 'current_liability'},
            {'code': '2200', 'name': 'Taxes Payable', 'type': 'liability', 'subtype': 'current_liability'},
            {'code': '2210', 'name': 'VAT Payable', 'type': 'liability', 'subtype': 'current_liability'},
            {'code': '2220', 'name': 'Payroll Taxes Payable', 'type': 'liability', 'subtype': 'current_liability'},
            {'code': '2300', 'name': 'Short-term Loans', 'type': 'liability', 'subtype': 'current_liability'},
            {'code': '2400', 'name': 'Accrued Expenses', 'type': 'liability', 'subtype': 'current_liability'},
            {'code': '2500', 'name': 'Long-term Debt', 'type': 'liability', 'subtype': 'long_term_liability'},

            # EQUITY (3000-3999)
            {'code': '3000', 'name': 'Owner\'s Capital', 'type': 'equity', 'subtype': 'capital'},
            {'code': '3100', 'name': 'Retained Earnings', 'type': 'equity', 'subtype': 'retained_earnings'},
            {'code': '3200', 'name': 'Current Year Earnings', 'type': 'equity', 'subtype': 'retained_earnings'},

            # REVENUE (4000-4999)
            {'code': '4000', 'name': 'Patient Service Revenue', 'type': 'revenue', 'subtype': 'operating_revenue'},
            {'code': '4010', 'name': 'Consultation Fees', 'type': 'revenue', 'subtype': 'operating_revenue'},
            {'code': '4020', 'name': 'Treatment Revenue', 'type': 'revenue', 'subtype': 'operating_revenue'},
            {'code': '4030', 'name': 'Surgical Fees', 'type': 'revenue', 'subtype': 'operating_revenue'},
            {'code': '4040', 'name': 'Laboratory Revenue', 'type': 'revenue', 'subtype': 'operating_revenue'},
            {'code': '4050', 'name': 'Radiology Revenue', 'type': 'revenue', 'subtype': 'operating_revenue'},
            {'code': '4100', 'name': 'Pharmaceutical Sales', 'type': 'revenue', 'subtype': 'operating_revenue'},
            {'code': '4200', 'name': 'Insurance Premium Revenue', 'type': 'revenue', 'subtype': 'operating_revenue'},
            {'code': '4300', 'name': 'Other Operating Revenue', 'type': 'revenue', 'subtype': 'operating_revenue'},
            {'code': '4900', 'name': 'Interest Income', 'type': 'revenue', 'subtype': 'non_operating_revenue'},

            # EXPENSES (5000-5999)
            {'code': '5000', 'name': 'Salaries and Wages', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5010', 'name': 'Physician Salaries', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5020', 'name': 'Nursing Salaries', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5030', 'name': 'Administrative Salaries', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5100', 'name': 'Employee Benefits', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5110', 'name': 'Health Insurance', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5120', 'name': 'Retirement Contributions', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5200', 'name': 'Medical Supplies Expense', 'type': 'expense', 'subtype': 'cost_of_goods_sold'},
            {'code': '5210', 'name': 'Pharmaceutical Purchases', 'type': 'expense', 'subtype': 'cost_of_goods_sold'},
            {'code': '5220', 'name': 'Laboratory Supplies', 'type': 'expense', 'subtype': 'cost_of_goods_sold'},
            {'code': '5300', 'name': 'Insurance Claims Paid', 'type': 'expense', 'subtype': 'cost_of_goods_sold'},
            {'code': '5400', 'name': 'Rent Expense', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5500', 'name': 'Utilities Expense', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5510', 'name': 'Electricity', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5520', 'name': 'Water', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5530', 'name': 'Internet and Phone', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5600', 'name': 'Maintenance and Repairs', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5610', 'name': 'Equipment Maintenance', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5620', 'name': 'Building Maintenance', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5700', 'name': 'Depreciation Expense', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5800', 'name': 'Insurance Expense', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5900', 'name': 'Professional Fees', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5910', 'name': 'Legal Fees', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '5920', 'name': 'Accounting Fees', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '6000', 'name': 'Marketing and Advertising', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '6100', 'name': 'Office Supplies', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '6200', 'name': 'Training and Development', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '6300', 'name': 'Travel Expenses', 'type': 'expense', 'subtype': 'operating_expense'},
            {'code': '6900', 'name': 'Interest Expense', 'type': 'expense', 'subtype': 'non_operating_expense'},
        ]

        for acc_data in accounts:
            ChartOfAccounts.objects.get_or_create(
                organization=organization,
                account_code=acc_data['code'],
                defaults={
                    'account_name': acc_data['name'],
                    'account_type': acc_data['type'],
                    'account_subtype': acc_data['subtype'],
                    'is_active': True,
                    'is_system_account': True,
                    'currency': 'XOF'
                }
            )

        self.stdout.write(f'  Created {len(accounts)} accounts')

    def create_taxes(self, organization):
        """Create standard tax configurations"""
        taxes = [
            {
                'name': 'TVA (18%)',
                'code': 'VAT18',
                'type': 'vat',
                'rate': Decimal('18.00'),
            },
            {
                'name': 'Retenue à la source (5%)',
                'code': 'WH5',
                'type': 'withholding_tax',
                'rate': Decimal('5.00'),
            },
        ]

        # Get tax payable account
        tax_payable = ChartOfAccounts.objects.filter(
            organization=organization,
            account_code='2210'
        ).first()

        for tax_data in taxes:
            Tax.objects.get_or_create(
                organization=organization,
                tax_code=tax_data['code'],
                defaults={
                    'tax_name': tax_data['name'],
                    'tax_type': tax_data['type'],
                    'tax_rate': tax_data['rate'],
                    'effective_date': date.today(),
                    'is_active': True,
                    'tax_payable_account': tax_payable
                }
            )

        self.stdout.write(f'  Created {len(taxes)} tax configurations')
