from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import date, timedelta
from decimal import Decimal
import calendar

from core.models import Participant
from hr.models import LeaveType, PayrollPeriod


class Command(BaseCommand):
    help = 'Initialize HR data for all healthcare organizations'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting HR initialization...'))

        try:
            with transaction.atomic():
                # Get all organizations
                organizations = Participant.objects.filter(
                    role__in=['hospital', 'pharmacy', 'insurance_company']
                )

                for org in organizations:
                    self.stdout.write(f'Initializing HR for: {org.full_name}')

                    # Create leave types
                    self.create_leave_types(org)

                    # Create payroll periods for current year
                    self.create_payroll_periods(org)

                    self.stdout.write(self.style.SUCCESS(f'  [OK] Completed: {org.full_name}'))

                self.stdout.write(self.style.SUCCESS('\n[SUCCESS] HR initialization complete!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Error: {str(e)}'))
            raise

    def create_leave_types(self, organization):
        """Create standard leave types for the organization"""
        leave_types = [
            {
                'name': 'Annual Leave',
                'code': 'ANNUAL',
                'description': 'Annual vacation leave',
                'days_per_year': 21,
                'max_carryover_days': 5,
                'is_paid': True,
                'requires_documentation': False,
                'requires_approval': True,
                'minimum_notice_days': 7,
                'maximum_consecutive_days': 14,
                'requires_minimum_service_months': 6,
            },
            {
                'name': 'Sick Leave',
                'code': 'SICK',
                'description': 'Leave for illness or injury',
                'days_per_year': 10,
                'max_carryover_days': 0,
                'is_paid': True,
                'requires_documentation': True,
                'requires_approval': True,
                'minimum_notice_days': 0,
                'maximum_consecutive_days': None,
                'requires_minimum_service_months': 0,
            },
            {
                'name': 'Maternity Leave',
                'code': 'MATERNITY',
                'description': 'Maternity leave for expecting mothers',
                'days_per_year': 90,
                'max_carryover_days': 0,
                'is_paid': True,
                'requires_documentation': True,
                'requires_approval': True,
                'minimum_notice_days': 30,
                'maximum_consecutive_days': None,
                'requires_minimum_service_months': 6,
            },
            {
                'name': 'Paternity Leave',
                'code': 'PATERNITY',
                'description': 'Paternity leave for new fathers',
                'days_per_year': 7,
                'max_carryover_days': 0,
                'is_paid': True,
                'requires_documentation': True,
                'requires_approval': True,
                'minimum_notice_days': 7,
                'maximum_consecutive_days': None,
                'requires_minimum_service_months': 6,
            },
            {
                'name': 'Compassionate Leave',
                'code': 'COMPASSIONATE',
                'description': 'Leave for family emergencies or bereavement',
                'days_per_year': 5,
                'max_carryover_days': 0,
                'is_paid': True,
                'requires_documentation': True,
                'requires_approval': True,
                'minimum_notice_days': 0,
                'maximum_consecutive_days': 5,
                'requires_minimum_service_months': 0,
            },
            {
                'name': 'Study Leave',
                'code': 'STUDY',
                'description': 'Leave for professional development and examinations',
                'days_per_year': 10,
                'max_carryover_days': 0,
                'is_paid': True,
                'requires_documentation': True,
                'requires_approval': True,
                'minimum_notice_days': 14,
                'maximum_consecutive_days': 10,
                'requires_minimum_service_months': 12,
            },
            {
                'name': 'Unpaid Leave',
                'code': 'UNPAID',
                'description': 'Unpaid leave for personal reasons',
                'days_per_year': 30,
                'max_carryover_days': 0,
                'is_paid': False,
                'requires_documentation': False,
                'requires_approval': True,
                'minimum_notice_days': 14,
                'maximum_consecutive_days': None,
                'requires_minimum_service_months': 6,
            },
        ]

        for leave_data in leave_types:
            LeaveType.objects.get_or_create(
                organization=organization,
                code=leave_data['code'],
                defaults={
                    'name': leave_data['name'],
                    'description': leave_data['description'],
                    'days_per_year': leave_data['days_per_year'],
                    'max_carryover_days': leave_data['max_carryover_days'],
                    'is_paid': leave_data['is_paid'],
                    'requires_documentation': leave_data['requires_documentation'],
                    'requires_approval': leave_data['requires_approval'],
                    'minimum_notice_days': leave_data['minimum_notice_days'],
                    'maximum_consecutive_days': leave_data['maximum_consecutive_days'],
                    'requires_minimum_service_months': leave_data['requires_minimum_service_months'],
                    'is_active': True,
                }
            )

        self.stdout.write(f'  Created {len(leave_types)} leave types')

    def create_payroll_periods(self, organization):
        """Create monthly payroll periods for the current year"""
        today = date.today()
        year = today.year

        # Create monthly payroll periods
        for month in range(1, 13):
            last_day = calendar.monthrange(year, month)[1]
            start_date = date(year, month, 1)
            end_date = date(year, month, last_day)

            # Pay date is typically 25th of the month (or last day if 25th doesn't exist)
            pay_day = min(25, last_day)
            pay_date = date(year, month, pay_day)

            period_name = f"{calendar.month_name[month]} {year} Payroll"

            # Determine status based on current date
            if end_date < today:
                # Past period
                status = 'closed'
            elif start_date <= today <= end_date:
                # Current period
                status = 'open'
            else:
                # Future period
                status = 'scheduled'

            PayrollPeriod.objects.get_or_create(
                organization=organization,
                period_name=period_name,
                defaults={
                    'frequency': 'monthly',
                    'start_date': start_date,
                    'end_date': end_date,
                    'pay_date': pay_date,
                    'status': status,
                }
            )

        self.stdout.write(f'  Created 12 monthly payroll periods for {year}')
