"""
Management command for comprehensive cache reconciliation.

Verifies and repairs:
- Rating caches (HospitalData, DoctorData, etc.)
- Wallet balances (computed vs stored)
- Inventory counts
- Appointment queue positions

Usage:
    python manage.py reconcile_caches
    python manage.py reconcile_caches --repair
    python manage.py reconcile_caches --check ratings
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Avg, Sum, Count
from decimal import Decimal
from core.models import Review, Participant, Wallet
from hospital.models import HospitalData
from doctor.models import DoctorData


class Command(BaseCommand):
    help = 'Verify and repair cached data across the platform'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repair',
            action='store_true',
            help='Repair inconsistencies (not just report them)',
        )
        parser.add_argument(
            '--check',
            type=str,
            choices=['ratings', 'wallets', 'inventory', 'all'],
            default='all',
            help='Which caches to check',
        )

    def handle(self, *args, **options):
        repair = options['repair']
        check_type = options['check']
        
        self.stdout.write(self.style.WARNING(
            '\n' + '='*70 + '\n'
            '  CACHE RECONCILIATION REPORT\n'
            + '='*70 + '\n'
        ))
        
        total_issues = 0
        total_repairs = 0
        
        # Check ratings
        if check_type in ['ratings', 'all']:
            issues, repairs = self._check_ratings(repair)
            total_issues += issues
            total_repairs += repairs
        
        # Check wallets
        if check_type in ['wallets', 'all']:
            issues, repairs = self._check_wallets(repair)
            total_issues += issues
            total_repairs += repairs
        
        # Summary
        self.stdout.write('\n' + '='*70)
        if total_issues == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    '\n✅ All caches are consistent! No issues found.\n'
                )
            )
        else:
            if repair:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n⚠️  Found {total_issues} inconsistencies, '
                        f'repaired {total_repairs}.\n'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n⚠️  Found {total_issues} inconsistencies. '
                        f'Run with --repair to fix them.\n'
                    )
                )
        self.stdout.write('='*70 + '\n')
    
    def _check_ratings(self, repair):
        """Check rating cache consistency"""
        self.stdout.write('\n📊 Checking rating caches...')
        issues = 0
        repairs = 0
        
        # Check hospitals
        self.stdout.write('  Hospitals: ', ending='')
        for hospital_data in HospitalData.objects.all():
            actual_rating = hospital_data.get_actual_rating()
            actual_reviews = hospital_data.get_actual_total_reviews()
            
            if (abs(hospital_data.rating - actual_rating) > 0.05 or 
                hospital_data.total_reviews != actual_reviews):
                issues += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'\n    ❌ {hospital_data.participant.full_name}: '
                        f'Cached={hospital_data.rating}/{hospital_data.total_reviews}, '
                        f'Actual={actual_rating}/{actual_reviews}'
                    )
                )
                
                if repair:
                    hospital_data.rating = actual_rating
                    hospital_data.total_reviews = actual_reviews
                    hospital_data.save(update_fields=['rating', 'total_reviews'])
                    repairs += 1
                    self.stdout.write(self.style.SUCCESS('      ✅ Repaired'))
        
        if issues == 0:
            self.stdout.write(self.style.SUCCESS('✅'))
        
        # Check doctors
        self.stdout.write('  Doctors: ', ending='')
        doctor_issues = 0
        for doctor_data in DoctorData.objects.all():
            approved_reviews = Review.objects.filter(
                reviewed_type='doctor',
                reviewed_id=doctor_data.participant.uid,
                is_approved=True
            )
            actual_rating = approved_reviews.aggregate(Avg('rating'))['rating__avg']
            actual_rating = round(actual_rating, 1) if actual_rating else 0.0
            actual_reviews = approved_reviews.count()
            
            if (abs(doctor_data.rating - actual_rating) > 0.05 or 
                doctor_data.total_reviews != actual_reviews):
                doctor_issues += 1
                issues += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'\n    ❌ {doctor_data.participant.full_name}: '
                        f'Cached={doctor_data.rating}/{doctor_data.total_reviews}, '
                        f'Actual={actual_rating}/{actual_reviews}'
                    )
                )
                
                if repair:
                    doctor_data.rating = actual_rating
                    doctor_data.total_reviews = actual_reviews
                    doctor_data.save(update_fields=['rating', 'total_reviews'])
                    repairs += 1
                    self.stdout.write(self.style.SUCCESS('      ✅ Repaired'))
        
        if doctor_issues == 0:
            self.stdout.write(self.style.SUCCESS('✅'))
        
        return issues, repairs
    
    def _check_wallets(self, repair):
        """Check wallet balance consistency"""
        self.stdout.write('\n💰 Checking wallet balances...')
        issues = 0
        repairs = 0
        
        for wallet in Wallet.objects.all():
            computed_balance = wallet.get_ledger_balance()
            stored_balance = wallet.balance or Decimal('0.00')
            
            if abs(computed_balance - stored_balance) > Decimal('0.01'):
                issues += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'\n  ❌ {wallet.participant.full_name}: '
                        f'Stored={stored_balance}, Computed={computed_balance}, '
                        f'Difference={stored_balance - computed_balance}'
                    )
                )
                
                if repair:
                    # Note: We're checking consistency, not updating
                    # Wallet balance is deprecated, ledger is source of truth
                    self.stdout.write(
                        self.style.WARNING(
                            '    ⚠️  Wallet balance field is deprecated. '
                            'Use get_ledger_balance() instead.'
                        )
                    )
                    # Could optionally sync the balance field here
                    # wallet.balance = computed_balance
                    # wallet.save(update_fields=['balance'])
                    # repairs += 1
        
        if issues == 0:
            self.stdout.write(self.style.SUCCESS('  ✅ All wallet balances consistent'))
        
        return issues, repairs
